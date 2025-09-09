"""SAFELY discover ALL existing data without modifying anything"""
import os
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

load_dotenv()

def main():
    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    
    print("🔍 DISCOVERING ALL YOUR EXISTING DATA (READ-ONLY)")
    print("="*60)
    
    # Check for ANY table that might contain data
    all_possible_tables = [
        'purchase_lots', 'sales', 'sales_data', 'sales_transactions', 'transactions',
        'inventory_transactions', 'lot_consumption', 'fifo_runs', 'fifo_calculations',
        'cogs_calculations', 'cost_basis', 'consumption_history', 'sales_history',
        'inventory_consumption', 'lot_history', 'attribution', 'runs'
    ]
    
    found_data = {}
    
    for table in all_possible_tables:
        try:
            result = client.table(table).select('*').execute()
            if result.data:
                found_data[table] = result.data
                df = pd.DataFrame(result.data)
                
                print(f"\n📋 {table.upper()}: {len(result.data)} records")
                print(f"   📊 Columns: {list(df.columns)}")
                
                # Show date range if available
                date_cols = [col for col in df.columns if 'date' in col.lower() or 'created_at' in col.lower()]
                if date_cols:
                    date_col = date_cols[0]
                    print(f"   📅 Date range: {df[date_col].min()} → {df[date_col].max()}")
                
                # Show key metrics
                if 'sku' in df.columns:
                    print(f"   🏷️  SKUs: {df['sku'].nunique()} unique")
                if 'remaining_unit_qty' in df.columns:
                    print(f"   📦 Remaining qty: {df['remaining_unit_qty'].sum():,}")
                if 'quantity' in df.columns:
                    print(f"   📦 Quantity: {df['quantity'].sum():,}")
                if 'units_sold' in df.columns:
                    print(f"   💰 Units sold: {df['units_sold'].sum():,}")
                
                # Show first record structure
                print(f"   📝 Sample: {dict(list(df.iloc[0].items())[:5])}...")
                
        except Exception as e:
            continue
    
    print(f"\n🎯 COMPLETE INVENTORY OF YOUR DATA:")
    print("="*50)
    for table, data in found_data.items():
        print(f"✅ {table}: {len(data)} records")
    
    print(f"\n⚠️  IMPORTANT:")
    print(f"   - I will NOT modify any existing data")
    print(f"   - I will only READ/analyze what you have")
    print(f"   - Any changes will be proposed first")
    print(f"   - You can backup your database first if worried")

if __name__ == "__main__":
    main()