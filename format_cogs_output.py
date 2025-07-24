#!/usr/bin/env python3
"""
Format COGS output files to fix floating point precision issues
"""
import pandas as pd
import sys
import os

def format_cogs_files(output_dir):
    """Format all COGS output files in the specified directory"""
    
    files_to_format = [
        'cogs_summary_supabase.csv',
        'cogs_attribution_supabase.csv'
    ]
    
    for filename in files_to_format:
        filepath = os.path.join(output_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            continue
            
        print(f"Formatting {filename}...")
        
        try:
            df = pd.read_csv(filepath)
            
            # Format monetary columns to 2 decimal places
            money_columns = [col for col in df.columns if any(word in col.lower() 
                           for word in ['cogs', 'cost', 'price', 'amount'])]
            
            for col in money_columns:
                if col in df.columns:
                    df[col] = df[col].round(2)
            
            # Format specific columns based on filename
            if 'summary' in filename:
                # COGS Summary specific formatting
                if 'Total_COGS' in df.columns:
                    df['Total_COGS'] = df['Total_COGS'].round(2)
                if 'Average_Unit_Cost' in df.columns:
                    df['Average_Unit_Cost'] = df['Average_Unit_Cost'].round(2)
                    
            elif 'attribution' in filename:
                # COGS Attribution specific formatting
                if 'Unit_Cost' in df.columns:
                    df['Unit_Cost'] = df['Unit_Cost'].round(2)
                if 'COGS_Amount' in df.columns:
                    df['COGS_Amount'] = df['COGS_Amount'].round(2)
            
            # Save the formatted file
            df.to_csv(filepath, index=False)
            print(f"  ✅ Formatted {len(df)} rows")
            
        except Exception as e:
            print(f"  ❌ Error formatting {filename}: {e}")

def create_formatted_summary_report(output_dir):
    """Create a nicely formatted summary report"""
    
    summary_file = os.path.join(output_dir, 'cogs_summary_supabase.csv')
    
    if not os.path.exists(summary_file):
        print("COGS summary file not found")
        return
    
    try:
        df = pd.read_csv(summary_file)
        
        # Create formatted report
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("COGS SUMMARY REPORT")
        report_lines.append("=" * 60)
        
        # Overall totals
        total_quantity = df['Total_Quantity'].sum()
        total_cogs = df['Total_COGS'].sum()
        avg_cost = total_cogs / total_quantity if total_quantity > 0 else 0
        
        report_lines.append(f"Total Units Sold: {total_quantity:,}")
        report_lines.append(f"Total COGS: ${total_cogs:,.2f}")
        report_lines.append(f"Average Unit Cost: ${avg_cost:.2f}")
        report_lines.append("")
        
        # Monthly breakdown
        df['Sale_Date'] = pd.to_datetime(df['Sale_Date'])
        df['Month'] = df['Sale_Date'].dt.strftime('%Y-%m')
        monthly = df.groupby('Month').agg({
            'Total_Quantity': 'sum', 
            'Total_COGS': 'sum'
        }).reset_index()
        
        report_lines.append("MONTHLY BREAKDOWN:")
        report_lines.append("-" * 40)
        for _, row in monthly.iterrows():
            month_avg = row['Total_COGS'] / row['Total_Quantity'] if row['Total_Quantity'] > 0 else 0
            report_lines.append(f"{row['Month']}: {row['Total_Quantity']:,} units, ${row['Total_COGS']:,.2f} (avg: ${month_avg:.2f})")
        
        report_lines.append("")
        
        # SKU breakdown
        sku_summary = df.groupby('SKU').agg({
            'Total_Quantity': 'sum',
            'Total_COGS': 'sum'
        }).reset_index().sort_values('Total_COGS', ascending=False)
        
        report_lines.append("TOP 10 SKUs BY COGS:")
        report_lines.append("-" * 40)
        for _, row in sku_summary.head(10).iterrows():
            sku_avg = row['Total_COGS'] / row['Total_Quantity'] if row['Total_Quantity'] > 0 else 0
            report_lines.append(f"{row['SKU']}: {row['Total_Quantity']:,} units, ${row['Total_COGS']:,.2f} (avg: ${sku_avg:.2f})")
        
        # Save report
        report_file = os.path.join(output_dir, 'cogs_summary_report.txt')
        with open(report_file, 'w') as f:
            f.write('\n'.join(report_lines))
        
        print(f"Created summary report: {report_file}")
        
        # Also print to console
        print("\n" + '\n'.join(report_lines))
        
    except Exception as e:
        print(f"Error creating summary report: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 format_cogs_output.py <output_directory>")
        print("Example: python3 format_cogs_output.py ./test_fixed")
        sys.exit(1)
    
    output_dir = sys.argv[1]
    
    if not os.path.exists(output_dir):
        print(f"Output directory does not exist: {output_dir}")
        sys.exit(1)
    
    print(f"Formatting COGS files in: {output_dir}")
    format_cogs_files(output_dir)
    print("\nCreating summary report...")
    create_formatted_summary_report(output_dir)
