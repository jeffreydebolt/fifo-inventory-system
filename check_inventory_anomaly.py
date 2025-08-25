#!/usr/bin/env python3
import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Supabase credentials
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set")
    exit(1)

# Create client
supabase = create_client(url, key)

# Query for lots where remaining > original
try:
    response = supabase.table("purchase_lots").select("*").execute()
    
    if hasattr(response, 'data'):
        lots = response.data
        anomalies = []
        
        for lot in lots:
            if lot['remaining_unit_qty'] > lot['original_unit_qty']:
                anomalies.append({
                    'lot_id': lot['lot_id'],
                    'po_number': lot['po_number'],
                    'sku': lot['sku'],
                    'original': lot['original_unit_qty'],
                    'remaining': lot['remaining_unit_qty'],
                    'difference': lot['remaining_unit_qty'] - lot['original_unit_qty']
                })
        
        if anomalies:
            print(f"\nFound {len(anomalies)} lots with remaining > original quantity:")
            print("-" * 100)
            print(f"{'Lot ID':<8} {'PO Number':<12} {'SKU':<15} {'Original':<10} {'Remaining':<10} {'Excess':<10}")
            print("-" * 100)
            
            for a in sorted(anomalies, key=lambda x: x['difference'], reverse=True):
                print(f"{a['lot_id']:<8} {a['po_number']:<12} {a['sku']:<15} "
                      f"{a['original']:<10} {a['remaining']:<10} {a['difference']:<10}")
        else:
            print("\nNo anomalies found - all lots have remaining <= original quantity")
            
        # Also check for any recently modified lots
        print(f"\n\nTotal lots in database: {len(lots)}")
        
except Exception as e:
    print(f"Error querying database: {e}")