#!/usr/bin/env python3
"""
Debug inventory sources
"""
import sys
sys.path.append('/Users/jeffreydebolt/Documents/fifo')

from api.services.supabase_service import supabase_service

# Check what current inventory returns
current_inventory = supabase_service.get_current_inventory("test_tenant")
print("=== Current (Demo) Inventory ===")
print(current_inventory)
print(f"Shape: {current_inventory.shape}")
if not current_inventory.empty:
    print(f"SKUs: {current_inventory['sku'].tolist()}")
    print(f"Quantities: {current_inventory['remaining_quantity'].tolist()}")
    print(f"Unit prices: {current_inventory['unit_price'].tolist()}")
    print(f"Freight costs: {current_inventory['freight_cost_per_unit'].tolist()}")