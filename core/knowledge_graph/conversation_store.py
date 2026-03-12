from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4


class InMemoryIssueConversationStore:
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    def create_conversation(
        self,
        tenant_id: str,
        initial_user_message: str,
        initial_assistant_message: Optional[str],
        selected_issue_id: Optional[str],
        selected_context: Optional[Dict[str, Any]],
        llm_context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        conversation_id = str(uuid4())

        payload = {
            "conversation_id": conversation_id,
            "tenant_id": tenant_id,
            "selected_issue_id": selected_issue_id,
            "selected_context": selected_context,
            "llm_context": llm_context,
            "messages": [
                {"role": "user", "content": initial_user_message},
                {"role": "assistant", "content": initial_assistant_message or ""},
            ],
            "mode": "issue_chat",
        }

        self._store[conversation_id] = payload
        return payload

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(conversation_id)

    def append_message(self, conversation_id: str, role: str, content: str) -> Optional[Dict[str, Any]]:
        conv = self._store.get(conversation_id)
        if not conv:
            return None

        conv.setdefault("messages", []).append({
            "role": role,
            "content": content,
        })
        return conv

    def update_context(
        self,
        conversation_id: str,
        *,
        selected_issue_id: Optional[str] = None,
        selected_context: Optional[Dict[str, Any]] = None,
        llm_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        conv = self._store.get(conversation_id)
        if not conv:
            return None

        if selected_issue_id is not None:
            conv["selected_issue_id"] = selected_issue_id
        if selected_context is not None:
            conv["selected_context"] = selected_context
        if llm_context is not None:
            conv["llm_context"] = llm_context

        return conv


conversation_store = InMemoryIssueConversationStore()