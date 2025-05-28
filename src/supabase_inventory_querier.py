# supabase_inventory_querier.py
"""
This script queries inventory data from a Supabase table.

Prerequisites:
1. Supabase project created and a table named 'purchase_lots' (or similar) exists 
   and is populated with inventory data. This table should ideally have columns like:
   - sku (TEXT)
   - original_unit_qty (INTEGER)
   - remaining_unit_qty (INTEGER)  <-- This is crucial for current balance
   - lot_id (TEXT, Primary Key or unique identifier for the lot)
   - received_date (DATE or TIMESTAMP)
   - po_number (TEXT)

2. Environment variables set for Supabase connection:
   - SUPABASE_URL: Your Supabase project URL.
   - SUPABASE_KEY: Your Supabase public anon key.

Usage:
   The script can be run directly. It will prompt for the type of query to perform.
   Ensure SUPABASE_URL and SUPABASE_KEY are set in your environment.
"""

import os
from supabase import create_client, Client
from collections import defaultdict

def get_supabase_client():
    """Initializes and returns the Supabase client."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set.")
        return None
    try:
        supabase: Client = create_client(url, key)
        return supabase
    except Exception as e:
        print(f"Error creating Supabase client: {e}")
        return None

def get_inventory_by_sku(supabase: Client, table_name: str = "purchase_lots"):
    """Queries and prints the total available inventory balance for each SKU."""
    try:
        # Assuming 'remaining_unit_qty' holds the current available stock for a lot
        # If not, adjust the query. If 'remaining_unit_qty' doesn't exist, this script
        # needs to be adapted based on how sales are deducted in Supabase.
        data, error = supabase.table(table_name).select("sku, remaining_unit_qty").execute()

        if hasattr(data, 'data') and hasattr(data, 'error'): # v2.x.x
            if data.error:
                print(f"Error querying inventory by SKU: {data.error}")
                return
            inventory_data = data.data
        elif isinstance(data, list) and len(data) > 0 and data[0] == 'data': # v1.x.x
            if error and error[1]:
                 print(f"Error querying inventory by SKU: {error[1]}")
                 return
            inventory_data = data[1]
        else:
            print(f"Could not parse inventory data from Supabase response: data={data}, error={error}")
            return

        if not inventory_data:
            print("No inventory data found.")
            return

        sku_balances = defaultdict(int)
        for item in inventory_data:
            if item.get("sku") and item.get("remaining_unit_qty") is not None:
                sku_balances[item["sku"]] += int(item["remaining_unit_qty"])
            else:
                print(f"Warning: Skipping item with missing SKU or remaining_unit_qty: {item}")

        if not sku_balances:
            print("No valid SKU balances to display.")
            return

        print("\n--- Inventory Balance by SKU ---")
        for sku, balance in sku_balances.items():
            print(f"SKU: {sku}, Total Available Balance: {balance}")
        print("-------------------------------")

    except Exception as e:
        print(f"An unexpected error occurred while querying inventory by SKU: {e}")

def get_inventory_by_lot(supabase: Client, table_name: str = "purchase_lots"):
    """Queries and prints the available inventory balance for each individual lot."""
    try:
        # Select relevant columns for lot details
        # Ensure 'lot_id' or a combination of fields (po_number, sku, received_date) uniquely identifies a lot.
        # We'll use po_number and sku as a proxy for lot identifier if lot_id is not standard.
        data, error = supabase.table(table_name).select(
            "po_number, sku, received_date, original_unit_qty, remaining_unit_qty"
        ).order('received_date', desc=False).execute()

        if hasattr(data, 'data') and hasattr(data, 'error'): # v2.x.x
            if data.error:
                print(f"Error querying inventory by lot: {data.error}")
                return
            lot_data = data.data
        elif isinstance(data, list) and len(data) > 0 and data[0] == 'data': # v1.x.x
            if error and error[1]:
                print(f"Error querying inventory by lot: {error[1]}")
                return
            lot_data = data[1]
        else:
            print(f"Could not parse lot data from Supabase response: data={data}, error={error}")
            return

        if not lot_data:
            print("No lot data found.")
            return

        print("\n--- Inventory Balance by Lot ---")
        for lot in lot_data:
            po = lot.get("po_number", "N/A")
            sku = lot.get("sku", "N/A")
            received = lot.get("received_date", "N/A")
            original_qty = lot.get("original_unit_qty", "N/A")
            remaining_qty = lot.get("remaining_unit_qty", "N/A")
            print(f"PO: {po}, SKU: {sku}, Received: {received}, Original Qty: {original_qty}, Remaining Qty: {remaining_qty}")
        print("------------------------------")

    except Exception as e:
        print(f"An unexpected error occurred while querying inventory by lot: {e}")

if __name__ == "__main__":
    supabase_client = get_supabase_client()
    if supabase_client:
        print("Supabase Inventory Querier")
        print("Ensure SUPABASE_URL and SUPABASE_KEY are set as environment variables.")
        print("Ensure the table 'purchase_lots' (or your configured table) exists and has inventory data, including a 'remaining_unit_qty' column.")

        while True:
            print("\nChoose an action:")
            print("1. View inventory balance by SKU")
            print("2. View inventory balance by Lot")
            print("3. Exit")
            choice = input("Enter your choice (1-3): ")

            if choice == '1':
                get_inventory_by_sku(supabase_client)
            elif choice == '2':
                get_inventory_by_lot(supabase_client)
            elif choice == '3':
                print("Exiting.")
                break
            else:
                print("Invalid choice. Please try again.")
    else:
        print("Failed to initialize Supabase client. Cannot perform queries.")

