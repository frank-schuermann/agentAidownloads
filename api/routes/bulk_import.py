"""
API Routes for Bulk Document Import

Handles ZIP upload and batch document processing.
"""

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from core.knowledge_graph.bulk_import_service import BulkImportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bulk-import", tags=["bulk-import"])


# =============================================================================
# Request/Response Models
# =============================================================================
class BulkImportResponse(BaseModel):
    """Response from bulk import."""
    status: str
    stats: dict
    timestamp: str


class BulkImportOptions(BaseModel):
    """Options for bulk import."""
    tenant_id: str = Field(default="tenant_demo")
    create_edges: bool = Field(default=True, description="Infer and create edges")
    min_edge_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for edge creation (0.0-1.0)"
    )


# =============================================================================
# Routes
# =============================================================================
@router.post("/zip", response_model=BulkImportResponse)
async def import_from_zip(
    file: UploadFile = File(..., description="ZIP file with documents"),
    tenant_id: str = Form("tenant_demo"),
    create_edges: bool = Form(True),
    min_edge_confidence: float = Form(0.5),
):
    """
    Import documents from ZIP archive.
    
    **Supported document types:**
    - Runbooks (RB-*, Runbook-*.txt)
    - Known Issues (KI-*, KnownIssue-*.txt)
    - FAQs (FAQ-*.txt)
    - SOPs (SOP-*.txt)
    - SPOs (SPO-*.txt)
    - User Guides (UserGuide-*.txt, Guide-*.txt)
    - Generic Documents (*.txt, *.md)
    
    **Automatic edge inference:**
    - Explicit references (KI-001 mentions RB-002)
    - Keyword overlap (both about 'voice' + 'routing')
    - Naming patterns (KI-Voice-Transfer ↔ Runbook-Voice-Outage)
    
    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/bulk-import/zip" \\
      -F "file=@documents.zip" \\
      -F "tenant_id=tenant_demo" \\
      -F "create_edges=true" \\
      -F "min_edge_confidence=0.6"
    ```
    """
    # Validate file type
    if not file.filename.endswith('.zip'):
        raise HTTPException(
            status_code=400,
            detail="Only ZIP files are supported"
        )
    
    # Read file bytes
    try:
        zip_bytes = await file.read()
    except Exception as e:
        logger.error(f"Error reading uploaded file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error reading file: {str(e)}"
        )
    
    # Import documents
    try:
        service = BulkImportService(tenant_id)
        result = service.import_from_zip(
            zip_bytes=zip_bytes,
            create_edges=create_edges,
            min_edge_confidence=min_edge_confidence,
        )
        
        logger.info(f"✅ Bulk import completed: {result['stats']}")
        
        return BulkImportResponse(**result)
    
    except Exception as e:
        logger.error(f"Bulk import failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Import failed: {str(e)}"
        )


@router.get("/status")
async def get_import_status():
    """
    Get current import service status.
    
    Returns basic health check and statistics.
    """
    return {
        "status": "online",
        "service": "Bulk Document Import",
        "supported_formats": [".txt", ".md", ".markdown"],
        "supported_types": [
            "Runbook", "KnownIssue", "FAQ", "SOP", "SPO",
            "UserGuide", "Configuration", "Infrastructure", "Document"
        ],
        "edge_inference": [
            "Explicit references",
            "Keyword-based semantic",
            "Naming pattern matching"
        ],
    }
