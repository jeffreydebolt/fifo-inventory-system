"""
Pydantic models for API requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


class CreateRunRequest(BaseModel):
    """Request to create a new COGS run"""
    tenant_id: str = Field(..., description="Tenant identifier")
    mode: str = Field(default="fifo", description="Calculation mode: 'fifo' or 'avg'")
    start_month: Optional[str] = Field(None, description="Starting month YYYY-MM")
    sales_data: Optional[List[Dict[str, Any]]] = Field(None, description="Sales data for processing")
    lots_data: Optional[List[Dict[str, Any]]] = Field(None, description="Lots data for processing")


class RunResponse(BaseModel):
    """Response for run operations"""
    run_id: str
    tenant_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_sales_processed: int = 0
    total_cogs_calculated: float = 0
    validation_errors_count: int = 0
    error_message: Optional[str] = None
    created_by: Optional[str] = None


class RunListResponse(BaseModel):
    """Response for listing runs"""
    runs: List[RunResponse]
    total: int
    page: int = 1
    limit: int = 50


class RollbackResponse(BaseModel):
    """Response for rollback operations"""
    run_id: str
    rollback_run_id: Optional[str] = None
    status: str
    restored_lots_count: int = 0
    message: str


class JournalEntryResponse(BaseModel):
    """Response for journal entry generation"""
    run_id: str
    format: str
    content: str
    generated_at: datetime


class ValidationErrorResponse(BaseModel):
    """Validation error details"""
    error_type: str
    sku: Optional[str] = None
    message: str
    sale_date: Optional[datetime] = None
    quantity: Optional[int] = None


class COGSAttributionResponse(BaseModel):
    """COGS attribution details"""
    attribution_id: str
    sale_id: str
    sku: str
    sale_date: datetime
    quantity_sold: int
    total_cogs: float
    average_unit_cost: float
    lot_allocations: List[Dict[str, Any]] = []


class RunDetailResponse(RunResponse):
    """Detailed run information"""
    attributions: List[COGSAttributionResponse] = []
    validation_errors: List[ValidationErrorResponse] = []
    inventory_movements_count: int = 0
    can_rollback: bool = True