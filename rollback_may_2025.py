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

def rollback_may_2025_cogs():
    """Rollback May 2025 COGS calculation by restoring original inventory"""
    
    # Initialize Supabase
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    # Load the COGS attribution to see what was allocated
    cogs_file = "./may_2025_cogs_final/cogs_attribution_supabase.csv"
    if not os.path.exists(cogs_file):
        logging.error(f"COGS attribution file not found: {cogs_file}")
        return False
    
    df_cogs = pd.read_csv(cogs_file)
    logging.info(f"Loaded {len(df_cogs)} COGS attribution records")
    
    # Group by lot to get total quantities to restore
    lot_restorations = df_cogs.groupby('Lot_ID')['Quantity_From_Lot'].sum().reset_index()
    lot_restorations.columns = ['lot_id', 'quantity_to_restore']
    
    logging.info(f"Need to restore quantities for {len(lot_restorations)} lots")
    
    # Get current inventory to calculate original quantities
    try:
        current_inventory = supabase.table("purchase_lots").select(
            "lot_id, remaining_unit_qty"
        ).execute()
        
        if hasattr(current_inventory, 'data'):
            current_data = current_inventory.data
        else:
            current_data = current_inventory[1] if isinstance(current_inventory, (list, tuple)) and len(current_inventory) > 1 else current_inventory
        
        df_current = pd.DataFrame(current_data)
        logging.info(f"Loaded current inventory for {len(df_current)} lots")
        
    except Exception as e:
        logging.error(f"Error loading current inventory: {e}")
        return False
    
    # Merge to get current quantities
    lot_restorations = lot_restorations.merge(
        df_current[['lot_id', 'remaining_unit_qty']], 
        on='lot_id', 
        how='left'
    )
    
    # Calculate original quantities (current + restored)
    lot_restorations['original_quantity'] = lot_restorations['remaining_unit_qty'] + lot_restorations['quantity_to_restore']
    
    # Update each lot
    success_count = 0
    error_count = 0
    
    for _, row in lot_restorations.iterrows():
        lot_id = row['lot_id']
        original_qty = int(row['original_quantity'])
        restored_qty = int(row['quantity_to_restore'])
        current_qty = int(row['remaining_unit_qty'])
        
        try:
            response = supabase.table("purchase_lots").update({
                "remaining_unit_qty": original_qty
            }).eq("lot_id", lot_id).execute()
            
            logging.info(f"✅ Restored lot {lot_id}: {current_qty} → {original_qty} (+{restored_qty})")
            success_count += 1
            
        except Exception as e:
            logging.error(f"❌ Failed to restore lot {lot_id}: {e}")
            error_count += 1
    
    logging.info(f"\n{'='*60}")
    logging.info(f"ROLLBACK COMPLETED")
    logging.info(f"{'='*60}")
    logging.info(f"Successfully restored: {success_count} lots")
    logging.info(f"Errors: {error_count} lots")
    logging.info(f"Total quantity restored: {lot_restorations['quantity_to_restore'].sum():,} units")
    logging.info(f"{'='*60}")
    
    return error_count == 0

if __name__ == "__main__":
    logging.info("Starting May 2025 COGS rollback...")
    success = rollback_may_2025_cogs()
    
    if success:
        logging.info("✅ Rollback completed successfully!")
    else:
        logging.error("❌ Rollback completed with errors. Check the log above.") 