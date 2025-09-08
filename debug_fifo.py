#!/usr/bin/env python3
"""
Debug FIFO calculation locally
"""
import pandas as pd
from api.services.supabase_service import SupabaseService

# Create test data
lots_data = {
    'lot_id': ['LOT001'],
    'sku': ['ABC-123'], 
    'received_date': ['2025-07-01'],
    'original_quantity': [100],
    'remaining_quantity': [100],
    'unit_price': [10],
    'freight_cost_per_unit': [1]
}

sales_data = {
    'SKU': ['DEF-456', 'ABC-123'],
    'Quantity_Sold': [75, 150], 
    'Sale_Month_Str': ['25-Jul', '25-Jul']
}

lots_df = pd.DataFrame(lots_data)
sales_df = pd.DataFrame(sales_data)

print("Lots DataFrame:")
print(lots_df)
print("\nSales DataFrame:")
print(sales_df)

# Create service instance (will work in demo mode)
service = SupabaseService()

# Test the FIFO calculation directly
result = service._calculate_fifo('demo_tenant', 'test_run', lots_df, sales_df)

print("\nFIFO Calculation Result:")
print(result)