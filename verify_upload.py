#!/usr/bin/env python3
import os
from supabase import create_client

# Get Supabase credentials
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set")
    exit(1)

# Create client
supabase = create_client(url, key)

# Query for recently uploaded lots
try:
    # Get the last 10 lots ordered by lot_id descending
    response = supabase.table("purchase_lots").select("*").order("lot_id", desc=True).limit(10).execute()
    
    if hasattr(response, 'data'):
        lots = response.data
        print(f"\nFound {len(lots)} recent lots:")
        print("-" * 80)
        for lot in lots:
            print(f"Lot ID: {lot['lot_id']}, PO: {lot['po_number']}, SKU: {lot['sku']}, "
                  f"Qty: {lot['original_unit_qty']}, Date: {lot['received_date']}")
    else:
        print("Could not retrieve data")
        
except Exception as e:
    print(f"Error querying lots: {e}")