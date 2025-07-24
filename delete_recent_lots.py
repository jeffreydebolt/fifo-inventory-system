#!/usr/bin/env python3

import pandas as pd
import os
import logging
import sys
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def get_supabase_client():
    """Initialize Supabase client"""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        logging.error("SUPABASE_URL and SUPABASE_KEY environment variables must be set.")
        return None
    
    try:
        supabase: Client = create_client(url, key)
        logging.info("Supabase client initialized successfully.")
        return supabase
    except Exception as e:
        logging.error(f"Error creating Supabase client: {e}")
        return None

def delete_recent_lots():
    """Delete the lots that were just uploaded"""
    
    # Initialize Supabase
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    # PO numbers of the lots that were just uploaded
    po_numbers_to_delete = [
        "ST0229", "ST0230", "ST0231", "ST0232", "ST0233", "ST0234", "ST0235", 
        "ST0236", "ST0237", "ST0238", "ST0239", "ST0240", "ST0241", "ST0242", 
        "ST0246", "ST0248", "ST0249"
    ]
    
    logging.info(f"Attempting to delete {len(po_numbers_to_delete)} lots...")
    
    # First, let's verify these lots exist and get their details
    try:
        # Get all lots with these PO numbers
        response = supabase.table("purchase_lots").select(
            "lot_id, po_number, sku, original_unit_qty, remaining_unit_qty"
        ).in_("po_number", po_numbers_to_delete).execute()
        
        if hasattr(response, 'data'):
            lots_data = response.data
        else:
            lots_data = response[1] if isinstance(response, (list, tuple)) and len(response) > 1 else response
        
        if not lots_data:
            logging.warning("No lots found with the specified PO numbers. They may have already been deleted.")
            return True
        
        df_lots = pd.DataFrame(lots_data)
        logging.info(f"Found {len(df_lots)} lots to delete:")
        
        for _, lot in df_lots.iterrows():
            logging.info(f"  - Lot {lot['lot_id']}: PO {lot['po_number']}, SKU {lot['sku']}, Qty {lot['remaining_unit_qty']}")
        
        # Confirm deletion
        print(f"\n{'='*60}")
        print(f"WARNING: About to delete {len(df_lots)} lots!")
        print(f"{'='*60}")
        print("This will permanently remove these lots from the database.")
        print("Are you sure you want to continue? (yes/no): ", end="")
        
        confirmation = input().strip().lower()
        if confirmation != 'yes':
            logging.info("Deletion cancelled by user.")
            return False
        
        # Delete each lot
        success_count = 0
        error_count = 0
        
        for _, lot in df_lots.iterrows():
            lot_id = lot['lot_id']
            po_number = lot['po_number']
            sku = lot['sku']
            
            try:
                response = supabase.table("purchase_lots").delete().eq("lot_id", lot_id).execute()
                logging.info(f"✅ Deleted lot {lot_id}: PO {po_number}, SKU {sku}")
                success_count += 1
                
            except Exception as e:
                logging.error(f"❌ Failed to delete lot {lot_id} (PO {po_number}): {e}")
                error_count += 1
        
        logging.info(f"\n{'='*60}")
        logging.info(f"DELETION COMPLETED")
        logging.info(f"{'='*60}")
        logging.info(f"Successfully deleted: {success_count} lots")
        logging.info(f"Errors: {error_count} lots")
        logging.info(f"{'='*60}")
        
        return error_count == 0
        
    except Exception as e:
        logging.error(f"Error during deletion process: {e}")
        return False

if __name__ == "__main__":
    logging.info("Starting deletion of recently uploaded lots...")
    success = delete_recent_lots()
    
    if success:
        logging.info("✅ Deletion completed successfully!")
    else:
        logging.error("❌ Deletion completed with errors. Check the log above.") 