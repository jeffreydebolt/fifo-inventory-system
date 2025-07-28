"""
Database models for multi-tenant FIFO COGS system.
These models represent the persistent storage schema.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from enum import Enum


class RunStatus(Enum):
    """Status of a COGS calculation run"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class COGSRun:
    """Represents a single COGS calculation run for a tenant"""
    run_id: str
    tenant_id: str
    status: RunStatus
    started_at: datetime
    completed_at: Optional[datetime]
    input_file_id: Optional[str]  # Reference to uploaded sales file
    error_message: Optional[str]
    created_by: Optional[str]  # User who initiated the run
    rollback_of_run_id: Optional[str]  # If this is a rollback, reference the original run
    
    # Statistics
    total_sales_processed: int = 0
    total_cogs_calculated: Decimal = Decimal('0')
    validation_errors_count: int = 0


@dataclass
class InventoryMovement:
    """Records every inventory change for audit trail"""
    movement_id: str
    tenant_id: str
    run_id: str
    lot_id: str
    sku: str
    movement_type: str  # 'sale', 'return', 'adjustment', 'rollback'
    quantity: int  # Positive for additions, negative for removals
    remaining_after: int
    unit_cost: Decimal
    created_at: datetime
    reference_id: Optional[str]  # Sale ID or other reference


@dataclass
class InventorySnapshot:
    """Point-in-time snapshot of inventory state"""
    snapshot_id: str
    tenant_id: str
    run_id: str
    lot_id: str
    sku: str
    remaining_quantity: int
    original_quantity: int
    unit_price: Decimal
    freight_cost_per_unit: Decimal
    received_date: datetime
    created_at: datetime
    is_current: bool  # True for latest state, False for historical


@dataclass
class COGSAttribution:
    """Detailed COGS attribution stored in database"""
    attribution_id: str
    tenant_id: str
    run_id: str
    sale_id: str
    sku: str
    sale_date: datetime
    quantity_sold: int
    total_cogs: Decimal
    average_unit_cost: Decimal
    created_at: datetime
    is_valid: bool = True  # Can be invalidated by rollback


@dataclass
class COGSAttributionDetail:
    """Line-item detail for each lot allocation"""
    detail_id: str
    attribution_id: str
    tenant_id: str
    lot_id: str
    quantity_allocated: int
    unit_cost: Decimal
    total_cost: Decimal


@dataclass
class COGSSummary:
    """Monthly COGS summary by SKU"""
    summary_id: str
    tenant_id: str
    run_id: str
    sku: str
    period: str  # YYYY-MM format
    total_quantity_sold: int
    total_cogs: Decimal
    average_unit_cost: Decimal
    created_at: datetime
    is_valid: bool = True  # Can be invalidated by rollback


@dataclass
class UploadedFile:
    """Track uploaded files for each tenant"""
    file_id: str
    tenant_id: str
    filename: str
    file_type: str  # 'sales', 'lots', etc.
    file_size: int
    uploaded_at: datetime
    uploaded_by: Optional[str]
    run_id: Optional[str]  # Which run processed this file
    processed: bool = False


@dataclass
class ValidationError:
    """Store validation errors from runs"""
    error_id: str
    tenant_id: str
    run_id: str
    error_type: str
    sku: Optional[str]
    message: str
    sale_date: Optional[datetime]
    quantity: Optional[int]
    created_at: datetime