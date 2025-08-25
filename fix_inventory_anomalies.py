#!/usr/bin/env python3
import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Supabase credentials
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set")
    exit(1)

# Create client
supabase = create_client(url, key)

# Query for lots where remaining > original
try:
    response = supabase.table("purchase_lots").select("*").execute()
    
    if hasattr(response, 'data'):
        lots = response.data
        anomalies = []
        
        for lot in lots:
            if lot['remaining_unit_qty'] > lot['original_unit_qty']:
                anomalies.append(lot)
        
        if anomalies:
            print(f"\nFound {len(anomalies)} lots to fix:")
            print("-" * 80)
            
            # Ask for confirmation
            confirm = input("\nDo you want to fix these by capping remaining at original? (yes/no): ")
            
            if confirm.lower() == 'yes':
                fixed_count = 0
                error_count = 0
                
                for lot in anomalies:
                    lot_id = lot['lot_id']
                    original = lot['original_unit_qty']
                    remaining = lot['remaining_unit_qty']
                    
                    try:
                        # Cap remaining at original
                        update_response = supabase.table("purchase_lots").update({
                            "remaining_unit_qty": original
                        }).eq("lot_id", lot_id).execute()
                        
                        print(f"✅ Fixed lot {lot_id}: {remaining} → {original} (capped at original)")
                        fixed_count += 1
                        
                    except Exception as e:
                        print(f"❌ Error fixing lot {lot_id}: {e}")
                        error_count += 1
                
                print(f"\n{'='*60}")
                print(f"FIXES COMPLETED")
                print(f"{'='*60}")
                print(f"Successfully fixed: {fixed_count} lots")
                print(f"Errors: {error_count} lots")
                print(f"{'='*60}")
            else:
                print("Fix cancelled by user")
        else:
            print("\nNo anomalies found - all lots have remaining <= original quantity")
            
except Exception as e:
    print(f"Error querying database: {e}")