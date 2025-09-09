"""Debug the quantity discrepancy - what you see vs what I calculated"""
import os
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

load_dotenv()

def main():
    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    
    print("🔍 DEBUGGING QUANTITY DISCREPANCY")
    print("="*50)
    
    # Get raw data
    result = client.table('purchase_lots').select('*').execute()
    print(f"📊 Raw query returned {len(result.data)} records")
    
    # Check if there are any data type issues
    raw_total = 0
    problematic_records = []
    
    for i, record in enumerate(result.data):
        remaining = record.get('remaining_unit_qty')
        if remaining is not None:
            try:
                remaining_val = float(remaining)
                raw_total += remaining_val
            except (ValueError, TypeError) as e:
                problematic_records.append((i, record.get('lot_id'), remaining, type(remaining), str(e)))
    
    print(f"📈 Manual calculation (raw loop): {raw_total:,.0f}")
    
    # Now with pandas
    df = pd.DataFrame(result.data)
    pandas_total = df['remaining_unit_qty'].sum()
    print(f"📊 Pandas calculation: {pandas_total:,.0f}")
    
    # Check data types in pandas
    print(f"🔧 Data type of remaining_unit_qty: {df['remaining_unit_qty'].dtype}")
    
    # Show any problematic records
    if problematic_records:
        print(f"\n⚠️  Problematic records found:")
        for i, lot_id, value, data_type, error in problematic_records:
            print(f"   Record {i}: lot_id={lot_id}, value={value}, type={data_type}, error={error}")
    
    # Show some sample values
    print(f"\n📋 Sample remaining_unit_qty values:")
    print(df[['lot_id', 'sku', 'remaining_unit_qty']].head(10).to_string(index=False))
    
    # Check for any filtering that might be needed
    print(f"\n🔍 Value distribution:")
    print(f"   • Records with remaining_unit_qty > 0: {len(df[df['remaining_unit_qty'] > 0])}")
    print(f"   • Records with remaining_unit_qty = 0: {len(df[df['remaining_unit_qty'] == 0])}")
    print(f"   • Records with remaining_unit_qty < 0: {len(df[df['remaining_unit_qty'] < 0])}")
    
    # Maybe you're looking at only active inventory?
    active_total = df[df['remaining_unit_qty'] > 0]['remaining_unit_qty'].sum()
    print(f"📦 Active inventory only (qty > 0): {active_total:,.0f}")
    
    print(f"\n❓ QUESTION: Are you looking at a filtered view in Supabase dashboard?")
    print(f"   (e.g., only showing records where remaining_unit_qty > 0?)")

if __name__ == "__main__":
    main()