"""Show the actual current inventory breakdown"""
import os
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

load_dotenv()

def main():
    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    
    result = client.table('purchase_lots').select('*').execute()
    df = pd.DataFrame(result.data)
    
    # Only active inventory (remaining > 0)
    active_df = df[df['remaining_unit_qty'] > 0].copy()
    
    print("📦 CURRENT ACTIVE INVENTORY BREAKDOWN")
    print("="*60)
    print(f"Total active lots: {len(active_df)}")
    print(f"Total active quantity: {active_df['remaining_unit_qty'].sum():,}")
    print()
    
    # Group by SKU
    sku_summary = active_df.groupby('sku').agg({
        'remaining_unit_qty': 'sum',
        'lot_id': 'count'
    }).rename(columns={'lot_id': 'lot_count'}).sort_values('remaining_unit_qty', ascending=False)
    
    print("🏷️  TOP 20 SKUs BY REMAINING QUANTITY:")
    print(sku_summary.head(20).to_string())
    
    print(f"\n📊 QUANTITY RANGES:")
    ranges = [
        (0, 100, "1-100"),
        (101, 500, "101-500"), 
        (501, 1000, "501-1,000"),
        (1001, 5000, "1,001-5,000"),
        (5001, 999999, "5,000+")
    ]
    
    for min_qty, max_qty, label in ranges:
        count = len(active_df[(active_df['remaining_unit_qty'] >= min_qty) & (active_df['remaining_unit_qty'] <= max_qty)])
        total_qty = active_df[(active_df['remaining_unit_qty'] >= min_qty) & (active_df['remaining_unit_qty'] <= max_qty)]['remaining_unit_qty'].sum()
        print(f"   {label}: {count} lots, {total_qty:,} total units")
    
    print(f"\n🔍 WHERE ARE YOU SEEING 165K?")
    print(f"   • In Supabase dashboard table view?")
    print(f"   • In a SQL query result?") 
    print(f"   • In an existing report/dashboard?")
    print(f"   • Maybe a different column or calculation?")

if __name__ == "__main__":
    main()