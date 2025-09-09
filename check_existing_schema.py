"""Check the existing schema your client data uses"""
import os
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

load_dotenv()

def main():
    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    
    print("🔍 Checking your existing schema...")
    
    # Check more tables that might exist
    possible_tables = [
        'purchase_lots', 'sales_transactions', 'sales_data', 'sales',
        'inventory_transactions', 'fifo_calculations', 'cogs_calculations',
        'lot_consumption', 'cost_basis_calculations'
    ]
    
    found_tables = {}
    
    for table_name in possible_tables:
        try:
            result = client.table(table_name).select('*').execute()
            if hasattr(result, 'data') and result.data:
                found_tables[table_name] = result.data
                print(f"\n📋 {table_name.upper()}: {len(result.data)} records")
                
                df = pd.DataFrame(result.data)
                print(f"   📊 Columns: {list(df.columns)}")
                
                # Look for identifying info
                if 'sku' in df.columns:
                    print(f"   🏷️  SKUs: {df['sku'].nunique()} unique - {df['sku'].head(3).tolist()}")
                if 'created_at' in df.columns:
                    print(f"   📅 Date range: {df['created_at'].min()} to {df['created_at'].max()}")
                if 'remaining_unit_qty' in df.columns:
                    print(f"   📦 Total remaining qty: {df['remaining_unit_qty'].sum()}")
                    
                # Show sample record
                print(f"   📝 Sample record: {dict(df.iloc[0])}")
                
        except Exception as e:
            continue
    
    print(f"\n🎯 FOUND YOUR DATA SCHEMA:")
    for table in found_tables.keys():
        print(f"   ✅ {table}")
    
    if found_tables:
        print(f"\n💡 Your client data uses a different schema than the current API expects.")
        print(f"   Current API expects: uploaded_files, inventory_snapshots, cogs_runs")
        print(f"   Your data uses: {list(found_tables.keys())}")
        print(f"\n🔧 Need to either:")
        print(f"   1. Migrate your data to the new schema, OR")
        print(f"   2. Update the API to work with your existing schema")

if __name__ == "__main__":
    main()