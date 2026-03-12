from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
import subprocess
import sys

router = APIRouter(tags=["knowledge-graph"])

class ReloadGraphRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier")
    kg_json: str = Field(..., description="Path to knowledge_graph.json")
    reset: bool = Field(True, description="If true, delete tenant graph first (recommended)")

@router.post("/api/reload-graph")
def reload_graph(req: ReloadGraphRequest):
    try:
        # Option A (simple + reliable): call your seeding module as a subprocess
        # You can extend this to pass --reset if your script supports it.
        cmd = [
            sys.executable,
            "-m",
            "scripts.kg_seed_ccas_poc",
            "--tenant-id",
            req.tenant_id,
            "--kg-json",
            req.kg_json,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or "Seed failed")

        return {"ok": True, "stdout": result.stdout}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))