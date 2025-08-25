import pandas as pd

# Read the CSV
df = pd.read_csv('july_final_fixed.csv')

# Convert "25-Jul" to "July 2025"
df['Month'] = df['Month'].apply(lambda x: f"July 20{x.split('-')[0]}")

# Save the converted file
df.to_csv('july_sales_converted.csv', index=False)

print(f"Converted {len(df)} rows")
print(f"Total quantity: {df['Units Moved'].sum()}")
print("\nFirst few rows:")
print(df.head())