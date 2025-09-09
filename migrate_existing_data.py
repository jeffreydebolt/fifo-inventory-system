"""Migrate existing purchase_lots data to the new multi-tenant schema"""
import os
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd
import uuid
from datetime import datetime

load_dotenv()

def main():
    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    
    # IMPORTANT: Set the tenant_id for your existing client
    TENANT_ID = "your_client_company"  # CHANGE THIS to your client's actual ID
    
    print(f"🔄 Migrating existing purchase_lots data to tenant_id: '{TENANT_ID}'")
    
    # Get existing purchase_lots data
    result = client.table('purchase_lots').select('*').execute()
    if not result.data:
        print("❌ No data found in purchase_lots table")
        return
    
    df = pd.DataFrame(result.data)
    print(f"📊 Found {len(df)} lots to migrate")
    
    # Create current inventory snapshot from purchase_lots
    inventory_records = []
    for _, row in df.iterrows():
        inventory_record = {
            'snapshot_id': str(uuid.uuid4()),
            'tenant_id': TENANT_ID,
            'run_id': None,  # This is the baseline inventory
            'lot_id': str(row['lot_id']),
            'sku': row['sku'],
            'remaining_quantity': int(row['remaining_unit_qty']),
            'original_quantity': int(row['original_unit_qty']),
            'unit_price': float(row['unit_price']),
            'freight_cost_per_unit': float(row['freight_cost_per_unit']),
            'received_date': row['received_date'],
            'is_current': True
        }
        inventory_records.append(inventory_record)
    
    # Insert into inventory_snapshots table
    print(f"💾 Inserting {len(inventory_records)} records into inventory_snapshots...")
    
    # Insert in batches to avoid hitting limits
    batch_size = 50
    for i in range(0, len(inventory_records), batch_size):
        batch = inventory_records[i:i+batch_size]
        try:
            result = client.table('inventory_snapshots').insert(batch).execute()
            print(f"   ✅ Inserted batch {i//batch_size + 1}: {len(batch)} records")
        except Exception as e:
            print(f"   ❌ Batch {i//batch_size + 1} failed: {e}")
    
    print(f"\n🎉 Migration complete!")
    print(f"📋 Summary:")
    print(f"   • {len(inventory_records)} lots migrated")
    print(f"   • {df['sku'].nunique()} unique SKUs") 
    print(f"   • {df['remaining_unit_qty'].sum()} total remaining units")
    print(f"   • Assigned to tenant_id: '{TENANT_ID}'")
    
    print(f"\n🔧 Next steps:")
    print(f"   1. Update the dashboard ClientContext.js with tenant_id: '{TENANT_ID}'")
    print(f"   2. Login to the dashboard with that client")
    print(f"   3. Your existing inventory will show up!")

if __name__ == "__main__":
    print("⚠️  WARNING: This will migrate your existing data to the new schema.")
    print("   Make sure to update TENANT_ID in the script first!")
    
    confirm = input("Do you want to proceed? (yes/no): ")
    if confirm.lower() == 'yes':
        main()
    else:
        print("❌ Migration cancelled")