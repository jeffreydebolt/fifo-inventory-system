"""
API routes for COGS runs management - with real FIFO processing.
"""
from fastapi import APIRouter, HTTPException, Query, Request
from typing import List, Optional, Dict
from datetime import datetime
import logging
import pandas as pd
import io
import os
import tempfile

router = APIRouter(prefix="/runs", tags=["runs"])
logger = logging.getLogger(__name__)

# Track uploaded files in memory (demo - would use database in production)
uploaded_files: Dict[str, pd.DataFrame] = {}


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
    request: Request
):
    """Create and execute a new COGS calculation run with real FIFO processing"""
    try:
        # Get request data
        data = await request.json()
        tenant_id = data.get("tenant_id", "demo")
        lots_file_id = data.get("lots_file_id")
        sales_file_id = data.get("sales_file_id")
        
        # Use database-driven FIFO processing
        from api.services.supabase_service import supabase_service
        result = supabase_service.process_fifo_with_database(tenant_id, lots_file_id, sales_file_id)
        
        response = {
            "run_id": result.get('run_id', f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
            "tenant_id": tenant_id,
            "status": "completed" if result.get("success") else "failed",
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "total_sales_processed": result.get("total_sales_processed", 0),
            "total_cogs_calculated": result.get("total_cogs_calculated", 0),
            "validation_errors_count": result.get("validation_errors", 0),
            "processed_skus": result.get("processed_skus", 0)
        }
        
        # Include error message if the run failed
        if result.get("error"):
            response["error"] = result.get("error")
            
        return response
        
    except Exception as e:
        logger.error(f"FIFO processing error: {str(e)}")
        return {
            "run_id": f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "tenant_id": "demo",
            "status": "failed",
            "error": str(e),
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "total_sales_processed": 0,
            "total_cogs_calculated": 0
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