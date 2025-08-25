#!/usr/bin/env python3
"""Upload the missing July lots to Supabase"""

import pandas as pd
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def upload_lots():
    # Initialize Supabase
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        logging.error("SUPABASE_URL and SUPABASE_KEY must be set")
        return False
    
    supabase: Client = create_client(url, key)
    logging.info("Connected to Supabase")
    
    # Read the lots file
    df = pd.read_csv('july_missing_lots.csv')
    logging.info(f"Loading {len(df)} lots")
    
    # Prepare data for upload
    lots_data = []
    for _, row in df.iterrows():
        lot = {
            'po_number': row['PO_Number'],
            'sku': row['SKU'],
            'received_date': row['Received_Date'],
            'original_unit_qty': int(row['Original_Unit_Qty']),
            'unit_price': float(row['Unit_Price']),
            'freight_cost_per_unit': float(row['Actual_Freight_Cost_Per_Unit']),
            'remaining_unit_qty': int(row['remaining_unit_qty'])
        }
        lots_data.append(lot)
    
    # Upload to Supabase
    try:
        result = supabase.table('purchase_lots').insert(lots_data).execute()
        logging.info(f"Successfully uploaded {len(lots_data)} lots")
        
        # Display uploaded lots
        for lot in lots_data:
            logging.info(f"  - {lot['sku']}: {lot['original_unit_qty']} units @ ${lot['unit_price']}")
        
        return True
    except Exception as e:
        logging.error(f"Error uploading lots: {e}")
        return False

if __name__ == "__main__":
    if upload_lots():
        print("\n✅ Lots uploaded successfully! You can now re-run the July COGS calculation.")
    else:
        print("\n❌ Failed to upload lots. Please check the error messages above.")