"""Find the real client tenant_id from the production database"""
import os
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

load_dotenv()

def main():
    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    
    print("🔍 Searching for real client data in production database...")
    
    # Check all tables for tenant_ids that aren't test data
    tables = {
        'uploaded_files': 'file uploads',
        'inventory_snapshots': 'inventory lots', 
        'cogs_runs': 'FIFO calculation runs',
        'cogs_attribution': 'sales attributions'
    }
    
    all_tenants = set()
    
    for table, description in tables.items():
        try:
            result = client.table(table).select('tenant_id, created_at').execute()
            if result.data:
                df = pd.DataFrame(result.data)
                tenant_counts = df['tenant_id'].value_counts()
                
                print(f"\n📊 {table.upper()} ({description}):")
                for tenant, count in tenant_counts.items():
                    if tenant != 'test_connection':  # Skip our test data
                        print(f"  🏢 tenant_id: '{tenant}' - {count} records")
                        all_tenants.add(tenant)
                        
                        # Show a sample record for context
                        sample = df[df['tenant_id'] == tenant].iloc[0]
                        if 'created_at' in sample:
                            print(f"      📅 First record: {sample['created_at']}")
                        if 'filename' in df.columns:
                            print(f"      📄 Sample file: {sample.get('filename', 'N/A')}")
                
        except Exception as e:
            print(f"❌ Error checking {table}: {e}")
    
    print(f"\n🎯 FOUND REAL CLIENT TENANT IDs: {sorted(all_tenants)}")
    
    # Show detailed info for each real tenant
    for tenant in sorted(all_tenants):
        print(f"\n" + "="*50)
        print(f"TENANT: {tenant}")
        print("="*50)
        
        # Get inventory
        try:
            inv_result = client.table('inventory_snapshots').select('*').eq('tenant_id', tenant).eq('is_current', True).execute()
            if inv_result.data:
                print(f"📦 Current Inventory: {len(inv_result.data)} lots")
                df = pd.DataFrame(inv_result.data)
                print(f"    SKUs: {df['sku'].nunique()} unique")
                print(f"    Total Quantity: {df['remaining_quantity'].sum()}")
        except Exception as e:
            print(f"📦 Inventory: Error - {e}")
        
        # Get runs
        try:
            runs_result = client.table('cogs_runs').select('*').eq('tenant_id', tenant).execute()
            if runs_result.data:
                print(f"🏃 COGS Runs: {len(runs_result.data)} total")
                df = pd.DataFrame(runs_result.data)
                completed = df[df['status'] == 'completed']
                print(f"    Completed: {len(completed)}")
                if not completed.empty:
                    print(f"    Latest: {completed['completed_at'].max()}")
        except Exception as e:
            print(f"🏃 Runs: Error - {e}")

if __name__ == "__main__":
    main()