from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
import json
from pathlib import Path

router = APIRouter(tags=["feedback"])

FEEDBACK_PATH = Path("feedback.json")

class FeedbackRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier")
    issue_id: str | None = Field(None, description="KnownIssue ID if available")
    rating: int = Field(..., ge=0, le=1, description="0=thumbs down, 1=thumbs up")
    message: str = Field(..., min_length=1, description="Original user message")
    comment: str | None = Field(None, description="Optional extra text")

@router.post("/api/feedback")
def submit_feedback(req: FeedbackRequest):
    try:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": req.tenant_id,
            "issue_id": req.issue_id,
            "rating": req.rating,
            "message": req.message,
            "comment": req.comment,
        }

        existing = []
        if FEEDBACK_PATH.exists():
            existing = json.loads(FEEDBACK_PATH.read_text(encoding="utf-8") or "[]")

        existing.append(record)
        FEEDBACK_PATH.write_text(json.dumps(existing, indent=2), encoding="utf-8")

        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))