from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import json
import traceback

from core.knowledge_graph.service import KnowledgeGraphService
from core.knowledge_graph.issue_router import resolve_known_issue_from_text
from core.knowledge_graph.conversation_store import conversation_store

router = APIRouter(tags=["knowledge-graph"])


class ResolveIssueRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier, e.g. tenant_demo")
    message: str = Field(..., min_length=3, description="User incident text")
    limit: int = Field(3, ge=1, le=10, description="Max candidate KnownIssues to return")


@router.post("/resolve_issue")
def resolve_issue(req: ResolveIssueRequest):
    try:
        print("\n[DEBUG] /resolve_issue called")
        print(f"[DEBUG] tenant_id={req.tenant_id} limit={req.limit}")
        print(f"[DEBUG] message={req.message!r}")

        kg = KnowledgeGraphService(req.tenant_id)
        result = resolve_known_issue_from_text(kg, req.message, limit=req.limit)

        conv = conversation_store.create_conversation(
            tenant_id=req.tenant_id,
            initial_user_message=req.message,
            initial_assistant_message=result.get("llm_answer"),
            selected_issue_id=result.get("selected_issue_id"),
            selected_context=result.get("selected_context"),
            llm_context=result.get("llm_context"),
        )

        result["conversation_id"] = conv["conversation_id"]

        safe_result = json.loads(json.dumps(result, default=str, ensure_ascii=False))
        print("[DEBUG] /resolve_issue success")
        return JSONResponse(content=safe_result)

    except Exception as e:
        print("\n[ERROR] /resolve_issue failed")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")
