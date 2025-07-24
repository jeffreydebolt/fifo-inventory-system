"""
Core data models for FIFO COGS calculation system.
These are pure Python dataclasses with no external dependencies.
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from enum import Enum


class TransactionType(Enum):
    SALE = "sale"
    RETURN = "return"


@dataclass
class PurchaseLot:
    """Represents a single purchase lot of inventory"""
    lot_id: str
    sku: str
    received_date: datetime
    original_quantity: int
    remaining_quantity: int
    unit_price: Decimal
    freight_cost_per_unit: Decimal
    tenant_id: Optional[str] = None
    
    @property
    def total_unit_cost(self) -> Decimal:
        """Total cost per unit including freight"""
        return self.unit_price + self.freight_cost_per_unit
    
    @property
    def is_exhausted(self) -> bool:
        """Check if this lot has no remaining inventory"""
        return self.remaining_quantity <= 0
    
    def allocate(self, quantity: int) -> 'LotAllocation':
        """Allocate units from this lot"""
        if quantity > self.remaining_quantity:
            raise ValueError(f"Cannot allocate {quantity} units from lot {self.lot_id} with only {self.remaining_quantity} remaining")
        
        allocation = LotAllocation(
            lot_id=self.lot_id,
            sku=self.sku,
            quantity=quantity,
            unit_cost=self.total_unit_cost,
            total_cost=self.total_unit_cost * Decimal(quantity)
        )
        
        self.remaining_quantity -= quantity
        return allocation
    
    def return_units(self, quantity: int) -> None:
        """Return units to this lot (for processing returns)"""
        self.remaining_quantity += quantity
        if self.remaining_quantity > self.original_quantity:
            raise ValueError(f"Cannot return {quantity} units to lot {self.lot_id}: would exceed original quantity")


@dataclass
class Sale:
    """Represents a single sale transaction"""
    sale_id: str
    sku: str
    sale_date: datetime
    quantity_sold: int
    transaction_type: TransactionType = TransactionType.SALE
    tenant_id: Optional[str] = None
    
    def __post_init__(self):
        """Determine transaction type based on quantity"""
        if self.quantity_sold < 0:
            self.transaction_type = TransactionType.RETURN
            self.quantity_sold = abs(self.quantity_sold)
    
    @property
    def is_return(self) -> bool:
        """Check if this is a return transaction"""
        return self.transaction_type == TransactionType.RETURN


@dataclass
class LotAllocation:
    """Represents an allocation of inventory from a specific lot to fulfill a sale"""
    lot_id: str
    sku: str
    quantity: int
    unit_cost: Decimal
    total_cost: Decimal


@dataclass
class COGSAttribution:
    """Detailed COGS attribution for a single sale"""
    sale_id: str
    sku: str
    sale_date: datetime
    quantity_sold: int
    allocations: List[LotAllocation] = field(default_factory=list)
    
    @property
    def total_cogs(self) -> Decimal:
        """Calculate total COGS for this sale"""
        return sum(alloc.total_cost for alloc in self.allocations)
    
    @property
    def average_unit_cost(self) -> Decimal:
        """Calculate average unit cost for this sale"""
        if self.quantity_sold == 0:
            return Decimal('0')
        return self.total_cogs / Decimal(self.quantity_sold)
    
    def add_allocation(self, allocation: LotAllocation) -> None:
        """Add a lot allocation to this attribution"""
        self.allocations.append(allocation)


@dataclass
class InventorySnapshot:
    """Represents the state of inventory at a point in time"""
    timestamp: datetime
    lots: List[PurchaseLot]
    
    def get_available_lots(self, sku: str, as_of_date: Optional[datetime] = None) -> List[PurchaseLot]:
        """Get available lots for a SKU, optionally filtered by date"""
        lots = [lot for lot in self.lots if lot.sku == sku and not lot.is_exhausted]
        
        if as_of_date:
            lots = [lot for lot in lots if lot.received_date <= as_of_date]
        
        # Sort by received date (FIFO order)
        return sorted(lots, key=lambda x: x.received_date)
    
    def total_quantity_by_sku(self, sku: str) -> int:
        """Get total remaining quantity for a SKU"""
        return sum(lot.remaining_quantity for lot in self.lots if lot.sku == sku)
    
    def total_value_by_sku(self, sku: str) -> Decimal:
        """Get total remaining value for a SKU"""
        return sum(
            lot.remaining_quantity * lot.total_unit_cost 
            for lot in self.lots if lot.sku == sku
        )


@dataclass
class COGSSummary:
    """Summary of COGS by SKU and period"""
    sku: str
    period: str  # Format: YYYY-MM
    total_quantity_sold: int
    total_cogs: Decimal
    average_unit_cost: Decimal
    
    @classmethod
    def from_attributions(cls, sku: str, period: str, attributions: List[COGSAttribution]) -> 'COGSSummary':
        """Create a summary from a list of attributions"""
        total_quantity = sum(attr.quantity_sold for attr in attributions)
        total_cogs = sum(attr.total_cogs for attr in attributions)
        avg_cost = total_cogs / Decimal(total_quantity) if total_quantity > 0 else Decimal('0')
        
        return cls(
            sku=sku,
            period=period,
            total_quantity_sold=total_quantity,
            total_cogs=total_cogs,
            average_unit_cost=avg_cost
        )


@dataclass
class ValidationError:
    """Represents a validation error in the data"""
    error_type: str
    sku: str
    message: str
    sale_date: Optional[datetime] = None
    quantity: Optional[int] = None