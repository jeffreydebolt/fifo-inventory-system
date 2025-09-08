#!/usr/bin/env python3
"""
Direct debug of FIFO processing
"""
import sys
sys.path.append('/Users/jeffreydebolt/Documents/fifo')

import pandas as pd
from api.services.supabase_service import supabase_service, _global_file_cache

# Simulate file uploads
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

print("=== Test Data ===")
print("Lots DataFrame:")
print(lots_df)
print("\nSales DataFrame:")  
print(sales_df)

# Store in global cache directly
lots_file_id = "test_lots_123"
sales_file_id = "test_sales_456"

_global_file_cache[lots_file_id] = lots_df
_global_file_cache[sales_file_id] = sales_df

print(f"\n=== Global Cache ===")
print(f"Cache keys: {list(_global_file_cache.keys())}")
print(f"Lots in cache: {lots_file_id in _global_file_cache}")
print(f"Sales in cache: {sales_file_id in _global_file_cache}")

# Test FIFO processing
print(f"\n=== FIFO Processing ===")
try:
    result = supabase_service.process_fifo_with_database(
        tenant_id="test_tenant",
        lots_file_id=lots_file_id, 
        sales_file_id=sales_file_id
    )
    print(f"FIFO Result: {result}")
except Exception as e:
    print(f"Error during FIFO processing: {e}")
    import traceback
    traceback.print_exc()