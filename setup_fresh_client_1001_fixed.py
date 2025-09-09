"""Set up fresh client 1001 - fixed version"""
import os
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd
import uuid
from datetime import datetime

load_dotenv()

def main():
    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    
    TENANT_ID = "1001"
    
    print(f"🏗️  Setting up fresh client: {TENANT_ID}")
    
    # Export current inventory from purchase_lots
    result = client.table('purchase_lots').select('*').execute()
    df = pd.DataFrame(result.data)
    active_inventory = df[df['remaining_unit_qty'] > 0].copy()
    print(f"📊 Found {len(active_inventory)} active lots with {active_inventory['remaining_unit_qty'].sum():,} total units")
    
    # Create inventory snapshots with a baseline run_id
    baseline_run_id = str(uuid.uuid4())
    print(f"📝 Using baseline run_id: {baseline_run_id}")
    
    inventory_records = []
    for _, row in active_inventory.iterrows():
        inventory_record = {
            'snapshot_id': str(uuid.uuid4()),
            'tenant_id': TENANT_ID,
            'run_id': baseline_run_id,  # Use baseline run ID instead of None
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
    
    # Create the baseline run record first
    run_record = {
        'run_id': baseline_run_id,
        'tenant_id': TENANT_ID,
        'status': 'completed',
        'started_at': datetime.now().isoformat(),
        'completed_at': datetime.now().isoformat(),
        'total_sales_processed': 0,
        'total_cogs_calculated': 0
    }
    
    try:
        client.table('cogs_runs').insert(run_record).execute()
        print("✅ Created baseline run record")
    except Exception as e:
        print(f"⚠️  Run record: {e}")
    
    # Insert inventory in batches
    batch_size = 50
    total_inserted = 0
    
    for i in range(0, len(inventory_records), batch_size):
        batch = inventory_records[i:i+batch_size]
        try:
            result = client.table('inventory_snapshots').insert(batch).execute()
            total_inserted += len(batch)
            print(f"✅ Inserted batch {i//batch_size + 1}: {len(batch)} records")
        except Exception as e:
            print(f"❌ Batch {i//batch_size + 1} failed: {e}")
            # Show first record of failed batch for debugging
            if batch:
                print(f"   Sample record: {batch[0]}")
            break
    
    print(f"\n🎉 Setup complete!")
    print(f"📊 Summary:")
    print(f"   • Tenant ID: {TENANT_ID}")
    print(f"   • Inventory records: {total_inserted}")
    print(f"   • Total units: {active_inventory['remaining_unit_qty'].sum():,}")
    print(f"   • Unique SKUs: {active_inventory['sku'].nunique()}")

if __name__ == "__main__":
    main()