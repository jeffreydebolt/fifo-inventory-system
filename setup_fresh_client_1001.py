"""Set up fresh client 1001 with proper multi-tenant structure"""
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
    COMPANY_NAME = "FirstLot Client 1001"
    
    print(f"🏗️  Setting up fresh client: {TENANT_ID}")
    print("="*50)
    
    # Step 1: Create tenants table if it doesn't exist (will fail gracefully if exists)
    print("1️⃣  Setting up tenants table...")
    try:
        # Try to insert tenant record
        tenant_record = {
            'tenant_id': TENANT_ID,
            'company_name': COMPANY_NAME,
            'email': 'client1001@firstlot.co',
            'created_at': datetime.now().isoformat(),
            'is_active': True
        }
        
        # First check if tenants table exists by trying to select
        try:
            existing = client.table('tenants').select('tenant_id').eq('tenant_id', TENANT_ID).execute()
            if existing.data:
                print(f"   ✅ Tenant {TENANT_ID} already exists")
            else:
                result = client.table('tenants').insert(tenant_record).execute()
                print(f"   ✅ Created tenant {TENANT_ID}")
        except Exception as e:
            if 'does not exist' in str(e):
                print(f"   ⚠️  Tenants table doesn't exist yet - will create with first insert")
                # We'll handle this in the dashboard setup
            else:
                print(f"   ⚠️  Tenant setup: {e}")
    
    except Exception as e:
        print(f"   ⚠️  Tenant table handling: {e}")
    
    # Step 2: Export current inventory from purchase_lots
    print(f"\n2️⃣  Exporting current inventory from purchase_lots...")
    result = client.table('purchase_lots').select('*').execute()
    if not result.data:
        print("   ❌ No data found in purchase_lots")
        return
    
    df = pd.DataFrame(result.data)
    active_inventory = df[df['remaining_unit_qty'] > 0].copy()
    print(f"   📊 Found {len(active_inventory)} active lots with {active_inventory['remaining_unit_qty'].sum():,} total units")
    
    # Step 3: Create inventory snapshots for new tenant
    print(f"\n3️⃣  Creating inventory snapshots for tenant {TENANT_ID}...")
    inventory_records = []
    
    for _, row in active_inventory.iterrows():
        inventory_record = {
            'snapshot_id': str(uuid.uuid4()),
            'tenant_id': TENANT_ID,
            'run_id': None,  # Baseline inventory
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
    
    # Insert in batches
    batch_size = 50
    total_inserted = 0
    
    for i in range(0, len(inventory_records), batch_size):
        batch = inventory_records[i:i+batch_size]
        try:
            result = client.table('inventory_snapshots').insert(batch).execute()
            total_inserted += len(batch)
            print(f"   ✅ Inserted batch {i//batch_size + 1}: {len(batch)} records")
        except Exception as e:
            print(f"   ❌ Batch {i//batch_size + 1} failed: {e}")
            break
    
    print(f"\n🎉 Fresh client {TENANT_ID} setup complete!")
    print(f"📊 Summary:")
    print(f"   • Tenant ID: {TENANT_ID}")
    print(f"   • Company: {COMPANY_NAME}")
    print(f"   • Inventory records: {total_inserted}")
    print(f"   • Total units: {active_inventory['remaining_unit_qty'].sum():,}")
    print(f"   • Unique SKUs: {active_inventory['sku'].nunique()}")
    
    # Calculate total value
    active_inventory['total_value'] = active_inventory['remaining_unit_qty'] * (active_inventory['unit_price'] + active_inventory['freight_cost_per_unit'])
    total_value = active_inventory['total_value'].sum()
    print(f"   • Total value: ${total_value:,.2f}")

if __name__ == "__main__":
    print("🚀 Setting up fresh client 1001...")
    print("This will NOT modify your existing purchase_lots table")
    print("It will create new records in inventory_snapshots table")
    print()
    
    confirm = input("Proceed? (yes/no): ")
    if confirm.lower() == 'yes':
        main()
    else:
        print("❌ Setup cancelled")