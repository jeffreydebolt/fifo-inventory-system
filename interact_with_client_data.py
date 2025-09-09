"""
Script to interact with production client data in Supabase
"""
import os
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd
from datetime import datetime

# Load environment variables
load_dotenv()

def connect_to_supabase():
    """Connect to Supabase database"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        raise ValueError("Missing Supabase credentials in .env file")
    
    return create_client(url, key)

def list_tenants(client):
    """List all unique tenants in the system"""
    print("\n📋 Listing all tenants in the system...")
    
    # Get unique tenants from uploaded_files
    result = client.table('uploaded_files').select('tenant_id').execute()
    tenants = set(row['tenant_id'] for row in result.data)
    
    print(f"\nFound {len(tenants)} tenants:")
    for tenant in sorted(tenants):
        print(f"  - {tenant}")
    
    return list(tenants)

def get_tenant_inventory(client, tenant_id):
    """Get current inventory for a specific tenant"""
    print(f"\n📦 Getting current inventory for tenant: {tenant_id}")
    
    result = client.table('inventory_snapshots').select(
        'lot_id, sku, remaining_quantity, unit_price, freight_cost_per_unit, received_date'
    ).eq('tenant_id', tenant_id).eq('is_current', True).execute()
    
    if result.data:
        df = pd.DataFrame(result.data)
        print(f"\nFound {len(df)} active lots:")
        print(df.to_string(index=False))
        return df
    else:
        print("No inventory found for this tenant")
        return pd.DataFrame()

def get_tenant_runs(client, tenant_id):
    """Get recent COGS runs for a tenant"""
    print(f"\n📊 Getting recent runs for tenant: {tenant_id}")
    
    result = client.table('cogs_runs').select(
        'run_id, status, started_at, completed_at, total_sales_processed, total_cogs_calculated'
    ).eq('tenant_id', tenant_id).order('started_at', desc=True).limit(10).execute()
    
    if result.data:
        df = pd.DataFrame(result.data)
        print(f"\nFound {len(df)} recent runs:")
        print(df.to_string(index=False))
        return df
    else:
        print("No runs found for this tenant")
        return pd.DataFrame()

def get_uploaded_files(client, tenant_id):
    """Get uploaded files for a tenant"""
    print(f"\n📄 Getting uploaded files for tenant: {tenant_id}")
    
    result = client.table('uploaded_files').select(
        'file_id, filename, file_type, file_size, uploaded_at, processed'
    ).eq('tenant_id', tenant_id).order('uploaded_at', desc=True).limit(20).execute()
    
    if result.data:
        df = pd.DataFrame(result.data)
        print(f"\nFound {len(df)} uploaded files:")
        print(df.to_string(index=False))
        return df
    else:
        print("No files found for this tenant")
        return pd.DataFrame()

def process_sales_without_lots(client, tenant_id, sales_file_id):
    """Process sales using existing inventory without uploading new lots"""
    print(f"\n🛒 Processing sales for tenant: {tenant_id} with file: {sales_file_id}")
    
    # This would normally call your API endpoint
    # For now, showing what the API call would look like
    print("\nTo process sales without new lots, make this API call:")
    print(f"""
    POST https://api.firstlot.co/api/v1/runs
    {
        "tenant_id": "{tenant_id}",
        "sales_file_id": "{sales_file_id}"
        // Note: lots_file_id is NOT included
    }
    """)

def main():
    """Main interaction script"""
    try:
        # Connect to Supabase
        client = connect_to_supabase()
        print("✅ Connected to Supabase successfully!")
        
        # List all tenants
        tenants = list_tenants(client)
        
        if not tenants:
            print("\n❌ No tenants found in the database")
            return
        
        # Interactive menu
        print("\n" + "="*50)
        print("Choose a tenant to interact with:")
        for i, tenant in enumerate(tenants):
            print(f"{i+1}. {tenant}")
        
        choice = input("\nEnter tenant number (or 'q' to quit): ")
        if choice.lower() == 'q':
            return
        
        try:
            tenant_idx = int(choice) - 1
            if 0 <= tenant_idx < len(tenants):
                selected_tenant = tenants[tenant_idx]
                print(f"\n✅ Selected tenant: {selected_tenant}")
                
                # Show tenant data
                inventory = get_tenant_inventory(client, selected_tenant)
                files = get_uploaded_files(client, selected_tenant)
                runs = get_tenant_runs(client, selected_tenant)
                
                # Example of processing sales without lots
                if not files.empty:
                    sales_files = files[files['file_type'] == 'sales']
                    if not sales_files.empty:
                        latest_sales_file = sales_files.iloc[0]['file_id']
                        process_sales_without_lots(client, selected_tenant, latest_sales_file)
                
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Please enter a valid number")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()