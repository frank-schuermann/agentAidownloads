from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import AzureOpenAI

from core.knowledge_graph.rag.llm_context_builder import LLMContextBuilder

load_dotenv()


class AzureLLMOrchestrator:
    def __init__(self, docs_base_dir: str | None = None):
        if docs_base_dir is None:
            base_dir = Path(__file__).resolve().parents[3]
            docs_base_dir = str(base_dir / "data" / "kg_docs")

        self.docs_base_dir = str(Path(docs_base_dir).resolve())

        self.client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        )

        self.chat_model = os.getenv("AZURE_OPENAI_CHAT_MODEL", "")
        self.context_builder = LLMContextBuilder(self.docs_base_dir)

        if not os.getenv("AZURE_OPENAI_ENDPOINT"):
            raise ValueError("Missing AZURE_OPENAI_ENDPOINT in .env")
        if not os.getenv("AZURE_OPENAI_API_KEY"):
            raise ValueError("Missing AZURE_OPENAI_API_KEY in .env")
        if not self.chat_model:
            raise ValueError("Missing AZURE_OPENAI_CHAT_MODEL in .env")

    def _format_doc_block(self, title: str, doc: Optional[Dict[str, str]]) -> str:
        if not doc:
            return f"{title}: NOT AVAILABLE\n"

        return (
            f"{title}:\n"
            f"File: {doc['file_name']}\n"
            f"Path: {doc['path']}\n"
            f"Content:\n{doc['content']}\n"
        )

    def simple_completion(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {"role": "system", "content": "You are a classification assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        return response.choices[0].message.content

    def _build_prompt(self, assembled: Dict[str, Any]) -> str:
        issue_summary = assembled["issue_summary"]
        required_docs = assembled["required_docs"]
        optional_docs = assembled["optional_docs"]

        prompt = f"""
You are a reliable enterprise technical support assistant.

Use ONLY the provided context.
Do not invent details.
Do not answer from memory.
If the context is incomplete, say that clearly.
If the issue context does not clearly support the requested answer, say that the known issue match is not strong enough.
Prioritize operational next steps from the runbook and SOP.

USER QUESTION:
{assembled["user_query"]}

SELECTED KNOWN ISSUE:
Issue ID: {issue_summary.get("issue_id")}
Severity: {issue_summary.get("severity")}
Status: {issue_summary.get("status")}
Root Cause: {issue_summary.get("root_cause")}
Workaround: {issue_summary.get("workaround")}
Symptoms: {issue_summary.get("symptoms")}
Affected Services: {issue_summary.get("affected_service_ids")}

REQUIRED DOCUMENTS:
{self._format_doc_block("KNOWN ISSUE DOCUMENT", required_docs.get("known_issue_doc"))}

{self._format_doc_block("RUNBOOK DOCUMENT", required_docs.get("runbook_doc"))}

{self._format_doc_block("SOP DOCUMENT", required_docs.get("sop_doc"))}

OPTIONAL DOCUMENTS:
{self._format_doc_block("FAQ DOCUMENT", optional_docs.get("faq_doc"))}

{self._format_doc_block("USER GUIDE DOCUMENT", optional_docs.get("guide_doc"))}

{self._format_doc_block("RELEASE NOTE DOCUMENT", optional_docs.get("release_doc"))}

Please answer in this structure:
1. Short issue identification
2. Likely cause
3. Immediate next steps
4. Communication / SOP guidance
5. Anything missing or uncertain
"""
        return prompt.strip()

    def _format_chat_history(self, chat_history: List[Dict[str, str]], max_turns: int = 8) -> str:
        trimmed = chat_history[-max_turns:] if chat_history else []

        if not trimmed:
            return "NO PRIOR CHAT HISTORY"

        lines: List[str] = []
        for msg in trimmed:
            role = (msg.get("role") or "").upper()
            content = msg.get("content") or ""
            lines.append(f"{role}: {content}")

        return "\n".join(lines)

    def _build_followup_prompt(
        self,
        user_query: str,
        assembled: Dict[str, Any],
        chat_history: List[Dict[str, str]],
    ) -> str:
        issue_summary = assembled["issue_summary"]
        required_docs = assembled["required_docs"]
        optional_docs = assembled["optional_docs"]

        history_block = self._format_chat_history(chat_history)

        prompt = f"""
You are a reliable enterprise technical support assistant continuing an existing issue conversation.

You are already inside a thread for the same selected known issue.
Use ONLY the provided issue context, documents, and prior conversation.
Do not invent details.
Do not switch to a new issue unless the user clearly asks about a different problem.
If the answer is not available in the current context, say that clearly.
Do not reuse prior issue context for a clearly unrelated new problem.

PRIOR CHAT HISTORY:
{history_block}

FOLLOW-UP USER QUESTION:
{user_query}

SELECTED KNOWN ISSUE:
Issue ID: {issue_summary.get("issue_id")}
Severity: {issue_summary.get("severity")}
Status: {issue_summary.get("status")}
Root Cause: {issue_summary.get("root_cause")}
Workaround: {issue_summary.get("workaround")}
Symptoms: {issue_summary.get("symptoms")}
Affected Services: {issue_summary.get("affected_service_ids")}

REQUIRED DOCUMENTS:
{self._format_doc_block("KNOWN ISSUE DOCUMENT", required_docs.get("known_issue_doc"))}

{self._format_doc_block("RUNBOOK DOCUMENT", required_docs.get("runbook_doc"))}

{self._format_doc_block("SOP DOCUMENT", required_docs.get("sop_doc"))}

OPTIONAL DOCUMENTS:
{self._format_doc_block("FAQ DOCUMENT", optional_docs.get("faq_doc"))}

{self._format_doc_block("USER GUIDE DOCUMENT", optional_docs.get("guide_doc"))}

{self._format_doc_block("RELEASE NOTE DOCUMENT", optional_docs.get("release_doc"))}

Answer naturally for the follow-up.
If useful, structure the answer as:
- direct answer
- relevant next step
- customer / agent wording
- uncertainty or missing info
"""
        return prompt.strip()

    def answer_from_known_issue(
        self,
        user_query: str,
        selected_issue_id: str,
        selected_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        assembled = self.context_builder.build(
            user_query=user_query,
            selected_issue_id=selected_issue_id,
            selected_context=selected_context,
        )

        prompt = self._build_prompt(assembled)

        response = self.client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a reliable enterprise technical support assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
        )

        answer = response.choices[0].message.content if response.choices else ""

        return {
            "ok": True,
            "selected_issue_id": selected_issue_id,
            "docs_base_dir": self.docs_base_dir,
            "answer": answer,
            "assembled_context": assembled,
        }

    def answer_followup_from_known_issue(
        self,
        user_query: str,
        selected_issue_id: str,
        selected_context: Dict[str, Any],
        chat_history: List[Dict[str, str]],
        llm_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        assembled = llm_context or self.context_builder.build(
            user_query=user_query,
            selected_issue_id=selected_issue_id,
            selected_context=selected_context,
        )

        assembled["user_query"] = user_query

        prompt = self._build_followup_prompt(
            user_query=user_query,
            assembled=assembled,
            chat_history=chat_history,
        )

        response = self.client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a reliable enterprise technical support assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
        )

        answer = response.choices[0].message.content if response.choices else ""

        return {
            "ok": True,
            "selected_issue_id": selected_issue_id,
            "docs_base_dir": self.docs_base_dir,
            "answer": answer,
            "assembled_context": assembled,
        }