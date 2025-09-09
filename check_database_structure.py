"""Check the actual database structure and all data"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def main():
    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    
    print("🔍 Checking actual database structure and data...")
    
    # First, let's see what tables exist
    try:
        # Try to get all records from each expected table
        tables = ['uploaded_files', 'inventory_snapshots', 'cogs_runs', 'cogs_attribution']
        
        for table in tables:
            print(f"\n📋 {table.upper()}:")
            try:
                result = client.table(table).select('*').execute()
                if result.data:
                    print(f"   📊 {len(result.data)} records found")
                    # Show first record structure
                    if result.data:
                        first_record = result.data[0]
                        print(f"   🔧 Columns: {list(first_record.keys())}")
                        
                        # Show all tenant_ids
                        tenant_ids = set()
                        for record in result.data:
                            if 'tenant_id' in record:
                                tenant_ids.add(record['tenant_id'])
                        print(f"   🏢 Tenant IDs: {sorted(tenant_ids)}")
                        
                        # Show sample data
                        print(f"   📝 Sample record:")
                        for key, value in first_record.items():
                            print(f"      {key}: {value}")
                else:
                    print("   📭 No records found")
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    main()