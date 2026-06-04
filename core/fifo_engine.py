"""
Core FIFO (First In, First Out) engine for COGS calculation.
Pure business logic with no external dependencies.
"""
from typing import List, Dict, Tuple, Optional
from decimal import Decimal
from datetime import datetime
import logging

from .models import (
    PurchaseLot, Sale, COGSAttribution, InventorySnapshot,
    COGSSummary, ValidationError, TransactionType, Shortfall
)


class FIFOEngine:
    """Core FIFO calculation engine"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.validation_errors: List[ValidationError] = []
        self.shortfalls: List[Shortfall] = []
    
    def process_transactions(
        self, 
        initial_inventory: InventorySnapshot,
        sales: List[Sale],
        snapshot_timestamp: Optional[datetime] = None,
        allow_partial_shortfalls: bool = False,
    ) -> Tuple[List[COGSAttribution], InventorySnapshot]:
        """
        Process sales transactions using FIFO logic.
        
        Args:
            initial_inventory: Starting inventory state
            sales: List of sales to process
            
        Returns:
            Tuple of (COGS attributions, final inventory snapshot)
        """
        # Create a working copy of inventory
        working_inventory = InventorySnapshot(
            timestamp=snapshot_timestamp or datetime.now(),
            lots=[self._copy_lot(lot) for lot in initial_inventory.lots]
        )
        
        # Separate returns and sales
        returns = [s for s in sales if s.is_return]
        regular_sales = [s for s in sales if not s.is_return]
        
        # Process returns first
        self._process_returns(working_inventory, returns)
        
        # Sort sales by date
        sorted_sales = sorted(regular_sales, key=lambda x: x.sale_date)
        
        # Process each sale
        attributions = []
        for sale in sorted_sales:
            attribution = self._process_single_sale(
                working_inventory,
                sale,
                allow_partial_shortfalls=allow_partial_shortfalls,
            )
            if attribution:
                attributions.append(attribution)
        
        return attributions, working_inventory
    
    def _process_returns(self, inventory: InventorySnapshot, returns: List[Sale]) -> None:
        """Process return transactions by adding inventory back to oldest lots"""
        for return_sale in returns:
            self.logger.info(f"Processing return for SKU {return_sale.sku}: {return_sale.quantity_sold} units")
            
            # Get lots for this SKU sorted by date (oldest first)
            sku_lots = sorted(
                [lot for lot in inventory.lots if lot.sku == return_sale.sku],
                key=lambda x: x.received_date
            )
            
            if not sku_lots:
                self.logger.warning(f"No lots found for return of SKU {return_sale.sku}")
                continue
            
            # Add units back to the oldest lot
            oldest_lot = sku_lots[0]
            try:
                oldest_lot.return_units(return_sale.quantity_sold)
                self.logger.info(
                    f"Returned {return_sale.quantity_sold} units to lot {oldest_lot.lot_id}. "
                    f"New quantity: {oldest_lot.remaining_quantity}"
                )
            except ValueError as e:
                self.logger.error(f"Error processing return: {e}")
                self.validation_errors.append(ValidationError(
                    error_type="RETURN_ERROR",
                    sku=return_sale.sku,
                    message=str(e),
                    sale_date=return_sale.sale_date,
                    quantity=return_sale.quantity_sold
                ))
    
    def _process_single_sale(
        self, 
        inventory: InventorySnapshot, 
        sale: Sale,
        allow_partial_shortfalls: bool = False,
    ) -> Optional[COGSAttribution]:
        """Process a single sale transaction"""
        attribution = COGSAttribution(
            sale_id=sale.sale_id,
            sku=sale.sku,
            sale_date=sale.sale_date,
            quantity_sold=sale.quantity_sold
        )
        
        # Get available lots for this SKU as of the sale date
        available_lots = inventory.get_available_lots(sale.sku, sale.sale_date)
        
        if not available_lots:
            message = f"No inventory available for SKU {sale.sku} on {sale.sale_date}"
            self.shortfalls.append(Shortfall(
                sale_id=sale.sale_id,
                sku=sale.sku,
                sale_date=sale.sale_date,
                requested_quantity=sale.quantity_sold,
                allocated_quantity=0,
                shortfall_quantity=sale.quantity_sold,
                available_quantity=0,
                reason="NO_INVENTORY",
                message=message,
            ))
            self.validation_errors.append(ValidationError(
                error_type="NO_INVENTORY",
                sku=sale.sku,
                message=message,
                sale_date=sale.sale_date,
                quantity=sale.quantity_sold
            ))
            return None
        
        # Check if we have enough total inventory
        total_available = sum(lot.remaining_quantity for lot in available_lots)
        if total_available < sale.quantity_sold:
            message = (f"Insufficient inventory for SKU {sale.sku}. "
                       f"Needed: {sale.quantity_sold}, Available: {total_available}")
            self.shortfalls.append(Shortfall(
                sale_id=sale.sale_id,
                sku=sale.sku,
                sale_date=sale.sale_date,
                requested_quantity=sale.quantity_sold,
                allocated_quantity=total_available if allow_partial_shortfalls else 0,
                shortfall_quantity=sale.quantity_sold - total_available,
                available_quantity=total_available,
                reason="INSUFFICIENT_INVENTORY",
                message=message,
            ))
            self.validation_errors.append(ValidationError(
                error_type="INSUFFICIENT_INVENTORY",
                sku=sale.sku,
                message=message,
                sale_date=sale.sale_date,
                quantity=sale.quantity_sold
            ))
            if not allow_partial_shortfalls:
                return None
        
        # Allocate from lots using FIFO
        remaining_to_allocate = min(sale.quantity_sold, total_available)
        
        for lot in available_lots:
            if remaining_to_allocate <= 0:
                break
            
            # Calculate how much we can take from this lot
            quantity_from_lot = min(remaining_to_allocate, lot.remaining_quantity)
            
            # Allocate from the lot
            try:
                allocation = lot.allocate(quantity_from_lot)
                attribution.add_allocation(allocation)
                remaining_to_allocate -= quantity_from_lot
                
                self.logger.debug(
                    f"Allocated {quantity_from_lot} units from lot {lot.lot_id} "
                    f"at ${lot.total_unit_cost:.2f}/unit"
                )
            except ValueError as e:
                self.logger.error(f"Error allocating from lot {lot.lot_id}: {e}")
                self.validation_errors.append(ValidationError(
                    error_type="ALLOCATION_ERROR",
                    sku=sale.sku,
                    message=str(e),
                    sale_date=sale.sale_date,
                    quantity=quantity_from_lot
                ))
        
        if remaining_to_allocate > 0:
            self.logger.error(
                f"Failed to fully allocate sale {sale.sale_id}. "
                f"Remaining: {remaining_to_allocate}"
            )
            return None
        
        allocated_quantity = sum(allocation.quantity for allocation in attribution.allocations)
        if allow_partial_shortfalls and allocated_quantity < sale.quantity_sold:
            attribution.quantity_sold = allocated_quantity

        return attribution if attribution.allocations else None
    
    def calculate_summary(
        self, 
        attributions: List[COGSAttribution]
    ) -> List[COGSSummary]:
        """Calculate COGS summary by SKU and month"""
        # Group attributions by SKU and month
        grouped: Dict[Tuple[str, str], List[COGSAttribution]] = {}
        
        for attr in attributions:
            sku = attr.sku
            period = attr.sale_date.strftime('%Y-%m')
            key = (sku, period)
            
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(attr)
        
        # Create summaries
        summaries = []
        for (sku, period), attrs in grouped.items():
            summary = COGSSummary.from_attributions(sku, period, attrs)
            summaries.append(summary)
        
        # Sort by SKU and period
        summaries.sort(key=lambda x: (x.sku, x.period))
        
        return summaries
    
    def _copy_lot(self, lot: PurchaseLot) -> PurchaseLot:
        """Create a deep copy of a purchase lot"""
        return PurchaseLot(
            lot_id=lot.lot_id,
            sku=lot.sku,
            received_date=lot.received_date,
            original_quantity=lot.original_quantity,
            remaining_quantity=lot.remaining_quantity,
            unit_price=lot.unit_price,
            freight_cost_per_unit=lot.freight_cost_per_unit
        )
    
    def get_validation_errors(self) -> List[ValidationError]:
        """Get all validation errors encountered during processing"""
        return self.validation_errors.copy()

    def get_shortfalls(self) -> List[Shortfall]:
        """Get explicit shortfalls encountered during processing."""
        return self.shortfalls.copy()
    
    def clear_validation_errors(self) -> None:
        """Clear all validation errors"""
        self.validation_errors.clear()
        self.shortfalls.clear()