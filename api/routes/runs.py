"""
API routes for COGS runs management.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from datetime import datetime
import logging

from api.models import (
    CreateRunRequest, RunResponse, RunListResponse, 
    RollbackResponse, RunDetailResponse, JournalEntryResponse
)
from services.journaled_calculator import JournaledCalculator
from core.fifo_engine import FIFOEngine

router = APIRouter(prefix="/runs", tags=["runs"])
logger = logging.getLogger(__name__)


# Dependency injection (would be configured in main app)
def get_calculator() -> JournaledCalculator:
    """Get journaled calculator instance"""
    engine = FIFOEngine()
    # In real app, this would inject a proper DB adapter
    return JournaledCalculator(engine, db_adapter=None)


@router.post("", response_model=RunResponse, status_code=201)
async def create_run(
    request: CreateRunRequest,
    calculator: JournaledCalculator = Depends(get_calculator)
):
    """
    Create and execute a new COGS calculation run.
    
    Creates a run record, processes the sales data, and journals all changes.
    Returns 409 if tenant has an active run.
    """
    try:
        # Convert request data to domain models
        lots = []  # Would convert from request.lots_data
        sales = []  # Would convert from request.sales_data
        
        result = calculator.create_and_execute_run(
            tenant_id=request.tenant_id,
            lots=lots,
            sales=sales,
            mode=request.mode,
            start_month=request.start_month,
            created_by=None  # Would get from auth context
        )
        
        return RunResponse(
            run_id=result['run_id'],
            tenant_id=request.tenant_id,
            status=result['status'],
            started_at=datetime.now(),
            completed_at=datetime.now(),
            total_sales_processed=len(sales),
            total_cogs_calculated=float(result['total_cogs'])
        )
        
    except ValueError as e:
        if "active run" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Failed to create run: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=RunListResponse)
async def list_runs(
    tenant_id: str = Query(..., description="Tenant ID to filter runs"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=1000, description="Items per page"),
    calculator: JournaledCalculator = Depends(get_calculator)
):
    """
    List COGS runs for a tenant with optional filtering.
    
    Supports pagination and status filtering.
    """
    try:
        # In real implementation, this would query the database
        runs = []  # Would fetch from DB based on filters
        
        return RunListResponse(
            runs=runs,
            total=len(runs),
            page=page,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Failed to list runs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{run_id}", response_model=RunDetailResponse)
async def get_run_detail(
    run_id: str,
    calculator: JournaledCalculator = Depends(get_calculator)
):
    """
    Get detailed information about a specific run.
    
    Includes attributions, validation errors, and rollback status.
    """
    try:
        # Would fetch from database
        run_data = {}  # calculator._get_run(run_id)
        
        if not run_data:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        
        return RunDetailResponse(
            run_id=run_id,
            tenant_id=run_data.get('tenant_id', ''),
            status=run_data.get('status', ''),
            started_at=run_data.get('started_at', datetime.now()),
            completed_at=run_data.get('completed_at'),
            can_rollback=run_data.get('status') in ['completed', 'failed']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get run {run_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{run_id}/rollback", response_model=RollbackResponse)
async def rollback_run(
    run_id: str,
    calculator: JournaledCalculator = Depends(get_calculator)
):
    """
    Rollback a completed run.
    
    Restores inventory to pre-run state and invalidates COGS data.
    Idempotent - safe to call multiple times.
    """
    try:
        result = calculator.rollback_run(
            run_id=run_id,
            rollback_by=None  # Would get from auth context
        )
        
        return RollbackResponse(
            run_id=result['run_id'],
            rollback_run_id=result.get('rollback_run_id'),
            status=result['status'],
            restored_lots_count=result.get('restored_lots_count', 0),
            message=result['message']
        )
        
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Failed to rollback run {run_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{run_id}/journal-entry", response_model=JournalEntryResponse)
async def get_journal_entry(
    run_id: str,
    format: str = Query("csv", description="Format: csv, json, or text"),
    calculator: JournaledCalculator = Depends(get_calculator)
):
    """
    Generate journal entry for accounting systems.
    
    Returns formatted journal entry that can be imported into Xero, QuickBooks, etc.
    """
    try:
        if format not in ["csv", "json", "text"]:
            raise HTTPException(status_code=400, detail="Format must be csv, json, or text")
        
        content = calculator.generate_journal_entry(run_id, format)
        
        if not content:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        
        return JournalEntryResponse(
            run_id=run_id,
            format=format,
            content=content,
            generated_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate journal entry for run {run_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")