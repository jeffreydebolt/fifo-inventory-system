#!/usr/bin/env python3

import pandas as pd
import os
import logging
import sys
from datetime import datetime
from pandas.tseries.offsets import MonthEnd
import argparse
import re
from supabase import create_client, Client
import csv
from dotenv import load_dotenv
from pathlib import Path

# --- Load environment variables from .env file ---
load_dotenv()

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# --- Supabase Configuration ---
SUPABASE_PURCHASES_TABLE_NAME = "purchase_lots"

# --- Column Mappings (Enhanced for robustness) ---
USER_SALES_COLUMNS_MAPPING = {
    "sku": "SKU",
    "units moved": "Quantity_Sold",
    "Month": "Sale_Month_Str" # Temporary column to hold month string
}

# --- Validation Constants ---
VALIDATION_ERROR_TYPES = {
    "SKU_NOT_FOUND": "SKU not found in inventory",
    "INSUFFICIENT_QUANTITY": "Insufficient quantity available",
    "INVALID_FORMAT": "Invalid data format",
    "NEGATIVE_QUANTITY": "Negative quantity not allowed"
}

# --- Supabase Client Initialization ---
def get_supabase_client():
    """Initializes and returns the Supabase client using .env file."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        logging.error("SUPABASE_URL and SUPABASE_KEY environment variables must be set in .env file.")
        return None
    try:
        supabase: Client = create_client(url, key)
        logging.info("Supabase client initialized successfully.")
        return supabase
    except Exception as e:
        logging.error(f"Error creating Supabase client: {e}")
        return None

# --- Normalize SKU Function ---
def normalize_sku(sku):
    """
    Normalizes SKU format for consistent matching.
    - Converts to uppercase
    - Removes spaces, dashes, and special characters
    - Handles leading zeros
    """
    if not sku or not isinstance(sku, str):
        return ""
    
    # Convert to uppercase
    normalized = sku.upper()
    
    # Remove spaces, dashes, and special characters
    normalized = re.sub(r'[^A-Z0-9]', '', normalized)
    
    return normalized

# --- Modified Load and Validate Purchases Function ---
def load_and_validate_purchases_from_supabase(supabase: Client):
    logging.info(f"Loading purchases data from Supabase table: {SUPABASE_PURCHASES_TABLE_NAME}")
    try:
        # Fetch all necessary columns. Assuming remaining_unit_qty > 0 lots are active.
        data, error = supabase.table(SUPABASE_PURCHASES_TABLE_NAME).select(
            "lot_id, po_number, sku, received_date, original_unit_qty, unit_price, freight_cost_per_unit, remaining_unit_qty"
        ).gt("remaining_unit_qty", 0).execute() # Only fetch lots with stock

        if hasattr(data, 'error') and data.error:
            logging.error(f"Error fetching data from Supabase: {data.error}")
            return None
        
        # Handle different Supabase client library versions for response structure
        if hasattr(data, 'data'): # v2.x.x client
            purchase_records = data.data
        elif isinstance(data, (list, tuple)) and len(data) == 2 and data[0] == 'data': # v1.x.x client
            purchase_records = data[1]
        else:
            logging.error(f"Unexpected response structure from Supabase: {data}")
            return None

        if not purchase_records:
            logging.warning("No purchase lot records found in Supabase or no lots with remaining quantity > 0.")
            # Return an empty DataFrame with expected columns if no data, so downstream functions don't break
            cols = ["Lot_ID", "PO_Number", "SKU", "Received_Date", "Original_Unit_Qty", "Unit_Price", "Freight_Cost_Per_Unit", "Remaining_Unit_Qty"]
            return pd.DataFrame(columns=cols)

        df = pd.DataFrame(purchase_records)
        logging.info(f"Successfully fetched {len(df)} records from Supabase.")

        # Rename columns to match script's internal naming convention
        # Supabase typically uses snake_case, script used PascalCase/specific names
        rename_map = {
            "lot_id": "Lot_ID",
            "po_number": "PO_Number",
            "sku": "SKU",
            "received_date": "Received_Date",
            "original_unit_qty": "Original_Unit_Qty",
            "unit_price": "Unit_Price",
            "freight_cost_per_unit": "Freight_Cost_Per_Unit",
            "remaining_unit_qty": "Remaining_Unit_Qty"
        }
        df.rename(columns=rename_map, inplace=True)

        # Validate required columns are present after rename
        required_cols_internal = list(rename_map.values())
        missing_cols = [col for col in required_cols_internal if col not in df.columns]
        if missing_cols:
            logging.error(f"Missing expected columns after fetching from Supabase and renaming: {', '.join(missing_cols)}")
            return None

    except Exception as e:
        logging.error(f"Error loading or processing purchases data from Supabase: {e}")
        return None

    # Data type conversions and validations (similar to original script)
    try:
        df["Received_Date"] = pd.to_datetime(df["Received_Date"], errors='coerce')
        
        numeric_cols = {"Original_Unit_Qty": int, "Remaining_Unit_Qty": int, "Unit_Price": float, "Freight_Cost_Per_Unit": float}
        for col, target_type in numeric_cols.items():
            df[col] = pd.to_numeric(df[col], errors='coerce')
            if df[col].isna().any():
                logging.warning(f"NaN values found in column \'{col}\' after numeric conversion. Filling with 0.")
                df[col] = df[col].fillna(0)
            df[col] = df[col].astype(target_type)

    except Exception as e:
        logging.error(f"Error converting data types in purchases data from Supabase: {e}")
        return None

    # Validations (dates, negative values)
    if df["Received_Date"].isna().any():
        logging.warning("Rows with invalid 'Received_Date' found in Supabase data. These rows will be excluded.")
        df = df[df["Received_Date"].notna()].copy()
        if df.empty:
            logging.error("All purchase rows excluded due to invalid 'Received_Date'. Cannot proceed.")
            return None

    if (df["Original_Unit_Qty"] < 0).any() or (df["Remaining_Unit_Qty"] < 0).any() or \
       (df["Unit_Price"] < 0).any() or (df["Freight_Cost_Per_Unit"] < 0).any():
        logging.error("Purchases data from Supabase contains negative critical values. Processing halted.")
        return None

    # Ensure PO_Number exists, default if not (though it should from Supabase)
    if "PO_Number" not in df.columns: df["PO_Number"] = "UNKNOWN_PO"
    df["PO_Number"] = df["PO_Number"].fillna("UNKNOWN_PO")

    # Total_Lot_Cost calculation (can be useful for reporting, though not strictly needed for FIFO if costs are per unit)
    df["Total_Lot_Cost"] = (df["Original_Unit_Qty"] * (df["Unit_Price"] + df["Freight_Cost_Per_Unit"])).astype(float)
    
    # Add normalized SKU column for matching
    df["Normalized_SKU"] = df["SKU"].apply(normalize_sku)
    
    # Sort by SKU and Received_Date for FIFO processing
    df.sort_values(by=["SKU", "Received_Date"], ascending=[True, True], inplace=True)
    logging.info("Purchases data from Supabase loaded and validated successfully.")
    return df

# --- Enhanced Load and Validate Sales Function ---
def load_and_validate_sales_user_format(file_path):
    logging.info(f"Loading user sales data from: {file_path}")
    try:
        if file_path.lower().endswith(".csv"):
            df = pd.read_csv(file_path, dtype=str)
        elif file_path.lower().endswith((".xls", ".xlsx")):
            df = pd.read_excel(file_path, dtype=str)
        else:
            logging.error(f"Unsupported file format for sales: {file_path}. Please use CSV or Excel.")
            return None
    except FileNotFoundError:
        logging.error(f"Sales file not found: {file_path}")
        return None
    except Exception as e:
        logging.error(f"Error loading sales file {file_path}: {e}")
        return None

    # Enhanced debugging: Print all column names found in the file
    logging.info(f"Found columns in sales file: {list(df.columns)}")
    
    # Clean column names: strip whitespace, convert to lowercase for case-insensitive matching
    df.columns = [col.strip() for col in df.columns]
    
    # Create a mapping of normalized column names (lowercase, no spaces) to actual column names
    normalized_cols = {col.lower().replace(' ', ''): col for col in df.columns}
    logging.info(f"Normalized column mapping: {normalized_cols}")
    
    # Check for required columns with more flexible matching
    required_cols_found = True
    column_mapping = {}
    
    for expected_col, internal_col in USER_SALES_COLUMNS_MAPPING.items():
        # Try exact match first
        if expected_col in df.columns:
            column_mapping[expected_col] = internal_col
            continue
            
        # Try normalized match (lowercase, no spaces)
        normalized_expected = expected_col.lower().replace(' ', '')
        if normalized_expected in normalized_cols:
            actual_col = normalized_cols[normalized_expected]
            column_mapping[actual_col] = internal_col
            logging.info(f"Found column '{actual_col}' matching expected '{expected_col}'")
            continue
            
        # Try partial match as last resort
        partial_matches = [col for col in df.columns if expected_col.lower() in col.lower()]
        if partial_matches:
            column_mapping[partial_matches[0]] = internal_col
            logging.info(f"Using partial match: '{partial_matches[0]}' for expected '{expected_col}'")
            continue
            
        logging.error(f"Could not find a match for required column '{expected_col}'")
        required_cols_found = False
    
    if not required_cols_found:
        logging.error(f"Missing required columns in user sales data. Expected columns based on mapping: {USER_SALES_COLUMNS_MAPPING}")
        logging.error(f"Available columns in file: {list(df.columns)}")
        return None
    
    # Rename columns using our discovered mapping
    logging.info(f"Using column mapping: {column_mapping}")
    df.rename(columns=column_mapping, inplace=True)

    # Verify all required internal columns now exist
    required_internal_cols = list(USER_SALES_COLUMNS_MAPPING.values())
    missing_cols = [col for col in required_internal_cols if col not in df.columns]
    if missing_cols:
        logging.error(f"After column mapping, still missing required internal columns: {', '.join(missing_cols)}")
        return None

    try:
        # Handle various date formats for Month
        try:
            df["Sale_Date"] = pd.to_datetime(df["Sale_Month_Str"], format='%B %Y', errors='coerce')
        except:
            try:
                # Try alternative format (e.g., MM/DD/YY)
                df["Sale_Date"] = pd.to_datetime(df["Sale_Month_Str"], errors='coerce')
                # Set to end of month
                df["Sale_Date"] = df["Sale_Date"] + MonthEnd(0)
                logging.info(f"Parsed dates using alternative format: {df['Sale_Date'].iloc[0]}")
            except:
                logging.error(f"Could not parse dates in format: {df['Sale_Month_Str'].iloc[0]}")
                return None
        
        # Clean and convert quantity values
        original_qty_sold_series = df["Quantity_Sold"].copy()
        df["Quantity_Sold"] = df["Quantity_Sold"].astype(str).str.replace(r'[$,]', '', regex=True).str.strip()
        df["Quantity_Sold_Numeric"] = pd.to_numeric(df["Quantity_Sold"], errors='coerce')
        
        # Log quantity conversion issues
        coerced_to_zero_indices = df[(df["Quantity_Sold_Numeric"].fillna(0) == 0) & 
                                     (original_qty_sold_series.fillna("").str.strip() != "") & 
                                     (original_qty_sold_series.fillna("").str.strip() != "0")].index
        for idx in coerced_to_zero_indices[:min(5, len(coerced_to_zero_indices))]:
            logging.warning(f"Sales quantity '{original_qty_sold_series.loc[idx]}' for SKU {df.loc[idx, 'SKU']} (Month: {df.loc[idx, 'Sale_Month_Str']}) was coerced to 0 due to non-numeric content.")
        
        df["Quantity_Sold"] = df["Quantity_Sold_Numeric"].fillna(0).astype(int)
        df.drop(columns=["Quantity_Sold_Numeric"], inplace=True)

    except Exception as e:
        logging.error(f"Error converting data types or month to date in user sales data: {e}")
        return None

    if (df["Quantity_Sold"] < 0).any():
        logging.warning("User sales data contains negative 'Quantity_Sold'. These will be ignored or handled by FIFO logic if zero.")

    # Add normalized SKU column for matching
    df["Normalized_SKU"] = df["SKU"].apply(normalize_sku)
    
    # Summarize by SKU and Sale_Date
    df_summarized = df.groupby(["SKU", "Normalized_SKU", "Sale_Date"])["Quantity_Sold"].sum().reset_index()
    df_summarized["Sales_Order_ID"] = "MONTHLY_SUMMARY_" + df_summarized["Sale_Date"].dt.strftime('%Y%m%d') + "_" + df_summarized["SKU"]
    df_summarized = df_summarized[df_summarized["Quantity_Sold"] > 0]
    
    if df_summarized.empty:
        logging.warning("All sales had zero or negative quantities after processing and summarization.")
        return pd.DataFrame(columns=["SKU", "Normalized_SKU", "Sale_Date", "Quantity_Sold", "Sales_Order_ID"])

    logging.info("User sales data loaded, validated, and summarized successfully.")
    return df_summarized

# --- New Validation Function ---
def validate_sales_against_inventory(df_sales, df_purchases, output_dir):
    """
    Performs comprehensive validation of sales data against inventory.
    Returns a tuple of (validation_passed, validation_report_path)
    """
    logging.info("Starting pre-processing validation of sales data against inventory...")
    
    if df_sales is None or df_purchases is None:
        logging.error("Sales or purchases data is None. Cannot perform validation.")
        return False, None
    
    if df_sales.empty:
        logging.warning("Sales data is empty. No validation needed.")
        return True, None
    
    # Create validation report dataframe
    validation_errors = []
    
    # Create inventory lookup by normalized SKU
    inventory_by_sku = {}
    for _, row in df_purchases.iterrows():
        normalized_sku = row["Normalized_SKU"]
        if normalized_sku not in inventory_by_sku:
            inventory_by_sku[normalized_sku] = {
                "original_sku": row["SKU"],
                "total_qty": 0,
                "lots": []
            }
        
        inventory_by_sku[normalized_sku]["total_qty"] += row["Remaining_Unit_Qty"]
        inventory_by_sku[normalized_sku]["lots"].append({
            "lot_id": row["Lot_ID"],
            "po_number": row["PO_Number"],
            "received_date": row["Received_Date"],
            "remaining_qty": row["Remaining_Unit_Qty"]
        })
    
    # Check each sale against inventory
    for _, sale in df_sales.iterrows():
        normalized_sku = sale["Normalized_SKU"]
        original_sku = sale["SKU"]
        quantity_needed = sale["Quantity_Sold"]
        sale_date = sale["Sale_Date"]
        sales_order_id = sale["Sales_Order_ID"]
        
        # Check if SKU exists in inventory
        if normalized_sku not in inventory_by_sku:
            validation_errors.append({
                "error_type": VALIDATION_ERROR_TYPES["SKU_NOT_FOUND"],
                "sales_order_id": sales_order_id,
                "original_sku": original_sku,
                "normalized_sku": normalized_sku,
                "sale_date": sale_date,
                "quantity_needed": quantity_needed,
                "quantity_available": 0,
                "lot_id": "N/A",
                "description": f"SKU '{original_sku}' not found in inventory"
            })
            continue
        
        # Check if sufficient quantity is available
        inventory_info = inventory_by_sku[normalized_sku]
        available_qty = inventory_info["total_qty"]
        
        if available_qty < quantity_needed:
            # Get lot details for error reporting
            lot_details = ", ".join([
                f"Lot {lot['lot_id']} (PO: {lot['po_number']}): {lot['remaining_qty']} units"
                for lot in inventory_info["lots"]
            ])
            
            validation_errors.append({
                "error_type": VALIDATION_ERROR_TYPES["INSUFFICIENT_QUANTITY"],
                "sales_order_id": sales_order_id,
                "original_sku": original_sku,
                "normalized_sku": normalized_sku,
                "sale_date": sale_date,
                "quantity_needed": quantity_needed,
                "quantity_available": available_qty,
                "lot_id": ", ".join([lot["lot_id"] for lot in inventory_info["lots"]]),
                "description": f"Insufficient quantity available. Needed: {quantity_needed}, Available: {available_qty}. Lots: {lot_details}"
            })
    
    # Generate validation report
    validation_passed = len(validation_errors) == 0
    
    if not validation_passed:
        # Create validation report dataframe
        df_validation = pd.DataFrame(validation_errors)
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate timestamp for report filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        validation_report_path = os.path.join(output_dir, f"validation_errors_{timestamp}.csv")
        
        # Save validation report
        df_validation.to_csv(validation_report_path, index=False)
        
        # Generate summary
        error_count = len(validation_errors)
        sku_not_found_count = sum(1 for e in validation_errors if e["error_type"] == VALIDATION_ERROR_TYPES["SKU_NOT_FOUND"])
        insufficient_qty_count = sum(1 for e in validation_errors if e["error_type"] == VALIDATION_ERROR_TYPES["INSUFFICIENT_QUANTITY"])
        
        logging.error(f"Validation failed with {error_count} errors:")
        logging.error(f"  - SKUs not found: {sku_not_found_count}")
        logging.error(f"  - Insufficient quantity: {insufficient_qty_count}")
        logging.error(f"Validation report saved to: {validation_report_path}")
        logging.error("Processing halted due to validation errors. Please fix the errors and try again.")
        
        return False, validation_report_path
    
    logging.info("Validation passed successfully. All SKUs found with sufficient quantity.")
    return True, None

# --- Process FIFO Function ---
def process_fifo(supabase: Client, df_purchases_orig: pd.DataFrame, df_sales_orig: pd.DataFrame, output_dir: str):
    if df_purchases_orig is None or df_sales_orig is None:
        logging.error("Input DataFrames for FIFO processing are None. Aborting.")
        return None, None, None
    if df_sales_orig.empty:
        logging.warning("Sales data is empty. No FIFO processing to perform.")
        cogs_cols = ["Sale_Date", "Sales_Order_ID", "SKU", "Lot_ID", "Attributed_Qty", "Attributed_Unit_Price", "Attributed_Freight_Cost_Per_Unit", "Attributed_Total_Unit_Cost", "Attributed_COGS", "Attributed_COGS_Unit_Only", "Attributed_COGS_Freight_Only", "Status"]
        summary_cols = ["Month", "SKU", "Total_Quantity_Sold", "Total_COGS_Blended", "Total_COGS_Unit_Only", "Total_COGS_Freight_Only"]
        return pd.DataFrame(columns=cogs_cols), pd.DataFrame(columns=summary_cols), df_purchases_orig.copy()

    # Validate sales against inventory before processing
    validation_passed, validation_report_path = validate_sales_against_inventory(df_sales_orig, df_purchases_orig, output_dir)
    if not validation_passed:
        logging.error(f"Validation failed. See report at: {validation_report_path}")
        return None, None, None

    df_purchases = df_purchases_orig.copy() # Work on a copy for local modifications
    df_sales = df_sales_orig.copy()
    logging.info("Starting FIFO processing with Supabase integration...")
    cogs_attribution_records = []

    for sale_idx, sale_transaction in df_sales.iterrows():
        current_sku = sale_transaction["SKU"]
        normalized_sku = sale_transaction["Normalized_SKU"]
        quantity_to_attribute = sale_transaction["Quantity_Sold"]
        sale_date = sale_transaction["Sale_Date"]
        sales_order_id = sale_transaction.get("Sales_Order_ID", f"SALE_{sale_idx}")

        logging.info(f"Processing sale: SKU {current_sku}, Qty {quantity_to_attribute}, Date {sale_date}, SO_ID: {sales_order_id}")
        if quantity_to_attribute <= 0: continue

        # Match by normalized SKU for more flexible matching
        lot_mask = (df_purchases["Normalized_SKU"] == normalized_sku) & (df_purchases["Remaining_Unit_Qty"] > 0)
        # Ensure we iterate in FIFO order (already sorted by Received_Date)
        available_lot_indices = df_purchases[lot_mask].index.tolist()

        if not available_lot_indices:
            logging.warning(f"No inventory for SKU {current_sku} for sale on {sale_date}. SO_ID: {sales_order_id}. Requested Qty: {sale_transaction['Quantity_Sold']}")
            cogs_attribution_records.append({
                "Sale_Date": sale_date, "Sales_Order_ID": sales_order_id, "SKU": current_sku,
                "Lot_ID": "UNFULFILLED", "Attributed_Qty": sale_transaction['Quantity_Sold'],
                "Attributed_Unit_Price": 0.0, "Attributed_Freight_Cost_Per_Unit": 0.0,
                "Attributed_Total_Unit_Cost": 0.0, "Attributed_COGS": 0.0,
                "Attributed_COGS_Unit_Only": 0.0, "Attributed_COGS_Freight_Only": 0.0,
                "Status": "No Inventory"
            })
            continue

        original_sale_qty_for_logging = quantity_to_attribute
        for lot_idx in available_lot_indices:
            if quantity_to_attribute == 0: break
            
            lot_remaining_qty_local = df_purchases.loc[lot_idx, "Remaining_Unit_Qty"]
            units_from_this_lot = min(quantity_to_attribute, lot_remaining_qty_local)
            if units_from_this_lot <= 0: continue

            lot_id_db = df_purchases.loc[lot_idx, "Lot_ID"] # This is the Supabase lot_id
            lot_unit_price = df_purchases.loc[lot_idx, "Unit_Price"]
            lot_freight_cost_per_unit = df_purchases.loc[lot_idx, "Freight_Cost_Per_Unit"]
            total_unit_cost_for_lot = lot_unit_price + lot_freight_cost_per_unit

            cogs_attribution_records.append({
                "Sale_Date": sale_date, "Sales_Order_ID": sales_order_id, "SKU": current_sku,
                "Lot_ID": lot_id_db, "Attributed_Qty": units_from_this_lot,
                "Attributed_Unit_Price": lot_unit_price, 
                "Attributed_Freight_Cost_Per_Unit": lot_freight_cost_per_unit,
                "Attributed_Total_Unit_Cost": total_unit_cost_for_lot,
                "Attributed_COGS": units_from_this_lot * total_unit_cost_for_lot,
                "Attributed_COGS_Unit_Only": units_from_this_lot * lot_unit_price,
                "Attributed_COGS_Freight_Only": units_from_this_lot * lot_freight_cost_per_unit,
                "Status": "Fulfilled"
            })

            # Update remaining quantity in local DataFrame
            df_purchases.loc[lot_idx, "Remaining_Unit_Qty"] -= units_from_this_lot
            quantity_to_attribute -= units_from_this_lot

            # Update Supabase with new remaining quantity
            try:
                new_remaining_qty = df_purchases.loc[lot_idx, "Remaining_Unit_Qty"]
                supabase.table(SUPABASE_PURCHASES_TABLE_NAME).update(
                    {"remaining_unit_qty": int(new_remaining_qty)}
                ).eq("lot_id", lot_id_db).execute()
                logging.info(f"Updated lot {lot_id_db} in Supabase. New remaining qty: {new_remaining_qty}")
            except Exception as e:
                logging.error(f"Error updating lot {lot_id_db} in Supabase: {e}")
                # Continue processing but log the error

        if quantity_to_attribute > 0:
            # This should never happen due to validation, but just in case
            logging.warning(f"Could not fully attribute sale for SKU {current_sku}. Remaining qty needed: {quantity_to_attribute}")
            cogs_attribution_records.append({
                "Sale_Date": sale_date, "Sales_Order_ID": sales_order_id, "SKU": current_sku,
                "Lot_ID": "PARTIALLY_UNFULFILLED", "Attributed_Qty": quantity_to_attribute,
                "Attributed_Unit_Price": 0.0, "Attributed_Freight_Cost_Per_Unit": 0.0,
                "Attributed_Total_Unit_Cost": 0.0, "Attributed_COGS": 0.0,
                "Attributed_COGS_Unit_Only": 0.0, "Attributed_COGS_Freight_Only": 0.0,
                "Status": "Partially Unfulfilled"
            })

    # Create COGS attribution DataFrame
    df_cogs_attribution = pd.DataFrame(cogs_attribution_records)
    if df_cogs_attribution.empty:
        logging.warning("No COGS attribution records generated.")
        cogs_cols = ["Sale_Date", "Sales_Order_ID", "SKU", "Lot_ID", "Attributed_Qty", "Attributed_Unit_Price", "Attributed_Freight_Cost_Per_Unit", "Attributed_Total_Unit_Cost", "Attributed_COGS", "Attributed_COGS_Unit_Only", "Attributed_COGS_Freight_Only", "Status"]
        summary_cols = ["Month", "SKU", "Total_Quantity_Sold", "Total_COGS_Blended", "Total_COGS_Unit_Only", "Total_COGS_Freight_Only"]
        return pd.DataFrame(columns=cogs_cols), pd.DataFrame(columns=summary_cols), df_purchases

    # Generate COGS summary
    df_cogs_summary = df_cogs_attribution.groupby(["Sale_Date", "SKU"]).agg({
        "Attributed_Qty": "sum",
        "Attributed_COGS": "sum",
        "Attributed_COGS_Unit_Only": "sum",
        "Attributed_COGS_Freight_Only": "sum"
    }).reset_index()

    df_cogs_summary.rename(columns={
        "Sale_Date": "Month",
        "Attributed_Qty": "Total_Quantity_Sold",
        "Attributed_COGS": "Total_COGS_Blended",
        "Attributed_COGS_Unit_Only": "Total_COGS_Unit_Only",
        "Attributed_COGS_Freight_Only": "Total_COGS_Freight_Only"
    }, inplace=True)

    logging.info("FIFO processing completed successfully.")
    return df_cogs_attribution, df_cogs_summary, df_purchases

# --- Main Function ---
def main():
    parser = argparse.ArgumentParser(description='FIFO Inventory Lot Attribution Calculator with Supabase Integration and Validation')
    parser.add_argument('--sales_file', required=True, help='Path to sales data file (CSV or Excel)')
    parser.add_argument('--output_dir', required=True, help='Directory to save output files')
    parser.add_argument('--log_file', required=True, help='Path to log file')
    parser.add_argument('--validate_only', action='store_true', help='Only validate sales data without processing')
    args = parser.parse_args()

    # Set up file logging
    file_handler = logging.FileHandler(args.log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)

    logging.info("Script started.")
    logging.info(f"Sales file: {args.sales_file}")
    logging.info(f"Output directory: {args.output_dir}")
    logging.info(f"Log file: {args.log_file}")
    logging.info(f"Validate only: {args.validate_only}")

    # Create output directory if it doesn't exist
    try:
        os.makedirs(args.output_dir, exist_ok=True)
        logging.info(f"Created output directory: {args.output_dir}")
    except Exception as e:
        logging.error(f"Error creating output directory: {e}")
        return

    # Initialize Supabase client
    supabase = get_supabase_client()
    if supabase is None:
        logging.error("Failed to initialize Supabase client. Exiting.")
        return

    # Load purchases data from Supabase
    df_purchases = load_and_validate_purchases_from_supabase(supabase)
    if df_purchases is None:
        logging.error("Failed to load or validate purchases data from Supabase. Exiting.")
        return

    # Load sales data
    df_sales = load_and_validate_sales_user_format(args.sales_file)
    if df_sales is None:
        logging.error("Failed to load or validate sales data. Exiting.")
        return

    # Validate sales against inventory
    validation_passed, validation_report_path = validate_sales_against_inventory(df_sales, df_purchases, args.output_dir)
    
    if args.validate_only:
        if validation_passed:
            logging.info("Validation completed successfully. All sales can be processed.")
            print("\nValidation Summary:")
            print("-------------------")
            print("✅ All validation checks passed!")
            print(f"Total Sales Entries: {len(df_sales)}")
            print(f"Total SKUs: {df_sales['SKU'].nunique()}")
            print(f"Total Units: {df_sales['Quantity_Sold'].sum()}")
            print("\nNext Steps: Run the script without --validate_only to process the sales.")
        else:
            logging.error("Validation failed. Please fix the errors and try again.")
            print("\nValidation Summary:")
            print("-------------------")
            print("❌ Validation failed!")
            print(f"Validation report saved to: {validation_report_path}")
            print("\nNext Steps: Fix the errors in the validation report and run validation again.")
        return
    
    if not validation_passed:
        logging.error("Validation failed. Exiting without processing sales.")
        return

    # Process FIFO
    df_cogs_attribution, df_cogs_summary, df_updated_inventory = process_fifo(supabase, df_purchases, df_sales, args.output_dir)
    if df_cogs_attribution is None or df_cogs_summary is None or df_updated_inventory is None:
        logging.error("FIFO processing failed. Exiting.")
        return

    # Save output files
    try:
        attribution_file = os.path.join(args.output_dir, "cogs_attribution_supabase.csv")
        summary_file = os.path.join(args.output_dir, "cogs_summary_supabase.csv")
        inventory_file = os.path.join(args.output_dir, "updated_inventory_snapshot_supabase.csv")

        df_cogs_attribution.to_csv(attribution_file, index=False)
        df_cogs_summary.to_csv(summary_file, index=False)
        df_updated_inventory.to_csv(inventory_file, index=False)

        logging.info(f"Saved COGS attribution to: {attribution_file}")
        logging.info(f"Saved COGS summary to: {summary_file}")
        logging.info(f"Saved updated inventory snapshot to: {inventory_file}")
    except Exception as e:
        logging.error(f"Error saving output files: {e}")

    logging.info("Script completed successfully.")

if __name__ == "__main__":
    main()
