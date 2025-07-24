"""
Validation logic for FIFO COGS calculation system.
"""
from typing import List, Optional, Set
from datetime import datetime
from decimal import Decimal

from .models import PurchaseLot, Sale, ValidationError


class FIFOValidator:
    """Validates data integrity for FIFO calculations"""
    
    def validate_sales_data(self, sales: List[Sale]) -> List[ValidationError]:
        """Validate sales data for consistency and correctness"""
        errors = []
        
        # Check for duplicate sale IDs
        sale_ids = [s.sale_id for s in sales]
        duplicates = self._find_duplicates(sale_ids)
        for dup_id in duplicates:
            errors.append(ValidationError(
                error_type="DUPLICATE_SALE_ID",
                sku="",
                message=f"Duplicate sale ID found: {dup_id}"
            ))
        
        # Validate individual sales
        for sale in sales:
            # Check for negative quantities (that aren't returns)
            if sale.quantity_sold == 0:
                errors.append(ValidationError(
                    error_type="ZERO_QUANTITY",
                    sku=sale.sku,
                    message=f"Sale {sale.sale_id} has zero quantity",
                    sale_date=sale.sale_date,
                    quantity=0
                ))
            
            # Check for empty SKU
            if not sale.sku or sale.sku.strip() == "":
                errors.append(ValidationError(
                    error_type="EMPTY_SKU",
                    sku="",
                    message=f"Sale {sale.sale_id} has empty SKU",
                    sale_date=sale.sale_date,
                    quantity=sale.quantity_sold
                ))
            
            # Check for future dates
            if sale.sale_date > datetime.now():
                errors.append(ValidationError(
                    error_type="FUTURE_DATE",
                    sku=sale.sku,
                    message=f"Sale {sale.sale_id} has future date: {sale.sale_date}",
                    sale_date=sale.sale_date,
                    quantity=sale.quantity_sold
                ))
        
        return errors
    
    def validate_purchase_lots(self, lots: List[PurchaseLot]) -> List[ValidationError]:
        """Validate purchase lot data"""
        errors = []
        
        # Check for duplicate lot IDs
        lot_ids = [lot.lot_id for lot in lots]
        duplicates = self._find_duplicates(lot_ids)
        for dup_id in duplicates:
            errors.append(ValidationError(
                error_type="DUPLICATE_LOT_ID",
                sku="",
                message=f"Duplicate lot ID found: {dup_id}"
            ))
        
        # Validate individual lots
        for lot in lots:
            # Check for negative quantities
            if lot.original_quantity <= 0:
                errors.append(ValidationError(
                    error_type="INVALID_LOT_QUANTITY",
                    sku=lot.sku,
                    message=f"Lot {lot.lot_id} has invalid original quantity: {lot.original_quantity}"
                ))
            
            if lot.remaining_quantity < 0:
                errors.append(ValidationError(
                    error_type="NEGATIVE_REMAINING",
                    sku=lot.sku,
                    message=f"Lot {lot.lot_id} has negative remaining quantity: {lot.remaining_quantity}"
                ))
            
            if lot.remaining_quantity > lot.original_quantity:
                errors.append(ValidationError(
                    error_type="EXCESS_REMAINING",
                    sku=lot.sku,
                    message=f"Lot {lot.lot_id} remaining quantity ({lot.remaining_quantity}) "
                            f"exceeds original ({lot.original_quantity})"
                ))
            
            # Check for negative costs
            if lot.unit_price < 0:
                errors.append(ValidationError(
                    error_type="NEGATIVE_PRICE",
                    sku=lot.sku,
                    message=f"Lot {lot.lot_id} has negative unit price: {lot.unit_price}"
                ))
            
            if lot.freight_cost_per_unit < 0:
                errors.append(ValidationError(
                    error_type="NEGATIVE_FREIGHT",
                    sku=lot.sku,
                    message=f"Lot {lot.lot_id} has negative freight cost: {lot.freight_cost_per_unit}"
                ))
            
            # Check for empty SKU
            if not lot.sku or lot.sku.strip() == "":
                errors.append(ValidationError(
                    error_type="EMPTY_SKU",
                    sku="",
                    message=f"Lot {lot.lot_id} has empty SKU"
                ))
        
        return errors
    
    def validate_date_availability(
        self, 
        lots: List[PurchaseLot], 
        sales: List[Sale]
    ) -> List[ValidationError]:
        """Validate that inventory exists before sale dates"""
        errors = []
        
        # Group lots by SKU
        lots_by_sku = {}
        for lot in lots:
            if lot.sku not in lots_by_sku:
                lots_by_sku[lot.sku] = []
            lots_by_sku[lot.sku].append(lot)
        
        # Check each sale
        for sale in sales:
            if sale.is_return:
                continue  # Skip returns for date validation
            
            sku_lots = lots_by_sku.get(sale.sku, [])
            
            # Find lots available before sale date
            available_lots = [
                lot for lot in sku_lots 
                if lot.received_date <= sale.sale_date and lot.remaining_quantity > 0
            ]
            
            if not available_lots:
                # Find earliest available lot
                future_lots = [
                    lot for lot in sku_lots 
                    if lot.remaining_quantity > 0
                ]
                
                if future_lots:
                    earliest = min(future_lots, key=lambda x: x.received_date)
                    days_diff = (earliest.received_date - sale.sale_date).days
                    
                    errors.append(ValidationError(
                        error_type="SALE_BEFORE_INVENTORY",
                        sku=sale.sku,
                        message=f"Sale on {sale.sale_date.strftime('%Y-%m-%d')} but "
                                f"earliest inventory is {earliest.received_date.strftime('%Y-%m-%d')} "
                                f"({days_diff} days later)",
                        sale_date=sale.sale_date,
                        quantity=sale.quantity_sold
                    ))
                else:
                    errors.append(ValidationError(
                        error_type="NO_INVENTORY_FOR_SKU",
                        sku=sale.sku,
                        message=f"No inventory found for SKU {sale.sku}",
                        sale_date=sale.sale_date,
                        quantity=sale.quantity_sold
                    ))
        
        return errors
    
    def validate_sufficient_inventory(
        self, 
        lots: List[PurchaseLot], 
        sales: List[Sale]
    ) -> List[ValidationError]:
        """Validate that there's sufficient inventory for all sales"""
        errors = []
        
        # Calculate total demand by SKU
        demand_by_sku = {}
        for sale in sales:
            if not sale.is_return:
                demand_by_sku[sale.sku] = demand_by_sku.get(sale.sku, 0) + sale.quantity_sold
            else:
                # Returns reduce demand
                demand_by_sku[sale.sku] = demand_by_sku.get(sale.sku, 0) - sale.quantity_sold
        
        # Calculate total supply by SKU
        supply_by_sku = {}
        for lot in lots:
            supply_by_sku[lot.sku] = supply_by_sku.get(lot.sku, 0) + lot.remaining_quantity
        
        # Check for insufficient inventory
        for sku, demand in demand_by_sku.items():
            supply = supply_by_sku.get(sku, 0)
            if supply < demand:
                errors.append(ValidationError(
                    error_type="INSUFFICIENT_TOTAL_INVENTORY",
                    sku=sku,
                    message=f"Total demand ({demand}) exceeds supply ({supply}) for SKU {sku}",
                    quantity=demand - supply
                ))
        
        return errors
    
    def _find_duplicates(self, items: List[str]) -> Set[str]:
        """Find duplicate items in a list"""
        seen = set()
        duplicates = set()
        for item in items:
            if item in seen:
                duplicates.add(item)
            seen.add(item)
        return duplicates
    
    def validate_all(
        self, 
        lots: List[PurchaseLot], 
        sales: List[Sale]
    ) -> List[ValidationError]:
        """Run all validations and return combined errors"""
        all_errors = []
        
        # Run individual validations
        all_errors.extend(self.validate_sales_data(sales))
        all_errors.extend(self.validate_purchase_lots(lots))
        all_errors.extend(self.validate_date_availability(lots, sales))
        all_errors.extend(self.validate_sufficient_inventory(lots, sales))
        
        return all_errors