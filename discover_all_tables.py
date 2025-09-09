"""Discover all tables in the Supabase database"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def main():
    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    
    print("🔍 Discovering all tables in the database...")
    
    # Try to query the information schema to see all tables
    try:
        # This might work to get all table names
        result = client.rpc('get_schema_tables').execute()
        print(f"Tables found via RPC: {result}")
    except Exception as e:
        print(f"RPC method failed: {e}")
    
    # Try common table names that might exist
    possible_tables = [
        'lots', 'inventory', 'purchases', 'sales', 'transactions',
        'fifo_runs', 'calculations', 'cost_basis', 'inventory_lots',
        'purchase_lots', 'sales_data', 'firstlot_data', 'client_data',
        'users', 'tenants', 'companies', 'files', 'uploads'
    ]
    
    print("\n🔍 Checking possible table names...")
    existing_tables = []
    
    for table_name in possible_tables:
        try:
            result = client.table(table_name).select('*').limit(1).execute()
            if hasattr(result, 'data'):
                existing_tables.append(table_name)
                print(f"   ✅ {table_name} - {len(result.data)} records (showing first)")
                if result.data:
                    record = result.data[0]
                    print(f"      Columns: {list(record.keys())}")
                    # Look for tenant-like fields
                    tenant_fields = [k for k in record.keys() if 'tenant' in k.lower() or 'client' in k.lower() or 'company' in k.lower()]
                    if tenant_fields:
                        print(f"      Tenant fields: {tenant_fields}")
        except Exception as e:
            continue
    
    print(f"\n🎯 Found existing tables: {existing_tables}")
    
    if not existing_tables:
        print("\n❌ No additional tables found with common names.")
        print("Your client data might be in tables with different names.")
        print("\nCan you check your Supabase dashboard at:")
        print("https://supabase.com/dashboard/project/mdjukynmoingazraqyio")
        print("and tell me what tables you see there?")

if __name__ == "__main__":
    main()