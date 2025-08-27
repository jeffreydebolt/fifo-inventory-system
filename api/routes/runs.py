"""
API routes for COGS runs management - simplified for deployment.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
import logging

router = APIRouter(prefix="/runs", tags=["runs"])
logger = logging.getLogger(__name__)


@router.get("")
async def list_runs(
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0)
):
    """List COGS calculation runs for a tenant"""
    # Stub implementation
    return {
        "runs": [],
        "total": 0,
        "page": offset // limit + 1,
        "limit": limit
    }


@router.post("", status_code=201)
async def create_run(
    tenant_id: str,
    mode: str = "fifo"
):
    """Create and execute a new COGS calculation run"""
    # Stub implementation
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    return {
        "run_id": run_id,
        "tenant_id": tenant_id,
        "status": "completed",
        "started_at": datetime.now().isoformat(),
        "completed_at": datetime.now().isoformat(),
        "total_sales_processed": 0,
        "total_cogs_calculated": 0.0,
        "validation_errors_count": 0
    }


@router.get("/{run_id}")
async def get_run(run_id: str, tenant_id: Optional[str] = Query(None)):
    """Get details of a specific run"""
    # Stub implementation
    return {
        "run_id": run_id,
        "tenant_id": tenant_id or "demo",
        "status": "completed",
        "started_at": datetime.now().isoformat(),
        "completed_at": datetime.now().isoformat(),
        "total_sales_processed": 0,
        "total_cogs_calculated": 0.0,
        "validation_errors_count": 0,
        "attributions": [],
        "validation_errors": []
    }


@router.delete("/{run_id}")
async def rollback_run(run_id: str, tenant_id: Optional[str] = Query(None)):
    """Rollback a COGS calculation run"""
    # Stub implementation
    return {
        "run_id": run_id,
        "status": "rolled_back",
        "restored_lots_count": 0,
        "message": "Run rolled back successfully (demo)"
    }


@router.get("/{run_id}/journal")
async def generate_journal_entry(
    run_id: str, 
    format: str = Query("quickbooks", regex="^(quickbooks|sage|csv)$")
):
    """Generate journal entry for a run"""
    # Stub implementation
    return {
        "run_id": run_id,
        "format": format,
        "content": "Demo journal entry content",
        "generated_at": datetime.now().isoformat()
    }