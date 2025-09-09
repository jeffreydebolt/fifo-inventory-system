"""Quick script to check all tenants across all tables"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def main():
    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    
    tables = ['uploaded_files', 'inventory_snapshots', 'cogs_runs', 'cogs_attribution']
    all_tenants = set()
    
    for table in tables:
        try:
            result = client.table(table).select('tenant_id').execute()
            tenants = set(row['tenant_id'] for row in result.data)
            print(f"{table}: {sorted(tenants)}")
            all_tenants.update(tenants)
        except Exception as e:
            print(f"{table}: Error - {e}")
    
    print(f"\nAll unique tenant_ids found: {sorted(all_tenants)}")

if __name__ == "__main__":
    main()