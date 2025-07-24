#!/usr/bin/env python3

import pandas as pd
from datetime import datetime

# Read the CSV file
df = pd.read_csv('lots_to_upload.csv')

print("Original dates:")
print(df['Received_Date'].head())

# Convert date format from DD-MMM-YY to YYYY-MM-DD
def convert_date(date_str):
    try:
        # Parse DD-MMM-YY format
        date_obj = datetime.strptime(date_str, '%d-%b-%y')
        # Convert to YYYY-MM-DD format
        return date_obj.strftime('%Y-%m-%d')
    except:
        return date_str

# Apply the conversion
df['Received_Date'] = df['Received_Date'].apply(convert_date)

print("\nConverted dates:")
print(df['Received_Date'].head())

# Save the converted file
df.to_csv('lots_to_upload_converted.csv', index=False)
print(f"\nConverted file saved as 'lots_to_upload_converted.csv'") 