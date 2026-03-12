from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.knowledge_graph.rag.retriever import HybridRetriever
from core.knowledge_graph.rag.llm_orchestrator import AzureLLMOrchestrator
from core.knowledge_graph.rag.candidate_judge import CandidateJudge


@dataclass
class IssueMatch:
    issue_id: str
    score: float
    service_ids: List[str]
    debug_hits: List[str]


def _project_root_from_here() -> Path:
    return Path(__file__).resolve().parents[2]


def _build_local_retriever() -> HybridRetriever:
    base_dir = _project_root_from_here()
    chroma_dir = base_dir / "chroma_store"

    return HybridRetriever(
        persist_directory=str(chroma_dir),
        collection_name="kg_rag_collection",
        top_k=5,
    )


def _save_rag_result_json(payload: Dict[str, Any]) -> None:
    base_dir = _project_root_from_here()
    out_dir = base_dir / "rag_debug"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / "last_rag_result.json"
    out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _extract_service_ids_from_context(selected_context: Optional[Dict[str, Any]]) -> List[str]:
    if not selected_context:
        return []

    affected = selected_context.get("affected") or {}
    services = affected.get("services") or []

    service_ids: List[str] = []
    for svc in services:
        sid = svc.get("service_id")
        if sid:
            service_ids.append(sid)

    return service_ids


def _is_context_usable(selected_context: Optional[Dict[str, Any]]) -> bool:
    """
    A candidate is only usable for the downstream LLM flow if:
      - KG returned a context
      - the issue has a document
      - at least one runbook OR one SOP exists
    """
    if not selected_context:
        return False

    issue = selected_context.get("issue") or {}
    linked = selected_context.get("linked") or {}

    if not issue.get("document"):
        return False

    runbooks = linked.get("runbooks") or []
    sops = linked.get("sops") or []

    if not runbooks and not sops:
        return False

    return True


# ----------------------------------------------------------------------
# KEYWORD FALLBACK
# ----------------------------------------------------------------------

def extract_keywords(text: str) -> List[str]:
    keyword_map = {
        "outage": ["outage", "down", "unavailable", "error", "failure", "drop"],
        "latency": ["slow", "delay", "latency", "timeout", "spinning"],
        "routing": ["routing", "queue", "workstream", "assignment", "overflow"],
        "voice": ["voice", "call", "transfer", "warm transfer", "cold transfer", "acs"],
        "chat": ["chat", "widget", "live chat", "web chat", "messaging"],
        "copilot": ["copilot", "suggestion", "draft", "summarization", "summary", "hallucination"],
        "knowledge": ["knowledge", "kb", "article", "documentation"],
        "wfm": ["wfm", "workforce", "forecast", "schedule", "intraday", "staffing"],
        "qm": ["quality", "qm", "scorecard", "evaluation", "rubric", "calibration"],
        "sso": ["sso", "login", "saml", "oauth", "authentication", "identity", "assertion"],
    }

    text_lower = (text or "").lower()
    found = set()

    for cat, terms in keyword_map.items():
        for term in terms:
            if term in text_lower:
                found.add(cat)
                found.add(term)

    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for", "of", "with", "and", "or",
        "it", "this", "that", "be", "has", "have", "had", "do", "does", "did", "will", "would",
    }

    for w in text_lower.split():
        cleaned = w.strip(".,!?;:\"'()[]{}").lower()
        if len(cleaned) > 2 and cleaned not in stop_words:
            found.add(cleaned)

    return list(found)


def _keyword_fallback_known_issue_search(kg: Any, message: str, limit: int = 3) -> Dict[str, Any]:
    keywords = extract_keywords(message)
    keywords_l = [k.lower() for k in keywords]

    cypher = """
    MATCH (ki:KnownIssue {tenant_id:$tenant_id})
    OPTIONAL MATCH (svc:Service {tenant_id:$tenant_id})-[:HAS_KNOWN_ISSUE {tenant_id:$tenant_id}]->(ki)
    RETURN ki AS issue, collect(distinct svc.service_id) AS service_ids
    """

    rows = kg.db.execute_read(cypher, {"tenant_id": kg.tenant_id}) or []

    candidates: List[IssueMatch] = []

    def _as_text(v: Any) -> str:
        if v is None:
            return ""
        if isinstance(v, list):
            return " ".join([str(x) for x in v])
        return str(v)

    for r in rows:
        issue = r.get("issue") or {}
        issue_id = (issue.get("issue_id") or "").strip()

        if not issue_id:
            continue

        service_ids = r.get("service_ids") or []

        hay = " ".join([
            _as_text(issue.get("symptoms")),
            _as_text(issue.get("root_cause")),
            _as_text(issue.get("workaround")),
            _as_text(issue.get("title")),
            _as_text(issue.get("description")),
        ]).lower()

        score = 0.0
        hits: List[str] = []

        for k in keywords_l:
            if k in hay:
                score += 1.0
                hits.append(k)

        if issue_id.lower() in message.lower():
            score += 5.0
            hits.append(issue_id.lower())

        if score > 0:
            candidates.append(
                IssueMatch(
                    issue_id=issue_id,
                    score=score,
                    service_ids=service_ids,
                    debug_hits=hits,
                )
            )

    candidates.sort(key=lambda x: x.score, reverse=True)
    top = candidates[:limit]

    return {
        "keywords": keywords,
        "candidates": top,
        "selected_issue_id": top[0].issue_id if top else None,
    }


# ----------------------------------------------------------------------
# MAIN ROUTER
# ----------------------------------------------------------------------

def resolve_known_issue_from_text(kg: Any, message: str, limit: int = 3) -> Dict[str, Any]:
    query = (message or "").strip()

    if not query:
        return {
            "ok": False,
            "rag_query": query,
            "fallback_used": False,
            "candidates": [],
            "selected_issue_id": None,
            "selected_context": None,
            "llm_answer": None,
            "llm_context": None,
            "error": "Empty message",
        }

    retriever = _build_local_retriever()

    rag_results = retriever.hybrid_search(query, top_k=max(3, min(limit * 3, 10)))

    _save_rag_result_json({
        "query": query,
        "rag_results": rag_results,
    })

    grouped_results = rag_results.get("grouped_results", []) or []

    rag_candidates: List[IssueMatch] = []

    for row in grouped_results:
        if row.get("doc_type") != "KnownIssue":
            continue

        entity_id = row.get("entity_id")
        score = float(row.get("best_score", 0.0))
        sources = row.get("sources", [])

        if not entity_id:
            continue

        rag_candidates.append(
            IssueMatch(
                issue_id=entity_id,
                score=score,
                service_ids=[],
                debug_hits=sources,
            )
        )

    rag_top = rag_candidates[:limit]

    judge = CandidateJudge()

    selected_issue_id: Optional[str] = None
    selected_context: Optional[Dict[str, Any]] = None
    fallback_used = False

    # -------------------------------
    # Candidate Judge on RAG results
    # -------------------------------
    for candidate in rag_top:
        ctx = kg.get_known_issue_full_context(candidate.issue_id)

        if not ctx:
            continue

        verdict = judge.judge(query, candidate.issue_id, ctx)

        is_match = verdict.get("match") is True
        confidence = float(verdict.get("confidence", 0) or 0)

        # Candidate must be semantically accepted by judge
        # AND structurally usable for the downstream LLM/doc flow
        if is_match and confidence > 0.6 and _is_context_usable(ctx):
            selected_issue_id = candidate.issue_id
            selected_context = ctx
            break

    # -------------------------------
    # Fallback to KG keyword search
    # -------------------------------
    if not selected_issue_id:
        fallback_used = True

        fallback = _keyword_fallback_known_issue_search(kg, query, limit)

        selected_issue_id = fallback.get("selected_issue_id")

        if selected_issue_id:
            selected_context = kg.get_known_issue_full_context(selected_issue_id)

        rag_top = fallback["candidates"]

    # -------------------------------
    # Extract service ids
    # -------------------------------
    if rag_top and selected_context:
        rag_top[0].service_ids = _extract_service_ids_from_context(selected_context)

    # -------------------------------
    # LLM answer generation
    # -------------------------------
    llm_result = None

    if selected_issue_id and selected_context:
        orchestrator = AzureLLMOrchestrator()

        llm_result = orchestrator.answer_from_known_issue(
            user_query=query,
            selected_issue_id=selected_issue_id,
            selected_context=selected_context,
        )

    return {
        "ok": True,
        "rag_query": query,
        "fallback_used": fallback_used,
        "candidates": [asdict(c) for c in rag_top],
        "selected_issue_id": selected_issue_id,
        "selected_context": selected_context,
        "llm_answer": llm_result["answer"] if llm_result else None,
        "llm_context": llm_result["assembled_context"] if llm_result else None,
    }