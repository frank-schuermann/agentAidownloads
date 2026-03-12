# core/knowledge_graph/issue_router.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


# Keyword extraction approach copied from the demo server.py style:
# - category term buckets + stopword fallback :contentReference[oaicite:2]{index=2}
def extract_keywords(text: str) -> List[str]:
    keyword_map = {
        # ccaaS-ish
        "outage": ["outage", "down", "unavailable", "error", "failure", "drop"],
        "latency": ["slow", "delay", "latency", "timeout", "spinning"],
        "routing": ["routing", "queue", "workstream", "assignment", "overflow"],
        "voice": ["voice", "call", "transfer", "warm transfer", "cold transfer", "acs"],
        "chat": ["chat", "widget", "live chat", "web chat", "messaging"],
        "copilot": ["copilot", "suggestion", "draft", "summarization"],
        "knowledge": ["knowledge", "kb", "article", "documentation"],
        # workforce management
        "wfm": ["wfm", "workforce", "forecast", "schedule", "intraday", "staffing", "regenerate", "regen", "jobs"],
        # quality management
        "qm": ["quality", "qm", "scorecard", "evaluation", "rubric", "calibration", "review"],
    }

    text_lower = (text or "").lower()
    found = set()

    for cat, terms in keyword_map.items():
        for term in terms:
            if term in text_lower:
                found.add(cat)
                found.add(term)

    # stopword fallback (same idea as demo) :contentReference[oaicite:3]{index=3}
    stop_words = {
        "the","a","an","is","are","was","were","in","on","at","to","for","of","with","and","or","not","from","by",
        "it","this","that","be","has","have","had","do","does","did","will","would","can","could","should","may","might",
        "i","we","they","he","she","our","their","my","your","but","if","when","then","than","no","yes","all","any",
        "some","been","being","about","into","through","after","before","between","out","up","down","just","also","very",
        "so","too","here","there","how","what","which","who"
    }

    for w in text_lower.split():
        cleaned = w.strip(".,!?;:\"'()[]{}").lower()
        if len(cleaned) > 2 and cleaned not in stop_words:
            found.add(cleaned)

    return list(found)


@dataclass
class IssueMatch:
    issue_id: str
    score: float
    service_ids: List[str]
    debug_hits: List[str]


def resolve_known_issue_from_text(kg: Any, message: str, limit: int = 3) -> Dict[str, Any]:
    """
    Returns:
      {
        "ok": True,
        "keywords": [...],
        "candidates": [ {issue_id, score, service_ids, debug_hits}, ... ],
        "selected_issue_id": "KI-xxx" | None,
        "selected_context": {...} | None
      }
    """
    keywords = extract_keywords(message)
    keywords_l = [k.lower() for k in keywords if k and isinstance(k, str)]

    # For a POC-sized graph, brute-force is fine:
    # Pull KnownIssues + linked Services, then score in Python.
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
            return " ".join([str(x) for x in v if x is not None])
        return str(v)

    for r in rows:
        issue = r.get("issue") or {}
        issue_id = (issue.get("issue_id") or "").strip()
        if not issue_id:
            continue

        service_ids = [sid for sid in (r.get("service_ids") or []) if sid]

        hay = " ".join([
            _as_text(issue.get("symptoms")),
            _as_text(issue.get("root_cause")),
            _as_text(issue.get("workaround")),
            _as_text(issue.get("status")),
            _as_text(issue.get("severity")),
            _as_text(issue.get("affected_versions")),
        ]).lower()

        # Simple weighted scoring:
        # - exact keyword hit adds points
        # - category hits (wfm/qm/etc) help cluster
        score = 0.0
        hits: List[str] = []
        for k in keywords_l:
            if k and k in hay:
                score += 1.0
                hits.append(k)

        # tiny bonus if the user literally typed "KI-00x"
        if issue_id.lower() in (message or "").lower():
            score += 5.0
            hits.append(f"id:{issue_id.lower()}")

        if score > 0:
            candidates.append(IssueMatch(issue_id=issue_id, score=score, service_ids=service_ids, debug_hits=hits[:20]))

    candidates.sort(key=lambda x: x.score, reverse=True)
    top = candidates[: max(1, min(limit, 10))]

    selected_issue_id = top[0].issue_id if top else None
    selected_context = kg.get_known_issue_full_context(selected_issue_id) if selected_issue_id else None

    return {
        "ok": True,
        "keywords": keywords[:25],
        "candidates": [
            {
                "issue_id": c.issue_id,
                "score": c.score,
                "service_ids": c.service_ids,
                "debug_hits": c.debug_hits,
            }
            for c in top
        ],
        "selected_issue_id": selected_issue_id,
        "selected_context": selected_context,
    }