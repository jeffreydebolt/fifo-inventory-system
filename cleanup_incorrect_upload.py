#!/usr/bin/env python3
"""
Remove the incorrectly uploaded lot data
"""

import os
from supabase import create_client, Client

def get_supabase_client():
    """Get Supabase client"""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set.")
        return None
    
    try:
        supabase = create_client(url, key)
        return supabase
    except Exception as e:
        print(f"Error creating Supabase client: {e}")
        return None

def cleanup_incorrect_upload():
    """Remove the incorrectly uploaded records"""
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    # The lot_ids that were incorrectly uploaded
    incorrect_lot_ids = [996, 997, 998, 999]
    
    try:
        print(f"Removing {len(incorrect_lot_ids)} incorrect records...")
        
        for lot_id in incorrect_lot_ids:
            result = supabase.table("purchase_lots").delete().eq("lot_id", lot_id).execute()
            print(f"Removed lot_id {lot_id}: {len(result.data)} records deleted")
        
        print("✅ Cleanup completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False

if __name__ == "__main__":
    cleanup_incorrect_upload()
