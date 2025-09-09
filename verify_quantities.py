"""VERIFY the exact quantities in your data - READ ONLY"""
import os
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

load_dotenv()

def main():
    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    
    print("🔍 VERIFYING YOUR EXACT QUANTITIES (READ-ONLY)")
    print("="*60)
    
    result = client.table('purchase_lots').select('*').execute()
    df = pd.DataFrame(result.data)
    
    print(f"📊 TOTAL RECORDS: {len(df)}")
    print()
    
    print(f"📦 QUANTITY BREAKDOWN:")
    print(f"   • Original total quantity: {df['original_unit_qty'].sum():,}")
    print(f"   • Remaining quantity: {df['remaining_unit_qty'].sum():,}")
    print(f"   • Consumed quantity: {(df['original_unit_qty'] - df['remaining_unit_qty']).sum():,}")
    print()
    
    print(f"🏷️  SKU SUMMARY:")
    print(f"   • Total unique SKUs: {df['sku'].nunique()}")
    print(f"   • SKUs with remaining inventory: {df[df['remaining_unit_qty'] > 0]['sku'].nunique()}")
    print(f"   • SKUs completely consumed: {df[df['remaining_unit_qty'] == 0]['sku'].nunique()}")
    print()
    
    print(f"📅 DATE RANGE:")
    print(f"   • Oldest lot: {df['received_date'].min()}")
    print(f"   • Newest lot: {df['received_date'].max()}")
    print()
    
    print(f"💰 VALUE SUMMARY:")
    remaining_df = df[df['remaining_unit_qty'] > 0]
    if not remaining_df.empty:
        remaining_value = (remaining_df['remaining_unit_qty'] * (remaining_df['unit_price'] + remaining_df['freight_cost_per_unit'])).sum()
        print(f"   • Value of remaining inventory: ${remaining_value:,.2f}")
    
    # Show some examples of consumed vs remaining lots
    print(f"\n📋 SAMPLE LOT STATUS:")
    sample = df.head(10)[['lot_id', 'sku', 'original_unit_qty', 'remaining_unit_qty', 'received_date']]
    print(sample.to_string(index=False))
    
    print(f"\n✅ VERIFICATION COMPLETE - No data was modified")

if __name__ == "__main__":
    main()