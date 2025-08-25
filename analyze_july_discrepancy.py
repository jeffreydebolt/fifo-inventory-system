import pandas as pd

# Read input and output files
input_df = pd.read_csv('july_sales_converted.csv')
output_df = pd.read_csv('july_2025_cogs_new/cogs_summary_supabase.csv')

# Group input by SKU and sum quantities
input_summary = input_df.groupby('SKU')['Quantity_Sold'].sum().reset_index()
input_summary.columns = ['SKU', 'Input_Qty']

# Extract output quantities
output_summary = output_df[['SKU', 'Total_Quantity_Sold']].copy()
output_summary.columns = ['SKU', 'Output_Qty']

# Merge to compare
comparison = pd.merge(input_summary, output_summary, on='SKU', how='outer')
comparison['Input_Qty'] = comparison['Input_Qty'].fillna(0)
comparison['Output_Qty'] = comparison['Output_Qty'].fillna(0)
comparison['Difference'] = comparison['Input_Qty'] - comparison['Output_Qty']

# Find discrepancies
discrepancies = comparison[comparison['Difference'] != 0].sort_values('Difference', ascending=False)

print("=== JULY 2025 SALES DISCREPANCY ANALYSIS ===\n")
print(f"Total Input Quantity: {input_df['Quantity_Sold'].sum():,.0f}")
print(f"Total Output Quantity: {output_df['Total_Quantity_Sold'].sum():,.0f}")
print(f"Total Discrepancy: {input_df['Quantity_Sold'].sum() - output_df['Total_Quantity_Sold'].sum():,.0f} units\n")

print("=== SKUs WITH DISCREPANCIES ===")
print(discrepancies.to_string(index=False))

print(f"\n=== SUMMARY ===")
print(f"Number of SKUs with discrepancies: {len(discrepancies)}")
print(f"Total unfulfilled quantity: {discrepancies['Difference'].sum():,.0f} units")

# Check for SKUs in input but not in output
missing_skus = comparison[comparison['Output_Qty'] == 0]
if len(missing_skus) > 0:
    print(f"\n=== SKUs WITH NO OUTPUT (No inventory available) ===")
    print(missing_skus[['SKU', 'Input_Qty']].to_string(index=False))