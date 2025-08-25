#!/usr/bin/env python3
import pandas as pd
import os
from supabase import create_client
from dotenv import load_dotenv
import logging
import sys

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
        supabase = create_client(url, key)
        logging.info("Supabase client initialized successfully.")
        return supabase
    except Exception as e:
        logging.error(f"Error creating Supabase client: {e}")
        return None

def restore_original_july_consumption():
    """Restore the original July COGS consumption to undo that sales run"""
    
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    # Load the original COGS attribution
    original_cogs = "./july_2025_cogs_new/cogs_attribution_supabase.csv"
    if not os.path.exists(original_cogs):
        logging.error(f"Original COGS file not found: {original_cogs}")
        return False
    
    df_original = pd.read_csv(original_cogs)
    # Filter out unfulfilled records
    df_fulfilled = df_original[df_original['Lot_ID'].apply(lambda x: str(x).isdigit())]
    df_unfulfilled = df_original[df_original['Lot_ID'] == 'UNFULFILLED']
    
    logging.info(f"Loaded {len(df_original)} total records")
    logging.info(f"  - {len(df_fulfilled)} fulfilled records")
    logging.info(f"  - {len(df_unfulfilled)} unfulfilled records")
    
    # Group by lot to get quantities that need to be restored
    lot_consumption = df_fulfilled.groupby('Lot_ID')['Attributed_Qty'].sum().reset_index()
    lot_consumption.columns = ['lot_id', 'quantity_to_restore']
    lot_consumption['lot_id'] = lot_consumption['lot_id'].astype(int)
    
    # Show unfulfilled SKUs
    if len(df_unfulfilled) > 0:
        unfulfilled_summary = df_unfulfilled.groupby('SKU')['Attributed_Qty'].sum().reset_index()
        logging.info("\nUnfulfilled SKUs from original run:")
        for _, row in unfulfilled_summary.iterrows():
            logging.info(f"  - {row['SKU']}: {row['Attributed_Qty']} units")
    
    logging.info(f"\nWill restore consumption for {len(lot_consumption)} lots")
    
    # First, let's check current state vs what we expect
    logging.info("\nChecking current inventory state...")
    
    success_count = 0
    error_count = 0
    
    for _, row in lot_consumption.iterrows():
        lot_id = row['lot_id']
        qty_to_restore = int(row['quantity_to_restore'])
        
        try:
            # Get current inventory
            current_response = supabase.table("purchase_lots").select(
                "remaining_unit_qty, original_unit_qty"
            ).eq("lot_id", lot_id).execute()
            
            if hasattr(current_response, 'data') and current_response.data:
                current_qty = current_response.data[0]['remaining_unit_qty']
                original_qty = current_response.data[0]['original_unit_qty']
                
                # Calculate what the new quantity should be
                new_qty = current_qty + qty_to_restore
                
                # Safety check: ensure we don't exceed original quantity
                if new_qty > original_qty:
                    logging.warning(f"⚠️  Lot {lot_id}: Would exceed original qty ({new_qty} > {original_qty}). Capping at original.")
                    new_qty = original_qty
                
                # Update the lot
                update_response = supabase.table("purchase_lots").update({
                    "remaining_unit_qty": new_qty
                }).eq("lot_id", lot_id).execute()
                
                logging.info(f"✅ Lot {lot_id}: {current_qty} → {new_qty} (restored {qty_to_restore})")
                success_count += 1
                
        except Exception as e:
            logging.error(f"❌ Failed to update lot {lot_id}: {e}")
            error_count += 1
    
    logging.info(f"\n{'='*60}")
    logging.info(f"RESTORATION COMPLETED")
    logging.info(f"{'='*60}")
    logging.info(f"Successfully restored: {success_count} lots")
    logging.info(f"Errors: {error_count} lots")
    logging.info(f"Total quantity restored: {lot_consumption['quantity_to_restore'].sum():,} units")
    
    if len(df_unfulfilled) > 0:
        logging.info(f"\nNote: The original run had {len(df_unfulfilled)} unfulfilled records.")
        logging.info("These should now be fulfillable with the newly added July lots.")
    
    logging.info(f"{'='*60}")
    
    return error_count == 0

if __name__ == "__main__":
    logging.info("Restoring original July COGS consumption...")
    logging.info("This will add back the quantities consumed in the original July run.")
    
    confirm = input("\nProceed with restoring original consumption? (yes/no): ")
    if confirm.lower() == 'yes':
        success = restore_original_july_consumption()
        
        if success:
            logging.info("\n✅ Original July consumption restored successfully!")
            logging.info("The inventory should now be in the pre-July state.")
            logging.info("You can now run a fresh July COGS calculation.")
        else:
            logging.error("\n❌ Restoration completed with errors. Check the log above.")
    else:
        logging.info("Restoration cancelled by user.")