#!/usr/bin/env python3
"""
Quick fix for the inventory querier parsing issue
Save this as 'inventory_querier_fixed.py' and run it
"""

import os
from supabase import create_client, Client
from collections import defaultdict

# Initialize Supabase client
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: Please set SUPABASE_URL and SUPABASE_KEY environment variables")
    exit(1)

supabase: Client = create_client(url, key)

def view_inventory_by_sku():
    """View inventory grouped by SKU"""
    try:
        # Query the data
        response = supabase.table('purchase_lots').select("sku, remaining_unit_qty").execute()
        
        # Group by SKU
        sku_totals = defaultdict(int)
        for item in response.data:
            sku_totals[item['sku']] += item['remaining_unit_qty']
        
        # Display results
        print("\n" + "="*60)
        print(f"{'SKU':<20} {'Total Remaining Qty':>20}")
        print("="*60)
        
        for sku, qty in sorted(sku_totals.items()):
            if qty > 0:  # Only show SKUs with inventory
                print(f"{sku:<20} {qty:>20,}")
        
        print("="*60)
        print(f"Total SKUs with inventory: {len([q for q in sku_totals.values() if q > 0])}")
        print(f"Total units in inventory: {sum(sku_totals.values()):,}")
        
    except Exception as e:
        print(f"Error: {e}")

def view_inventory_by_lot():
    """View all lots with remaining inventory"""
    try:
        # Query the data
        response = supabase.table('purchase_lots').select("*").order("sku", desc=False).order("received_date", desc=False).execute()
        
        print("\n" + "="*100)
        print(f"{'Lot ID':<10} {'PO Number':<15} {'SKU':<20} {'Received':<12} {'Remaining':>10} {'Unit Price':>10}")
        print("="*100)
        
        for lot in response.data:
            if lot['remaining_unit_qty'] > 0:
                print(f"{lot.get('lot_id', 'N/A'):<10} {lot.get('po_number', 'N/A'):<15} {lot['sku']:<20} {lot.get('received_date', 'N/A'):<12} {lot['remaining_unit_qty']:>10,} ${lot.get('unit_price', 0):>9.2f}")
        
        print("="*100)
        
    except Exception as e:
        print(f"Error: {e}")

def main():
    while True:
        print("\n📦 Inventory Status")
        print("1. View inventory by SKU")
        print("2. View inventory by Lot")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            view_inventory_by_sku()
        elif choice == '2':
            view_inventory_by_lot()
        elif choice == '3':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
