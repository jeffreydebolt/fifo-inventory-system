#!/usr/bin/env python3
import pandas as pd
from pandas.tseries.offsets import MonthEnd

# Replicate the exact logic from fifo_calculator_enhanced.py
print("=== DEBUGGING FIFO PARSING LOGIC ===\n")

# Read the data
df = pd.read_csv('sales_data_date_fixed.csv', dtype=str)
print(f"1. Initial load: {df.shape}")
print(f"   Columns: {list(df.columns)}")
print(f"   First row: {df.iloc[0].to_dict()}")

# Clean column names
df.columns = [col.strip() for col in df.columns]

# Column mapping (from the script)
USER_SALES_COLUMNS_MAPPING = {
    "SKU": "SKU",
    "Units Moved": "Quantity_Sold",
    "Month": "Sale_Month_Str"
}

# Apply column mapping
column_mapping = {'sku': 'SKU', 'units moved': 'Quantity_Sold', 'Month': 'Sale_Month_Str'}
df.rename(columns=column_mapping, inplace=True)
print(f"\n2. After column mapping: {list(df.columns)}")

# Date parsing (exact logic from script)
print(f"\n3. Date parsing...")
print(f"   Sample Sale_Month_Str: {df['Sale_Month_Str'].iloc[0]}")

try:
    df["Sale_Date"] = pd.to_datetime(df["Sale_Month_Str"], format='%B %Y', errors='coerce')
    print(f"   After %B %Y format: {df['Sale_Date'].iloc[0]}")
except:
    print("   %B %Y format failed")

# Alternative format
try:
    df["Sale_Date"] = pd.to_datetime(df["Sale_Month_Str"], errors='coerce')
    df["Sale_Date"] = df["Sale_Date"] + MonthEnd(0)
    print(f"   After alternative format: {df['Sale_Date'].iloc[0]}")
    print(f"   NaT count: {df['Sale_Date'].isna().sum()}")
except Exception as e:
    print(f"   Alternative format failed: {e}")

# Quantity processing
print(f"\n4. Quantity processing...")
print(f"   Sample Quantity_Sold: '{df['Quantity_Sold'].iloc[0]}' (type: {type(df['Quantity_Sold'].iloc[0])})")

df["Quantity_Sold"] = df["Quantity_Sold"].astype(str).str.replace(r'[$,]', '', regex=True).str.strip()
df.loc[df["Quantity_Sold"] == "#VALUE!", "Quantity_Sold"] = "0"
df["Quantity_Sold_Numeric"] = pd.to_numeric(df["Quantity_Sold"], errors='coerce')
df["Quantity_Sold"] = df["Quantity_Sold_Numeric"].fillna(0).astype(int)
df.drop(columns=["Quantity_Sold_Numeric"], inplace=True)

print(f"   After processing: {df['Quantity_Sold'].iloc[0]} (type: {type(df['Quantity_Sold'].iloc[0])})")
print(f"   Zero/negative count: {(df['Quantity_Sold'] <= 0).sum()}")

# Add normalized SKU
def normalize_sku(sku):
    if not sku or not isinstance(sku, str):
        return ""
    return sku.upper()

df["Normalized_SKU"] = df["SKU"].apply(normalize_sku)

# Filter empty SKUs
print(f"\n5. SKU filtering...")
print(f"   Before filtering: {len(df)} rows")
df = df[df["SKU"].notna() & (df["SKU"] != "")]
print(f"   After filtering: {len(df)} rows")

# The critical groupby step
print(f"\n6. Groupby operation...")
print(f"   Columns before groupby: {list(df.columns)}")
print(f"   Data types:")
for col in ["SKU", "Normalized_SKU", "Sale_Date", "Quantity_Sold"]:
    print(f"     {col}: {df[col].dtype}")

try:
    df_summarized = df.groupby(["SKU", "Normalized_SKU", "Sale_Date"])["Quantity_Sold"].sum().reset_index()
    print(f"   After groupby: {len(df_summarized)} rows")
    if len(df_summarized) > 0:
        print(f"   Sample grouped row: {df_summarized.iloc[0].to_dict()}")
    else:
        print("   ERROR: Groupby resulted in empty dataframe!")
        
    # Check for filtering that removes data
    valid_sales = df_summarized[df_summarized["Quantity_Sold"] > 0]
    print(f"   Valid sales (>0): {len(valid_sales)} rows")
    
except Exception as e:
    print(f"   Groupby failed: {e}")

print("\n=== END DEBUG ===")
