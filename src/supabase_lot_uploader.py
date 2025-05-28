# supabase_lot_uploader.py
"""
This script uploads purchase lot data from a CSV file to a Supabase table.

Prerequisites:
1. Supabase project created and a table named 'purchase_lots' exists.
   The 'purchase_lots' table should have columns like:
   - po_number (TEXT, Primary Key or part of a composite key)
   - sku (TEXT)
   - received_date (DATE or TIMESTAMP)
   - original_unit_qty (INTEGER)
   - unit_price (NUMERIC)
   - freight_cost_per_unit (NUMERIC)
   - remaining_unit_qty (INTEGER, NOT NULL)
   - (Optional) lot_id (TEXT, Primary Key, if not using po_number + sku + received_date as composite)

2. Environment variables set for Supabase connection:
   - SUPABASE_URL: Your Supabase project URL.
   - SUPABASE_KEY: Your Supabase public anon key (or service role key if necessary, with appropriate security considerations).

CSV File Format:
The input CSV file should have a header row and columns corresponding to the 
Supabase table, for example:
PO_Number,SKU,Received_Date,Original_Unit_Qty,Unit_Price,Actual_Freight_Cost_Per_Unit
PO123,SKU001,2023-01-15,100,10.50,1.20
...
"""

import os
import csv
from supabase import create_client, Client
from datetime import datetime

# Configuration
SUPABASE_TABLE_NAME = "purchase_lots"

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

def upload_lots_from_csv(supabase: Client, csv_file_path: str):
    """Reads lot data from a CSV file and uploads it to Supabase."""
    records_to_insert = []
    try:
        with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            expected_headers = ["PO_Number", "SKU", "Received_Date", "Original_Unit_Qty", "Unit_Price", "Actual_Freight_Cost_Per_Unit"]
            if not all(header in reader.fieldnames for header in expected_headers):
                print(f"Error: CSV file must contain at least the headers: {', '.join(expected_headers)}")
                print(f"Found headers: {', '.join(reader.fieldnames)}")
                # Allow if 'remaining_unit_qty' is also present, but primary ones must be there.
                if not all(h in reader.fieldnames for h in ["PO_Number", "SKU", "Received_Date"]):
                     return False

            for row_number, row in enumerate(reader, 1):
                try:
                    # Skip row if essential fields are empty (likely a blank row)
                    if not row.get("PO_Number") or not row.get("SKU") or not row.get("Received_Date"):
                        print(f"Skipping row {row_number} due to missing essential data (PO_Number, SKU, or Received_Date): {row}")
                        continue

                    # Clean numeric strings by removing commas
                    original_unit_qty_str = str(row["Original_Unit_Qty"]).replace(',', '')
                    unit_price_str = str(row["Unit_Price"]).replace(',', '')
                    freight_cost_per_unit_str = str(row["Actual_Freight_Cost_Per_Unit"]).replace(',', '')
                    
                    # Ensure values are not empty strings before conversion, default to 0 if so after cleaning
                    original_unit_qty_str = original_unit_qty_str if original_unit_qty_str.strip() else "0"
                    unit_price_str = unit_price_str if unit_price_str.strip() else "0.0"
                    freight_cost_per_unit_str = freight_cost_per_unit_str if freight_cost_per_unit_str.strip() else "0.0"

                    original_qty = int(float(original_unit_qty_str)) # Convert to float first for decimals then int

                    record = {
                        "po_number": str(row["PO_Number"]),
                        "sku": str(row["SKU"]),
                        "received_date": datetime.strptime(row["Received_Date"], "%Y-%m-%d").strftime("%Y-%m-%d"),
                        "original_unit_qty": original_qty,
                        "unit_price": float(unit_price_str),
                        "freight_cost_per_unit": float(freight_cost_per_unit_str),
                        "remaining_unit_qty": original_qty  # Set remaining_unit_qty to original_unit_qty for new lots
                    }
                    records_to_insert.append(record)
                except ValueError as ve:
                    print(f"Skipping row {row_number} due to data conversion error: {row}. Error: {ve}")
                    continue
                except KeyError as ke:
                    print(f"Skipping row {row_number} due to missing key: {ke} in row {row}.")
                    continue

        if not records_to_insert:
            print("No valid records found in CSV to upload.")
            return False

        print(f"Attempting to insert {len(records_to_insert)} records into '{SUPABASE_TABLE_NAME}'...")
        data, error = supabase.table(SUPABASE_TABLE_NAME).insert(records_to_insert).execute()
        
        if hasattr(data, 'data') and hasattr(data, 'error'): # Likely v2.x.x
             if data.error:
                print(f"Error inserting data: {data.error}")
                return False
             else:
                print(f"Successfully inserted {len(data.data)} records.")
                return True
        elif isinstance(data, list) and len(data) > 0 and data[0] == 'data': # Heuristic for v1.x.x
            actual_data = data[1]
            if error and error[1]:
                print(f"Error inserting data: {error[1]}")
                return False
            else:
                print(f"Successfully inserted {len(actual_data)} records.")
                return True
        else: 
            print(f"Data insertion response: data={data}, error={error}")
            print("Could not definitively determine success from response structure. Please check Supabase.")
            if error and ( (isinstance(error, tuple) and len(error) > 1 and error[1]) or (hasattr(error, 'message') and error.message) ):
                return False
            elif data and hasattr(data, 'data') and len(data.data) == len(records_to_insert):
                return True 
            elif data and isinstance(data, list) and len(data) > 1 and isinstance(data[1], list) and len(data[1]) == len(records_to_insert):
                return True
            return False

    except FileNotFoundError:
        print(f"Error: CSV file not found at {csv_file_path}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

if __name__ == "__main__":
    supabase_client = get_supabase_client()
    if supabase_client:
        csv_path = "lots_to_upload.csv"

        print(f"Please ensure your Supabase URL and Key are set as environment variables (SUPABASE_URL, SUPABASE_KEY).")
        print(f"Ensure the table '{SUPABASE_TABLE_NAME}' exists in Supabase with appropriate columns (including 'remaining_unit_qty' as NOT NULL).")
        print(f"Ensure the CSV file '{csv_path}' exists and is correctly formatted.")
        
        if not os.path.exists(csv_path):
            print(f"Creating a dummy '{csv_path}' for demonstration purposes.")
            dummy_data = [
                ["PO_Number", "SKU", "Received_Date", "Original_Unit_Qty", "Unit_Price", "Actual_Freight_Cost_Per_Unit"],
                ["PO001", "SKU101", "2024-01-15", "100", "10.50", "1.20"],
                ["PO002", "SKU102", "2024-01-20", "2,000", "20.00", "2.50"],
                ["PO003", "SKU101", "2024-02-10", "50", "10.25", "1.15"]
            ]
            with open(csv_path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(dummy_data)
            print(f"Dummy '{csv_path}' created. You should replace it with your actual data.")

        user_ready = input("Are you ready to proceed with uploading? (yes/no): ")
        if user_ready.lower() == 'yes':
            success = upload_lots_from_csv(supabase_client, csv_path)
            if success:
                print("Lot data upload process completed successfully.")
            else:
                print("Lot data upload process failed. Please check the error messages above and your Supabase table logs/structure.")
        else:
            print("Upload cancelled by user.")

