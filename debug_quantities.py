#!/usr/bin/env python3

import pandas as pd

# Read the sales file
df = pd.read_csv('sales_2025_clean.csv')

print("Original data:")
print(df.head(10))
print("\nData types:")
print(df.dtypes)
print("\nQuantity column unique values:")
print(df['units moved'].unique()[:10])

# Try the same processing as the main script
original_qty_sold_series = df["units moved"].copy()
print(f"\nOriginal quantity series type: {type(original_qty_sold_series)}")
print(f"First few values: {original_qty_sold_series.head()}")

# Clean and convert quantity values
df["Quantity_Sold"] = df["units moved"].astype(str).str.replace(r'[$,]', '', regex=True).str.strip()
print(f"\nAfter cleaning: {df['Quantity_Sold'].head()}")

# Handle #VALUE! errors from Excel
df.loc[df["Quantity_Sold"] == "#VALUE!", "Quantity_Sold"] = "0"
print(f"\nAfter handling #VALUE!: {df['Quantity_Sold'].head()}")

df["Quantity_Sold_Numeric"] = pd.to_numeric(df["Quantity_Sold"], errors='coerce')
print(f"\nAfter numeric conversion: {df['Quantity_Sold_Numeric'].head()}")

df["Quantity_Sold"] = df["Quantity_Sold_Numeric"].fillna(0).astype(int)
print(f"\nFinal quantities: {df['Quantity_Sold'].head()}")

print(f"\nSummary:")
print(f"Total rows: {len(df)}")
print(f"Non-zero quantities: {len(df[df['Quantity_Sold'] > 0])}")
print(f"Zero quantities: {len(df[df['Quantity_Sold'] == 0])}")
print(f"Negative quantities: {len(df[df['Quantity_Sold'] < 0])}") 