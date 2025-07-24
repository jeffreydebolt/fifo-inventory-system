#!/usr/bin/env python3
"""
Debug script to replicate the FIFO calculator's data parsing logic
"""
import pandas as pd
import numpy as np

def debug_sales_parsing(filename):
    """Debug the exact parsing logic used by the FIFO calculator"""
    print(f"=== DEBUGGING SALES DATA PARSING: {filename} ===\n")
    
    # Step 1: Read raw CSV
    print("Step 1: Reading raw CSV...")
    try:
        df_raw = pd.read_csv(filename)
        print(f"Raw shape: {df_raw.shape}")
        print(f"Raw columns: {list(df_raw.columns)}")
        print("Raw data types:")
        print(df_raw.dtypes)
        print("\nFirst 5 rows (raw):")
        print(df_raw.head())
        print()
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return
    
    # Step 2: Replicate the column mapping logic
    print("Step 2: Column mapping logic...")
    columns = df_raw.columns.tolist()
    print(f"Found columns: {columns}")
    
    # Step 3: Check quantity column specifically
    print("Step 3: Analyzing quantity column...")
    qty_col = 'units moved'  # We know this from the logs
    
    if qty_col in df_raw.columns:
        print(f"Quantity column: '{qty_col}'")
        qty_series = df_raw[qty_col]
        print(f"Quantity data type: {qty_series.dtype}")
        print(f"Unique values: {sorted(qty_series.unique())}")
        
        # Check for non-numeric values
        print("\nChecking for non-numeric values...")
        for i, val in enumerate(qty_series.head(10)):
            try:
                float_val = float(val)
                print(f"Row {i}: '{val}' -> {float_val}")
            except (ValueError, TypeError):
                print(f"Row {i}: '{val}' -> NOT NUMERIC")
        
        # Try converting to numeric (like pandas does)
        print(f"\nConverting to numeric...")
        qty_numeric = pd.to_numeric(qty_series, errors='coerce')
        print(f"After to_numeric conversion:")
        print(f"  NaN count: {qty_numeric.isna().sum()}")
        print(f"  Zero or negative count: {(qty_numeric <= 0).sum()}")
        print(f"  Valid positive count: {(qty_numeric > 0).sum()}")
        
        # Show actual values
        print(f"\nFirst 10 converted values:")
        for i in range(min(10, len(qty_numeric))):
            print(f"  {i}: {qty_series.iloc[i]} -> {qty_numeric.iloc[i]}")

if __name__ == "__main__":
    debug_sales_parsing("sales_data_cleaned.csv")
