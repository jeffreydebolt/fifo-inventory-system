"""
Convert existing CSV files to match API format requirements.
"""
import pandas as pd
import sys

def convert_lots_file(input_file, output_file):
    """Convert lots file to API format."""
    # Read existing file
    df = pd.read_csv(input_file)
    
    print(f"Original columns: {list(df.columns)}")
    
    # Create new DataFrame with API format
    converted = pd.DataFrame({
        'lot_id': df['PO_Number'],
        'sku': df['SKU'],
        'received_date': pd.to_datetime(df['Received_Date']).dt.strftime('%Y-%m-%d'),
        'original_quantity': df['Original_Unit_Qty'],
        'remaining_quantity': df['remaining_unit_qty'],
        'unit_price': df['Unit_Price'],
        'freight_cost_per_unit': df['Actual_Freight_Cost_Per_Unit']
    })
    
    # Save converted file
    converted.to_csv(output_file, index=False)
    print(f"Converted {len(converted)} rows to {output_file}")
    print(f"New columns: {list(converted.columns)}")
    
    # Show sample
    print("\nSample data:")
    print(converted.head())
    
    return converted

def convert_sales_file(input_file, output_file):
    """Convert sales file to API format."""
    # Read existing file
    df = pd.read_csv(input_file)
    
    print(f"Original columns: {list(df.columns)}")
    
    # Try to find the right columns
    # Common variations: 'Units Moved', 'units moved', 'Quantity', etc.
    quantity_col = None
    for col in df.columns:
        if 'unit' in col.lower() or 'quantity' in col.lower() or 'qty' in col.lower():
            quantity_col = col
            break
    
    if not quantity_col:
        print("ERROR: Could not find quantity column!")
        return None
    
    # Find date/month column
    date_col = None
    for col in df.columns:
        if 'month' in col.lower() or 'date' in col.lower() or 'period' in col.lower():
            date_col = col
            break
    
    if not date_col:
        print("ERROR: Could not find date/month column!")
        return None
    
    # Create new DataFrame with API format
    converted = pd.DataFrame({
        'sku': df[df.columns[0]],  # Assume first column is SKU
        'units moved': df[quantity_col],
        'Month': df[date_col]
    })
    
    # Save converted file
    converted.to_csv(output_file, index=False)
    print(f"Converted {len(converted)} rows to {output_file}")
    print(f"New columns: {list(converted.columns)}")
    
    # Show sample
    print("\nSample data:")
    print(converted.head())
    
    return converted

if __name__ == "__main__":
    print("=== CSV Format Converter for FIFO API ===\n")
    
    # Convert the August lots file
    print("1. Converting Lots File...")
    try:
        convert_lots_file(
            'aug_lots_to_upload.csv',
            'aug_lots_api_format.csv'
        )
    except Exception as e:
        print(f"Error converting lots: {e}")
    
    # Convert sales file if it exists
    print("\n2. Looking for sales file...")
    sales_files = [
        'aug_sales_converted.csv',
        'sales_2025.csv',
        'test_sales_data.csv'
    ]
    
    for sales_file in sales_files:
        try:
            print(f"\nTrying {sales_file}...")
            import os
            if os.path.exists(sales_file):
                convert_sales_file(
                    sales_file,
                    f'{sales_file.replace(".csv", "_api_format.csv")}'
                )
                break
        except Exception as e:
            print(f"Error with {sales_file}: {e}")
    
    print("\n✅ Conversion complete! Use the *_api_format.csv files for upload.")