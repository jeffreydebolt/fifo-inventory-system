#!/usr/bin/env python3
"""
Clean the golden sales CSV file by removing empty rows and validating data.
"""
import pandas as pd
import sys
from pathlib import Path

def clean_golden_sales(input_path: str, output_path: str):
    """Clean golden sales CSV file"""
    print(f"Loading {input_path}...")
    
    # Read CSV
    df = pd.read_csv(input_path)
    
    # Remove empty columns (unnamed columns)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
    # Remove rows where all values are NaN
    df = df.dropna(how='all')
    
    # Remove rows where key columns are NaN
    df = df.dropna(subset=['sku', 'units moved', 'Month'])
    
    # Validate Month column
    invalid_months = df[df['Month'].isna() | (df['Month'].str.strip() == '')]
    if len(invalid_months) > 0:
        print(f"ERROR: Found {len(invalid_months)} rows with invalid Month values")
        print(invalid_months)
        sys.exit(1)
    
    # Validate units moved is numeric
    df['units moved'] = pd.to_numeric(df['units moved'], errors='coerce')
    invalid_units = df[df['units moved'].isna()]
    if len(invalid_units) > 0:
        print(f"ERROR: Found {len(invalid_units)} rows with invalid units moved values")
        print(invalid_units)
        sys.exit(1)
    
    # Convert units to int
    df['units moved'] = df['units moved'].astype(int)
    
    print(f"Original rows: {len(pd.read_csv(input_path))}")
    print(f"Cleaned rows: {len(df)}")
    print(f"Removed: {len(pd.read_csv(input_path)) - len(df)} empty/invalid rows")
    
    # Save cleaned file
    df.to_csv(output_path, index=False)
    print(f"Saved cleaned file to {output_path}")
    
    # Show sample
    print("\nFirst 5 rows of cleaned data:")
    print(df.head())
    
    return df

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    input_file = project_root / "golden" / "golden_sales.csv"
    output_file = project_root / "golden" / "golden_sales_clean.csv"
    
    clean_golden_sales(str(input_file), str(output_file))