#!/usr/bin/env python3
import os
import csv
from supabase import create_client
from datetime import datetime

# Get Supabase credentials
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set")
    exit(1)

# Create client
supabase = create_client(url, key)

# Read and process July lots
records_to_insert = []

with open('july_missing_lots.csv', 'r') as f:
    reader = csv.DictReader(f)
    
    for row in reader:
        # Clean and parse date (M/D/YY format)
        date_str = row['Received_Date']
        # Parse M/D/YY format - the 25 means 2025
        date_obj = datetime.strptime(date_str, "%m/%d/%y")
        # For 2-digit years, Python interprets 00-68 as 2000-2068, 69-99 as 1969-1999
        # So 25 is already correctly 2025
        
        # Clean numeric values (remove $, commas, spaces)
        def clean_number(val):
            return val.replace('$', '').replace(',', '').strip()
        
        original_qty = int(clean_number(row['Original_Unit_Qty']))
        
        record = {
            "po_number": row['PO_Number'],
            "sku": row['SKU'],
            "received_date": date_obj.strftime("%Y-%m-%d"),
            "original_unit_qty": original_qty,
            "unit_price": float(clean_number(row['Unit_Price'])),
            "freight_cost_per_unit": float(clean_number(row['Actual_Freight_Cost_Per_Unit'])),
            "remaining_unit_qty": original_qty
        }
        records_to_insert.append(record)

print(f"Prepared {len(records_to_insert)} records for upload")
print("\nFirst 3 records as preview:")
for i, rec in enumerate(records_to_insert[:3]):
    print(f"{i+1}. PO: {rec['po_number']}, SKU: {rec['sku']}, Date: {rec['received_date']}, Qty: {rec['original_unit_qty']}")

# Auto-confirm upload
confirm = 'yes'
print("\nProceeding with upload...")
if confirm.lower() == 'yes':
    try:
        response = supabase.table("purchase_lots").insert(records_to_insert).execute()
        
        if hasattr(response, 'data') and response.data:
            print(f"\nSuccessfully uploaded {len(response.data)} lots!")
            print("\nUploaded lot IDs:")
            for lot in response.data[:5]:  # Show first 5
                print(f"  - Lot ID: {lot['lot_id']}, PO: {lot['po_number']}, SKU: {lot['sku']}")
            if len(response.data) > 5:
                print(f"  ... and {len(response.data) - 5} more")
        else:
            print("Upload may have failed - please check the database")
            
    except Exception as e:
        print(f"Error during upload: {e}")
else:
    print("Upload cancelled")