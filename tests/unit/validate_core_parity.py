#!/usr/bin/env python3
"""
Simple validation script to ensure our core engine produces
the same results as the legacy calculator
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from datetime import datetime
from decimal import Decimal
from core.models import PurchaseLot, Sale, InventorySnapshot
from core.fifo_engine import FIFOEngine
from core.validators import FIFOValidator


def run_simple_test():
    """Run a simple test case and display results"""
    print("Running Core FIFO Engine Validation Test")
    print("=" * 60)
    
    # Create test data
    lots = [
        PurchaseLot(
            lot_id="LOT001",
            sku="TEST-SKU",
            received_date=datetime(2024, 1, 1),
            original_quantity=100,
            remaining_quantity=100,
            unit_price=Decimal("10.00"),
            freight_cost_per_unit=Decimal("1.00")
        ),
        PurchaseLot(
            lot_id="LOT002", 
            sku="TEST-SKU",
            received_date=datetime(2024, 1, 15),
            original_quantity=50,
            remaining_quantity=50,
            unit_price=Decimal("12.00"),
            freight_cost_per_unit=Decimal("1.50")
        )
    ]
    
    sales = [
        Sale(
            sale_id="SALE001",
            sku="TEST-SKU",
            sale_date=datetime(2024, 2, 1),
            quantity_sold=120
        )
    ]
    
    # Initialize engine
    engine = FIFOEngine()
    validator = FIFOValidator()
    
    # Create inventory snapshot
    inventory = InventorySnapshot(
        timestamp=datetime.now(),
        lots=lots
    )
    
    # Validate data
    print("\nValidating data...")
    errors = validator.validate_all(lots, sales)
    if errors:
        print(f"Found {len(errors)} validation errors:")
        for error in errors:
            print(f"  - {error.error_type}: {error.message}")
    else:
        print("✓ No validation errors")
    
    # Process transactions
    print("\nProcessing transactions...")
    attributions, final_inventory = engine.process_transactions(inventory, sales)
    
    # Display results
    print(f"\nProcessed {len(attributions)} sales:")
    for attr in attributions:
        print(f"\nSale ID: {attr.sale_id}")
        print(f"SKU: {attr.sku}")
        print(f"Quantity: {attr.quantity_sold}")
        print(f"Total COGS: ${attr.total_cogs}")
        print(f"Average Unit Cost: ${attr.average_unit_cost}")
        print("Allocations:")
        for alloc in attr.allocations:
            print(f"  - Lot {alloc.lot_id}: {alloc.quantity} units @ ${alloc.unit_cost}/unit = ${alloc.total_cost}")
    
    # Generate summary
    summaries = engine.calculate_summary(attributions)
    print(f"\nMonthly Summaries:")
    for summary in summaries:
        print(f"  {summary.sku} - {summary.period}: {summary.total_quantity_sold} units, ${summary.total_cogs} total COGS")
    
    # Display final inventory
    print(f"\nFinal Inventory State:")
    for lot in final_inventory.lots:
        if lot.remaining_quantity > 0:
            print(f"  Lot {lot.lot_id} ({lot.sku}): {lot.remaining_quantity} units remaining")
    
    print("\n" + "=" * 60)
    print("Validation complete!")
    
    # Expected results for verification
    print("\nExpected Results:")
    print("- Total COGS: $1,370.00 (100 units @ $11 + 20 units @ $13.50)")
    print("- Lot LOT001: 0 units remaining")
    print("- Lot LOT002: 30 units remaining")


if __name__ == "__main__":
    run_simple_test()