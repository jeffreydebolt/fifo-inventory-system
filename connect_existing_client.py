"""Connect your existing purchase_lots data to the dashboard system"""
import os
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd
import uuid
from datetime import datetime

load_dotenv()

def main():
    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    
    # Use your existing data tenant
    TENANT_ID = "existing_client"
    
    print(f"🔗 Connecting existing purchase_lots data to dashboard...")
    
    # Get your existing data
    result = client.table('purchase_lots').select('*').execute()
    df = pd.DataFrame(result.data)
    active_inventory = df[df['remaining_unit_qty'] > 0].copy()
    
    print(f"📊 Found {len(active_inventory)} active lots with {active_inventory['remaining_unit_qty'].sum():,} units")
    
    # Create baseline run
    baseline_run_id = str(uuid.uuid4())
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
        print("✅ Created baseline run")
    except Exception as e:
        print(f"Run record: {e}")
    
    # Create inventory snapshots
    inventory_records = []
    for _, row in active_inventory.iterrows():
        inventory_record = {
            'snapshot_id': str(uuid.uuid4()),
            'tenant_id': TENANT_ID,
            'run_id': baseline_run_id,
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
    
    # Clear any existing records for this tenant first
    try:
        client.table('inventory_snapshots').delete().eq('tenant_id', TENANT_ID).execute()
    except:
        pass
    
    # Insert in batches
    batch_size = 50
    for i in range(0, len(inventory_records), batch_size):
        batch = inventory_records[i:i+batch_size]
        try:
            client.table('inventory_snapshots').insert(batch).execute()
            print(f"✅ Inserted batch {i//batch_size + 1}: {len(batch)} records")
        except Exception as e:
            print(f"❌ Batch failed: {e}")
            break
    
    print(f"\n🎉 Connected existing data!")
    print(f"   • Tenant: {TENANT_ID}")
    print(f"   • Units: {active_inventory['remaining_unit_qty'].sum():,}")
    print(f"   • SKUs: {active_inventory['sku'].nunique()}")

if __name__ == "__main__":
    main()