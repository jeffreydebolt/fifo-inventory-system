#!/usr/bin/env python3

import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import MonthEnd

# Read the sales file
df = pd.read_csv('sales_2025_clean.csv')

print("Original data shape:", df.shape)
print("Original data head:")
print(df.head())

# Apply the same processing as the main script
df["Quantity_Sold"] = df["units moved"].astype(str).str.replace(r'[$,]', '', regex=True).str.strip()
df.loc[df["Quantity_Sold"] == "#VALUE!", "Quantity_Sold"] = "0"
df["Quantity_Sold_Numeric"] = pd.to_numeric(df["Quantity_Sold"], errors='coerce')
df["Quantity_Sold"] = df["Quantity_Sold_Numeric"].fillna(0).astype(int)

# Handle date conversion
print(f"\nSample Month values:")
print(df["Month"].head())
print(f"Month column type: {df['Month'].dtype}")

try:
    df["Sale_Date"] = pd.to_datetime(df["Month"], format='%B %Y', errors='coerce')
    print(f"\nDate conversion result:")
    print(df["Sale_Date"].head())
    print(f"NaT count: {df['Sale_Date'].isna().sum()}")
except Exception as e:
    print(f"Date conversion failed: {e}")

# Add normalized SKU column
def normalize_sku(sku):
    if not sku or not isinstance(sku, str):
        return ""
    normalized = sku.upper()
    if normalized.startswith("AMAZON."):
        parts = normalized.split(".")
        if len(parts) > 2:
            normalized = parts[-1]
    if "." in normalized:
        normalized = normalized.split(".")[0]
    normalized = re.sub(r'[^A-Z0-9]', '', normalized)
    return normalized

import re
df["Normalized_SKU"] = df["sku"].apply(normalize_sku)

# Filter out rows with empty SKUs
df = df[df["sku"].notna() & (df["sku"] != "")]
print(f"\nAfter filtering empty SKUs: {len(df)} rows")

# Check if we have valid dates
if df["Sale_Date"].isna().all():
    print(f"\nPROBLEM: All dates are NaT! This is why summarization fails.")
    print("The date format ' May 2025' (with leading space) is not being parsed correctly.")
    return

# Summarize by SKU and Sale_Date
print(f"\nBefore summarization - quantities > 0: {len(df[df['Quantity_Sold'] > 0])}")
print(f"Before summarization - quantities = 0: {len(df[df['Quantity_Sold'] == 0])}")

df_summarized = df.groupby(["sku", "Normalized_SKU", "Sale_Date"])["Quantity_Sold"].sum().reset_index()
df_summarized["Sales_Order_ID"] = "MONTHLY_SUMMARY_" + df_summarized["Sale_Date"].dt.strftime('%Y%m%d') + "_" + df_summarized["sku"]

print(f"\nAfter summarization - total rows: {len(df_summarized)}")
print(f"After summarization - quantities > 0: {len(df_summarized[df_summarized['Quantity_Sold'] > 0])}")
print(f"After summarization - quantities = 0: {len(df_summarized[df_summarized['Quantity_Sold'] == 0])}")

print(f"\nSummarized data head:")
print(df_summarized.head(10)) 