from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import json
import traceback

from core.knowledge_graph.conversation_store import conversation_store
from core.knowledge_graph.rag.llm_orchestrator import AzureLLMOrchestrator

router = APIRouter(tags=["knowledge-graph"])

def _looks_like_new_issue(message: str) -> bool:
    text = (message or "").strip().lower()
    words = text.split()

    if not text:
        return False

    explicit_new_issue_phrases = [
        "another issue",
        "new issue",
        "different issue",
        "separate issue",
        "unrelated issue",
    ]
    if any(p in text for p in explicit_new_issue_phrases):
        return True

    followup_markers = [
        "runbook",
        "sop",
        "stakeholder",
        "stakeholders",
        "customer",
        "customers",
        "user",
        "users",
        "workaround",
        "mitigation",
        "impact",
        "next step",
        "next steps",
        "what do i tell",
        "what should i tell",
        "what do i say",
        "what should i say",
        "tell them",
        "communication",
        "update",
        "status update",
        "based on sop",
        "based on the sop",
        "based on runbook",
        "based on the runbook",
    ]
    if any(m in text for m in followup_markers):
        return False

    question_starters = {
        "what", "why", "how", "when", "where",
        "can", "should", "do", "does", "is", "are"
    }
    if words and words[0] in question_starters:
        return False

    # Looks like a fresh symptom/problem statement
    problem_markers = [
        "not working",
        "is failing",
        "failed",
        "broken",
        "error",
        "issue",
        "unable to",
        "cannot",
        "can't",
        "stuck",
        "down",
        "timeout",
        "login failed",
        "not updating",
    ]
    if any(m in text for m in problem_markers):
        return True

    # Default safer behavior:
    # if unclear, keep it in current thread instead of forcing new issue
    return False


class IssueChatRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier, e.g. tenant_demo")
    conversation_id: str = Field(..., min_length=1, description="Existing conversation id")
    message: str = Field(..., min_length=1, description="Follow-up user message")


@router.post("/issue_chat")
def issue_chat(req: IssueChatRequest):
    try:
        print("\n[DEBUG] /issue_chat called")
        print(f"[DEBUG] tenant_id={req.tenant_id}")
        print(f"[DEBUG] conversation_id={req.conversation_id}")
        print(f"[DEBUG] message={req.message!r}")

        conv = conversation_store.get_conversation(req.conversation_id)

        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if conv.get("tenant_id") != req.tenant_id:
            raise HTTPException(status_code=403, detail="Conversation does not belong to this tenant")

        selected_issue_id = conv.get("selected_issue_id")
        selected_context = conv.get("selected_context")
        llm_context = conv.get("llm_context")
        chat_history = conv.get("messages", [])

        if not selected_issue_id or not selected_context:
            raise HTTPException(
                status_code=400,
                detail="Conversation does not contain a selected issue context"
            )
        
        if _looks_like_new_issue(req.message):
            result = {
                "ok": True,
                "conversation_id": req.conversation_id,
                "selected_issue_id": selected_issue_id,
                "llm_answer": (
                    "This looks like a new or unrelated issue. Please click 'Start New Issue' "
                    "so I can run a fresh issue resolution instead of continuing the current thread."
                ),
                "requires_new_issue_resolution": True,
                "llm_context": llm_context,
            }

            safe_result = json.loads(json.dumps(result, default=str, ensure_ascii=False))
            return JSONResponse(content=safe_result)

        orchestrator = AzureLLMOrchestrator()

        llm_result = orchestrator.answer_followup_from_known_issue(
            user_query=req.message,
            selected_issue_id=selected_issue_id,
            selected_context=selected_context,
            chat_history=chat_history,
            llm_context=llm_context,
        )

        conversation_store.append_message(req.conversation_id, "user", req.message)
        conversation_store.append_message(req.conversation_id, "assistant", llm_result["answer"])
        conversation_store.update_context(
            req.conversation_id,
            llm_context=llm_result.get("assembled_context"),
        )

        result = {
            "ok": True,
            "conversation_id": req.conversation_id,
            "selected_issue_id": selected_issue_id,
            "llm_answer": llm_result["answer"],
            "llm_context": llm_result.get("assembled_context"),
        }

        safe_result = json.loads(json.dumps(result, default=str, ensure_ascii=False))
        print("[DEBUG] /issue_chat success")
        return JSONResponse(content=safe_result)

    except HTTPException:
        raise
    except Exception as e:
        print("\n[ERROR] /issue_chat failed")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")