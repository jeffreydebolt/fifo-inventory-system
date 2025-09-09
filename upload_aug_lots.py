#!/usr/bin/env python3
"""
Upload August lots data to Supabase
Specifically designed for aug_lots_to_upload.csv
"""

import os
import csv
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

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

def upload_aug_lots_from_csv(supabase: Client, csv_file_path: str):
    """Reads August lot data from CSV and uploads to Supabase."""
    records_to_insert = []
    try:
        # Read the CSV file
        df = pd.read_csv(csv_file_path)
        
        print(f"Processing {len(df)} records from {csv_file_path}")
        print("Sample data:")
        print(df.head())
        
        for row_number, row in df.iterrows():
            try:
                # Skip row if essential fields are empty
                if pd.isna(row["PO_Number"]) or pd.isna(row["SKU"]) or pd.isna(row["Received_Date"]):
                    print(f"Skipping row {row_number + 1} due to missing essential data")
                    continue

                # Clean and convert data
                po_number = str(row["PO_Number"]).strip()
                sku = str(row["SKU"]).strip()
                received_date = str(row["Received_Date"]).strip()
                
                # Convert quantities to integers
                original_qty = int(float(row["Original_Unit_Qty"]))
                remaining_qty = int(float(row["remaining_unit_qty"]))
                
                # Convert prices to floats
                unit_price = float(row["Unit_Price"])
                freight_cost = float(row["Actual_Freight_Cost_Per_Unit"])
                
                # Calculate total cost
                total_cost = (unit_price + freight_cost) * original_qty

                record = {
                    "po_number": po_number,
                    "sku": sku,
                    "received_date": received_date,
                    "original_unit_qty": original_qty,
                    "unit_price": unit_price,
                    "freight_cost_per_unit": freight_cost,
                    "remaining_unit_qty": remaining_qty,
                    "total_cost": total_cost
                }
                records_to_insert.append(record)
                
                print(f"Processed: {po_number} - {sku} - Qty: {original_qty}")
                
            except Exception as e:
                print(f"Error processing row {row_number + 1}: {e}")
                print(f"Row data: {row.to_dict()}")
                continue

        if not records_to_insert:
            print("No valid records to upload")
            return False

        print(f"\nAttempting to insert {len(records_to_insert)} records into 'purchase_lots'...")
        
        # Insert records in batches to avoid timeout
        batch_size = 10
        for i in range(0, len(records_to_insert), batch_size):
            batch = records_to_insert[i:i + batch_size]
            result = supabase.table("purchase_lots").insert(batch).execute()
            print(f"Inserted batch {i//batch_size + 1}: {len(result.data)} records")
        
        print(f"✅ Successfully uploaded {len(records_to_insert)} August lots!")
        return True

    except Exception as e:
        print(f"❌ Error uploading August lots: {e}")
        return False

def main():
    print("=== August Lots Uploader ===")
    
    # Check if CSV file exists
    csv_file = "aug_lots_to_upload.csv"
    if not os.path.exists(csv_file):
        print(f"❌ Error: {csv_file} not found!")
        return
    
    # Get Supabase client
    supabase_client = get_supabase_client()
    if not supabase_client:
        print("❌ Failed to connect to Supabase")
        return
    
    # Upload the data
    success = upload_aug_lots_from_csv(supabase_client, csv_file)
    
    if success:
        print("\n🎉 August lots upload completed successfully!")
    else:
        print("\n💥 Upload failed. Please check the error messages above.")

if __name__ == "__main__":
    main()
