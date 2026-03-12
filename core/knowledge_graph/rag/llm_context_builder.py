from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional


class LLMContextBuilder:
    def __init__(self, docs_base_dir: str | None = None):
        if docs_base_dir is None:
            # This file lives in:
            # kg/core/knowledge_graph/rag/llm_context_builder.py
            # parents[3] -> kg/
            base_dir = Path(__file__).resolve().parents[3]
            docs_base_dir = str(base_dir / "data" / "kg_docs")

        self.docs_base_dir = Path(docs_base_dir).resolve()

    def _read_doc(self, relative_path: Optional[str]) -> Optional[Dict[str, str]]:
        if not relative_path:
            return None

        # Normalize any incoming KG path and keep only the file name.
        # Examples:
        #   data/Runbook_QM_RubricCacheReset.txt
        #   kg/Runbook_QM_RubricCacheReset.txt
        #   C:/temp/Runbook_QM_RubricCacheReset.txt
        #   Runbook_QM_RubricCacheReset.txt
        file_name = Path(str(relative_path).replace("\\", "/")).name
        full_path = self.docs_base_dir / file_name

        if not full_path.exists():
            return None

        return {
            "file_name": file_name,
            "path": str(full_path),
            "content": full_path.read_text(encoding="utf-8").strip(),
        }

    def _first_or_none(self, items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        return items[0] if items else None

    def build(
        self,
        user_query: str,
        selected_issue_id: str,
        selected_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        issue = selected_context.get("issue") or {}
        linked = selected_context.get("linked") or {}
        affected = selected_context.get("affected") or {}

        services = affected.get("services") or []
        runbooks = linked.get("runbooks") or []
        sops = linked.get("sops") or []
        faqs = linked.get("faqs") or []
        documents = linked.get("documents") or []
        releases = linked.get("releases") or []

        known_issue_doc = self._read_doc(issue.get("document"))
        runbook_doc = self._read_doc(self._first_or_none(runbooks).get("document") if runbooks else None)
        sop_doc = self._read_doc(self._first_or_none(sops).get("document") if sops else None)

        faq_doc = self._read_doc(self._first_or_none(faqs).get("document") if faqs else None)
        guide_doc = self._read_doc(self._first_or_none(documents).get("document") if documents else None)
        release_doc = self._read_doc(self._first_or_none(releases).get("document") if releases else None)

        return {
            "user_query": user_query,
            "selected_issue_id": selected_issue_id,
            "docs_base_dir": str(self.docs_base_dir),
            "issue_summary": {
                "issue_id": issue.get("issue_id"),
                "severity": issue.get("severity"),
                "status": issue.get("status"),
                "root_cause": issue.get("root_cause"),
                "workaround": issue.get("workaround"),
                "symptoms": issue.get("symptoms", []),
                "affected_service_ids": [
                    svc.get("service_id")
                    for svc in services
                    if svc.get("service_id")
                ],
            },
            "required_docs": {
                "known_issue_doc": known_issue_doc,
                "runbook_doc": runbook_doc,
                "sop_doc": sop_doc,
            },
            "optional_docs": {
                "faq_doc": faq_doc,
                "guide_doc": guide_doc,
                "release_doc": release_doc,
            },
        }