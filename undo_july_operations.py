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

def undo_july_sales_and_rollback():
    """Undo the July sales processing and the rollback that preceded it"""
    
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    # Load the COGS attribution from the fresh run to see what was consumed
    cogs_file = "./july_2025_fresh_run/cogs_attribution_supabase.csv"
    if not os.path.exists(cogs_file):
        logging.error(f"COGS attribution file not found: {cogs_file}")
        return False
    
    df_cogs = pd.read_csv(cogs_file)
    # Filter out any unfulfilled records
    df_cogs = df_cogs[df_cogs['Lot_ID'].apply(lambda x: str(x).isdigit())]
    
    logging.info(f"Loaded {len(df_cogs)} COGS records from fresh July run")
    
    # Group by lot to get quantities that were consumed in the fresh run
    consumed_quantities = df_cogs.groupby('Lot_ID')['Attributed_Qty'].sum().reset_index()
    consumed_quantities.columns = ['lot_id', 'quantity_consumed']
    consumed_quantities['lot_id'] = consumed_quantities['lot_id'].astype(int)
    
    # Now we need to:
    # 1. Subtract the quantities that were consumed in the fresh run (undo the sales)
    # 2. This should restore the inventory to the state after the rollback
    
    success_count = 0
    error_count = 0
    
    for _, row in consumed_quantities.iterrows():
        lot_id = row['lot_id']
        consumed_qty = int(row['quantity_consumed'])
        
        try:
            # Get current inventory
            current_response = supabase.table("purchase_lots").select(
                "remaining_unit_qty, original_unit_qty"
            ).eq("lot_id", lot_id).execute()
            
            if hasattr(current_response, 'data') and current_response.data:
                current_qty = current_response.data[0]['remaining_unit_qty']
                
                # Restore by subtracting what was consumed
                new_qty = current_qty - consumed_qty
                
                # Update the lot
                update_response = supabase.table("purchase_lots").update({
                    "remaining_unit_qty": new_qty
                }).eq("lot_id", lot_id).execute()
                
                logging.info(f"✅ Lot {lot_id}: {current_qty} → {new_qty} (removed {consumed_qty} consumed)")
                success_count += 1
                
        except Exception as e:
            logging.error(f"❌ Failed to update lot {lot_id}: {e}")
            error_count += 1
    
    logging.info(f"\n{'='*60}")
    logging.info(f"UNDO OPERATIONS COMPLETED")
    logging.info(f"{'='*60}")
    logging.info(f"Successfully updated: {success_count} lots")
    logging.info(f"Errors: {error_count} lots")
    logging.info(f"Total quantity restored: {consumed_quantities['quantity_consumed'].sum():,} units")
    logging.info(f"{'='*60}")
    
    # Now check if we have the state from before the rollback
    # Load the original July COGS to see what the inventory should be
    original_cogs = "./july_2025_cogs_new/cogs_attribution_supabase.csv"
    if os.path.exists(original_cogs):
        df_original = pd.read_csv(original_cogs)
        df_original = df_original[df_original['Lot_ID'].apply(lambda x: str(x).isdigit())]
        original_consumed = df_original.groupby('Lot_ID')['Attributed_Qty'].sum().reset_index()
        
        logging.info("\nTo fully restore to pre-rollback state, we would need to re-apply the original July COGS consumption.")
        logging.info("This would consume the quantities from the july_2025_cogs_new run.")
    
    return error_count == 0

if __name__ == "__main__":
    logging.info("Starting undo of July operations...")
    
    confirm = input("\nThis will undo the July sales processing. Continue? (yes/no): ")
    if confirm.lower() == 'yes':
        success = undo_july_sales_and_rollback()
        
        if success:
            logging.info("✅ Undo completed successfully!")
            logging.info("\nNOTE: The inventory is now in the state it was after the rollback.")
            logging.info("To fully restore to the original state (before rollback), you would need to re-apply the original July COGS.")
        else:
            logging.error("❌ Undo completed with errors. Check the log above.")
    else:
        logging.info("Undo cancelled by user.")