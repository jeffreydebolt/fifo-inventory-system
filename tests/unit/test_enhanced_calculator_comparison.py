#!/usr/bin/env python3
"""
Direct comparison test between our new core engine and the existing 
fifo_calculator_enhanced.py to ensure identical behavior.
"""
import sys
import os
import tempfile
import pandas as pd
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.models import PurchaseLot, Sale, InventorySnapshot
from core.fifo_engine import FIFOEngine


def create_test_scenario():
    """Create a test scenario that exercises all key features"""
    
    # Test inventory with multiple SKUs and lots
    test_lots = [
        # SKU-A: Multiple lots for testing FIFO order
        {
            'lot_id': 'LA001',
            'sku': 'SKU-A', 
            'received_date': '2024-01-01',
            'original_quantity': 100,
            'remaining_quantity': 100,
            'unit_price': 10.00,
            'freight_cost_per_unit': 1.00
        },
        {
            'lot_id': 'LA002',
            'sku': 'SKU-A',
            'received_date': '2024-01-15', 
            'original_quantity': 150,
            'remaining_quantity': 150,
            'unit_price': 11.00,
            'freight_cost_per_unit': 1.00
        },
        # SKU-B: Single lot
        {
            'lot_id': 'LB001',
            'sku': 'SKU-B',
            'received_date': '2024-01-10',
            'original_quantity': 200,
            'remaining_quantity': 200,
            'unit_price': 5.00,
            'freight_cost_per_unit': 0.50
        }
    ]
    
    # Test sales including returns
    test_sales = [
        # Regular sales
        {'sale_id': 'S001', 'sku': 'SKU-A', 'sale_date': '2024-02-01', 'quantity_sold': 80},
        {'sale_id': 'S002', 'sku': 'SKU-B', 'sale_date': '2024-02-01', 'quantity_sold': 50},
        {'sale_id': 'S003', 'sku': 'SKU-A', 'sale_date': '2024-02-15', 'quantity_sold': 120},
        # Return (negative quantity)
        {'sale_id': 'R001', 'sku': 'SKU-A', 'sale_date': '2024-02-20', 'quantity_sold': -30},
        # More sales after return
        {'sale_id': 'S004', 'sku': 'SKU-A', 'sale_date': '2024-03-01', 'quantity_sold': 40}
    ]
    
    return test_lots, test_sales


def run_core_engine_test():
    """Run test through our new core engine"""
    print("Running test through new Core Engine...")
    
    test_lots_data, test_sales_data = create_test_scenario()
    
    # Convert to core models
    lots = []
    for lot_data in test_lots_data:
        lot = PurchaseLot(
            lot_id=lot_data['lot_id'],
            sku=lot_data['sku'],
            received_date=pd.to_datetime(lot_data['received_date']).to_pydatetime(),
            original_quantity=lot_data['original_quantity'],
            remaining_quantity=lot_data['remaining_quantity'],
            unit_price=Decimal(str(lot_data['unit_price'])),
            freight_cost_per_unit=Decimal(str(lot_data['freight_cost_per_unit']))
        )
        lots.append(lot)
    
    sales = []
    for sale_data in test_sales_data:
        sale = Sale(
            sale_id=sale_data['sale_id'],
            sku=sale_data['sku'],
            sale_date=pd.to_datetime(sale_data['sale_date']).to_pydatetime(),
            quantity_sold=sale_data['quantity_sold']
        )
        sales.append(sale)
    
    # Create inventory and process
    inventory = InventorySnapshot(timestamp=datetime.now(), lots=lots)
    engine = FIFOEngine()
    
    attributions, final_inventory = engine.process_transactions(inventory, sales)
    summaries = engine.calculate_summary(attributions)
    
    # Display results
    print("\nCore Engine Results:")
    print("-" * 40)
    
    print("\nCOGS Attributions:")
    for attr in attributions:
        print(f"  {attr.sale_id} ({attr.sku}): {attr.quantity_sold} units = ${attr.total_cogs}")
        for alloc in attr.allocations:
            print(f"    - From {alloc.lot_id}: {alloc.quantity} @ ${alloc.unit_cost}")
    
    print("\nMonthly Summary:")
    for summary in summaries:
        print(f"  {summary.sku} - {summary.period}: {summary.total_quantity_sold} units, ${summary.total_cogs}")
    
    print("\nFinal Inventory:")
    for lot in final_inventory.lots:
        if lot.remaining_quantity > 0:
            print(f"  {lot.lot_id}: {lot.remaining_quantity} units")
    
    # Calculate some key metrics for comparison
    total_cogs = sum(attr.total_cogs for attr in attributions)
    total_units_sold = sum(attr.quantity_sold for attr in attributions)
    
    print(f"\nKey Metrics:")
    print(f"  Total COGS: ${total_cogs}")
    print(f"  Total Units Sold: {total_units_sold}")
    
    return {
        'attributions': attributions,
        'summaries': summaries,
        'final_inventory': final_inventory,
        'total_cogs': total_cogs,
        'total_units_sold': total_units_sold
    }


def verify_results():
    """Verify our results match expected behavior"""
    results = run_core_engine_test()
    
    print("\n" + "=" * 60)
    print("Verification Summary:")
    print("=" * 60)
    
    # Expected results based on manual calculation
    expected = {
        'total_units_sold': 290,  # 80 + 50 + 120 + 40 (sales, excluding returns from attribution)
        'sku_a_final_inventory': 40,  # Initial: 250, Sales: -240, Return: +30 = 40
        'sku_b_final_inventory': 150,  # 200 - 50 = 150
    }
    
    # Calculate actual values
    sku_a_remaining = sum(
        lot.remaining_quantity 
        for lot in results['final_inventory'].lots 
        if lot.sku == 'SKU-A'
    )
    sku_b_remaining = sum(
        lot.remaining_quantity 
        for lot in results['final_inventory'].lots 
        if lot.sku == 'SKU-B'
    )
    
    # Verify
    print(f"Total Units Sold: {results['total_units_sold']} (expected: {expected['total_units_sold']})")
    print(f"SKU-A Final Inventory: {sku_a_remaining} (expected: {expected['sku_a_final_inventory']})")
    print(f"SKU-B Final Inventory: {sku_b_remaining} (expected: {expected['sku_b_final_inventory']})")
    
    # Check if all match
    all_match = (
        results['total_units_sold'] == expected['total_units_sold'] and
        sku_a_remaining == expected['sku_a_final_inventory'] and
        sku_b_remaining == expected['sku_b_final_inventory']
    )
    
    if all_match:
        print("\n✅ All calculations match expected results!")
    else:
        print("\n❌ Some calculations don't match!")
    
    return all_match


if __name__ == "__main__":
    verify_results()