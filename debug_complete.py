#!/usr/bin/env python3
import pandas as pd
from pandas.tseries.offsets import MonthEnd
import re

def normalize_sku(sku):
    """Exact normalize_sku function from the FIFO script"""
    if not sku or not isinstance(sku, str):
        return ""
    
    # Convert to uppercase
    normalized = sku.upper()
    
    # Remove Amazon prefixes if present
    if normalized.startswith("AMAZON."):
        parts = normalized.split(".")
        if len(parts) > 2:
            normalized = parts[-1]
    
    # Remove suffixes with periods
    if "." in normalized:
        normalized = normalized.split(".")[0]
    
    # Remove spaces, dashes, and special characters
    normalized = re.sub(r'[^A-Z0-9]', '', normalized)
    
    return normalized

print("=== COMPLETE FIFO DEBUG ===\n")

# Step 1-6 from before (we know these work)
df = pd.read_csv('sales_data_date_fixed.csv', dtype=str)
df.columns = [col.strip() for col in df.columns]
df.rename(columns={'sku': 'SKU', 'units moved': 'Quantity_Sold', 'Month': 'Sale_Month_Str'}, inplace=True)

# Date parsing
try:
    df["Sale_Date"] = pd.to_datetime(df["Sale_Month_Str"], format='%B %Y', errors='coerce')
except:
    pass

try:
    df["Sale_Date"] = pd.to_datetime(df["Sale_Month_Str"], errors='coerce')
    df["Sale_Date"] = df["Sale_Date"] + MonthEnd(0)
except Exception as e:
    print(f"Date parsing failed: {e}")

# Quantity processing
df["Quantity_Sold"] = df["Quantity_Sold"].astype(str).str.replace(r'[$,]', '', regex=True).str.strip()
df.loc[df["Quantity_Sold"] == "#VALUE!", "Quantity_Sold"] = "0"
df["Quantity_Sold_Numeric"] = pd.to_numeric(df["Quantity_Sold"], errors='coerce')
df["Quantity_Sold"] = df["Quantity_Sold_Numeric"].fillna(0).astype(int)
df.drop(columns=["Quantity_Sold_Numeric"], inplace=True)

# SKU normalization
df["Normalized_SKU"] = df["SKU"].apply(normalize_sku)
print(f"Sample normalized SKUs:")
for i in range(min(5, len(df))):
    print(f"  {df['SKU'].iloc[i]} -> {df['Normalized_SKU'].iloc[i]}")

# Filter empty SKUs
df = df[df["SKU"].notna() & (df["SKU"] != "")]

# Groupby
df_summarized = df.groupby(["SKU", "Normalized_SKU", "Sale_Date"])["Quantity_Sold"].sum().reset_index()
df_summarized["Sales_Order_ID"] = "MONTHLY_SUMMARY_" + df_summarized["Sale_Date"].dt.strftime('%Y%m%d') + "_" + df_summarized["SKU"]

print(f"\nAfter groupby: {len(df_summarized)} rows")
print(f"Sample row: {df_summarized.iloc[0].to_dict()}")

# *** THE CRITICAL STEP THAT MIGHT BE FILTERING EVERYTHING ***
print(f"\n7. Critical filtering step...")
print(f"   Before filtering: {len(df_summarized)} rows")
print(f"   Quantities > 0: {(df_summarized['Quantity_Sold'] > 0).sum()}")
print(f"   Quantities <= 0: {(df_summarized['Quantity_Sold'] <= 0).sum()}")

# Check if the issue is in the empty dataframe check
if df_summarized.empty:
    print("   ERROR: DataFrame is empty after groupby!")
else:
    print("   DataFrame is not empty after groupby")
    
    # Check for the specific filtering logic
    filtered = df_summarized[df_summarized["Quantity_Sold"] > 0]
    print(f"   After >0 filter: {len(filtered)} rows")
    
    if filtered.empty:
        print("   ERROR: All quantities filtered out as <= 0!")
        print("   Sample quantities:", df_summarized["Quantity_Sold"].head().tolist())
    else:
        print("   ✅ SUCCESS: Valid sales data exists!")

print("\n=== END COMPLETE DEBUG ===")
