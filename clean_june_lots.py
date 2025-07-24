#!/usr/bin/env python3

import pandas as pd
import re
from datetime import datetime

def clean_june_lots():
    """Clean the June lots file for upload"""
    
    # Read the original file
    df = pd.read_csv('lots_to_upload_June.csv')
    
    # Remove empty rows
    df = df.dropna(subset=['PO_Number', 'SKU']).reset_index(drop=True)
    
    # Clean date format (convert "12-Jun-25" to "2025-06-12")
    def convert_date(date_str):
        if pd.isna(date_str) or date_str == '':
            return None
        try:
            # Parse date like "12-Jun-25"
            date_obj = datetime.strptime(str(date_str), '%d-%b-%y')
            return date_obj.strftime('%Y-%m-%d')
        except:
            return None
    
    df['Received_Date'] = df['Received_Date'].apply(convert_date)
    
    # Clean numeric fields (remove commas, dollar signs, spaces)
    def clean_numeric(value):
        if pd.isna(value) or value == '':
            return 0
        # Convert to string, remove commas, dollar signs, and spaces
        cleaned = str(value).replace(',', '').replace('$', '').replace(' ', '')
        try:
            return float(cleaned)
        except:
            return 0
    
    # Clean quantity and price fields
    df['Original_Unit_Qty'] = df['Original_Unit_Qty'].apply(clean_numeric)
    df['Unit_Price'] = df['Unit_Price'].apply(clean_numeric)
    df['Actual_Freight_Cost_Per_Unit'] = df['Actual_Freight_Cost_Per_Unit'].apply(clean_numeric)
    df['remaining_unit_qty'] = df['remaining_unit_qty'].apply(clean_numeric)
    
    # Convert quantities to integers
    df['Original_Unit_Qty'] = df['Original_Unit_Qty'].astype(int)
    df['remaining_unit_qty'] = df['remaining_unit_qty'].astype(int)
    
    # Remove the extra unnamed columns
    df = df[['PO_Number', 'SKU', 'Received_Date', 'Original_Unit_Qty', 'Unit_Price', 'Actual_Freight_Cost_Per_Unit', 'remaining_unit_qty']]
    
    # Save cleaned file
    output_file = 'lots_to_upload_June_clean.csv'
    df.to_csv(output_file, index=False)
    
    print(f"Cleaned file saved as: {output_file}")
    print(f"Processed {len(df)} lots:")
    
    for _, row in df.iterrows():
        print(f"  - PO {row['PO_Number']}: {row['SKU']}, {row['Original_Unit_Qty']} units, ${row['Unit_Price']:.2f} + ${row['Actual_Freight_Cost_Per_Unit']:.2f} freight")
    
    return output_file

if __name__ == "__main__":
    clean_june_lots() 