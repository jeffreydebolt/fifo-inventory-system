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
    "SKU": "SKU",                # Now matches user's actual capitalization
    "Units Moved": "Quantity_Sold",  # Now matches user's actual capitalization
    "Month": "Sale_Month_Str"    # Matches user's actual capitalization
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
    - Handles Amazon prefixes and suffixes
    """
    if not sku or not isinstance(sku, str):
        return ""
    
    # Convert to uppercase
    normalized = sku.upper()
    
    # Remove Amazon prefixes if present
    if normalized.startswith("AMAZON."):
        parts = normalized.split(".")
        if len(parts) > 2:
            normalized = parts[-1]  # Take the last part after Amazon.Found.
    
    # Remove suffixes with periods (like .missing1)
    if "." in normalized:
        normalized = normalized.split(".")[0]
    
    # Remove spaces, dashes, and special characters
    normalized = re.sub(r'[^A-Z0-9]', '', normalized)
    
    return normalized

# --- Modified Load and Validate Purchases Function ---
def load_and_validate_purchases_from_supabase(supabase: Client):
    logging.info(f"Loading purchases data from Supabase table: {SUPABASE_PURCHASES_TABLE_NAME}")
    try:
        # Fetch all necessary columns. Assuming remaining_unit_qty > 0 lots are active.
        data = supabase.table(SUPABASE_PURCHASES_TABLE_NAME).select(
            "lot_id, po_number, sku, received_date, original_unit_qty, unit_price, freight_cost_per_unit, remaining_unit_qty"
        ).gt("remaining_unit_qty", 0).execute()

        if hasattr(data, 'error') and data.error:
            logging.error(f"Error fetching data from Supabase: {data.error}")
            return None
        
        # Handle different Supabase client library versions for response structure
        if hasattr(data, 'data'): # v2.x.x client
            purchase_records = data.data
        else: # v1.x.x client or other structure
            purchase_records = data[1] if isinstance(data, (list, tuple)) and len(data) > 1 else data

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
    
    # Clean column names: strip whitespace
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
        # Try multiple date formats
        df["Sale_Date"] = None
        
        # First try %B %Y format (December 2022)
        try:
            df["Sale_Date"] = pd.to_datetime(df["Sale_Month_Str"], format='%B %Y', errors='coerce')
            if not df["Sale_Date"].isna().all():
                logging.info("Parsed dates using %B %Y format")
        except:
            pass
        
        # If that failed, try MM/DD/YYYY format
        if df["Sale_Date"].isna().all():
            try:
                df["Sale_Date"] = pd.to_datetime(df["Sale_Month_Str"], format='%m/%d/%Y', errors='coerce')
                if not df["Sale_Date"].isna().all():
                    df["Sale_Date"] = df["Sale_Date"] + MonthEnd(0)
                    logging.info("Parsed dates using %m/%d/%Y format")
            except:
                pass
        
        # If still failed, try generic parsing
        if df["Sale_Date"].isna().all():
            try:
                df["Sale_Date"] = pd.to_datetime(df["Sale_Month_Str"], errors='coerce')
                df["Sale_Date"] = df["Sale_Date"] + MonthEnd(0)
                logging.info("Parsed dates using generic format")
            except:
                logging.error(f"Could not parse dates in any format: {df['Sale_Month_Str'].iloc[0]}")
                return None
        
        # Check if we still have NaT values
        if df["Sale_Date"].isna().all():
            logging.error(f"All dates resulted in NaT. Sample: {df['Sale_Month_Str'].iloc[0]}")
            return None
        
        # Clean and convert quantity values
        original_qty_sold_series = df["Quantity_Sold"].copy()
        df["Quantity_Sold"] = df["Quantity_Sold"].astype(str).str.replace(r'[$,]', '', regex=True).str.strip()
        
        # Handle #VALUE! errors from Excel
        df.loc[df["Quantity_Sold"] == "#VALUE!", "Quantity_Sold"] = "0"
        
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
    
    # Filter out rows with empty SKUs
    df = df[df["SKU"].notna() & (df["SKU"] != "")]
    
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
                "description": f"SKU {original_sku} not found in inventory"
            })
            continue
        
        # Check if sufficient quantity is available
        inventory_info = inventory_by_sku[normalized_sku]
        if inventory_info["total_qty"] < quantity_needed:
            validation_errors.append({
                "error_type": VALIDATION_ERROR_TYPES["INSUFFICIENT_QUANTITY"],
                "sales_order_id": sales_order_id,
                "original_sku": original_sku,
                "normalized_sku": normalized_sku,
                "sale_date": sale_date,
                "quantity_needed": quantity_needed,
                "quantity_available": inventory_info["total_qty"],
                "lot_id": ", ".join([str(lot["lot_id"]) for lot in inventory_info["lots"]]),
                "description": f"Insufficient quantity for SKU {original_sku}. Need {quantity_needed}, have {inventory_info['total_qty']}"
            })
    
    # If no errors, validation passed
    if not validation_errors:
        logging.info("Validation passed! All sales can be fulfilled from inventory.")
        return True, None
    
    # Create validation report
    df_validation = pd.DataFrame(validation_errors)
    
    # Save validation report
    validation_report_path = os.path.join(output_dir, "validation_errors.csv")
    df_validation.to_csv(validation_report_path, index=False)
    
    # Log validation summary
    sku_not_found_count = len(df_validation[df_validation["error_type"] == VALIDATION_ERROR_TYPES["SKU_NOT_FOUND"]])
    insufficient_qty_count = len(df_validation[df_validation["error_type"] == VALIDATION_ERROR_TYPES["INSUFFICIENT_QUANTITY"]])
    
    logging.warning(f"Validation failed with {len(validation_errors)} errors:")
    logging.warning(f"  - SKUs not found in inventory: {sku_not_found_count}")
    logging.warning(f"  - Insufficient quantity errors: {insufficient_qty_count}")
    logging.warning(f"Validation report saved to: {validation_report_path}")
    
    # Create SKU mapping suggestions for not found SKUs
    if sku_not_found_count > 0:
        create_sku_mapping_suggestions(df_validation, df_purchases, output_dir)
    
    return False, validation_report_path

# --- SKU Mapping Suggestions ---
def create_sku_mapping_suggestions(df_validation, df_purchases, output_dir):
    """Creates suggestions for mapping sales SKUs to inventory SKUs"""
    not_found_skus = df_validation[df_validation["error_type"] == VALIDATION_ERROR_TYPES["SKU_NOT_FOUND"]]
    
    if not_found_skus.empty:
        return
    
    # Get all inventory SKUs
    inventory_skus = df_purchases[["SKU", "Normalized_SKU"]].drop_duplicates()
    
    # Create suggestions
    suggestions = []
    
    for _, row in not_found_skus.iterrows():
        sales_sku = row["original_sku"]
        normalized_sales_sku = row["normalized_sku"]
        
        # Look for similar SKUs in inventory
        for _, inv_row in inventory_skus.iterrows():
            inv_sku = inv_row["SKU"]
            normalized_inv_sku = inv_row["Normalized_SKU"]
            
            # Check for partial matches
            if (normalized_sales_sku in normalized_inv_sku) or (normalized_inv_sku in normalized_sales_sku):
                similarity = "Partial Match"
            elif normalized_sales_sku[:3] == normalized_inv_sku[:3]:
                similarity = "Prefix Match"
            else:
                continue
            
            suggestions.append({
                "sales_sku": sales_sku,
                "inventory_sku": inv_sku,
                "similarity": similarity,
                "normalized_sales_sku": normalized_sales_sku,
                "normalized_inventory_sku": normalized_inv_sku
            })
    
    if suggestions:
        df_suggestions = pd.DataFrame(suggestions)
        suggestions_path = os.path.join(output_dir, "sku_mapping_suggestions.csv")
        df_suggestions.to_csv(suggestions_path, index=False)
        logging.info(f"SKU mapping suggestions saved to: {suggestions_path}")

# --- FIFO Processing Function ---
def process_fifo(df_sales, df_purchases, supabase):
    """
    Process sales using FIFO method and update inventory in Supabase.
    Returns a tuple of (cogs_attribution, cogs_summary, updated_inventory)
    """
    if df_sales.empty:
        logging.warning("Sales data is empty. No FIFO processing to perform.")
        return pd.DataFrame(), pd.DataFrame(), df_purchases.copy()
    
    # Sort sales by date
    df_sales = df_sales.sort_values("Sale_Date")
    
    # Initialize results dataframes
    cogs_attribution = []
    updated_inventory = df_purchases.copy()
    
    # Process each sale
    for _, sale in df_sales.iterrows():
        normalized_sku = sale["Normalized_SKU"]
        original_sku = sale["SKU"]
        quantity_needed = sale["Quantity_Sold"]
        sale_date = sale["Sale_Date"]
        sales_order_id = sale["Sales_Order_ID"]
        
        # Find matching lots for this SKU
        matching_lots = updated_inventory[updated_inventory["Normalized_SKU"] == normalized_sku].copy()
        
        if matching_lots.empty:
            logging.warning(f"No matching lots found for SKU {original_sku} (normalized: {normalized_sku}). Skipping.")
            continue
        
        # Sort lots by received date (FIFO)
        matching_lots = matching_lots.sort_values("Received_Date")
        
        # Allocate quantity from lots
        remaining_to_allocate = quantity_needed
        
        for idx, lot in matching_lots.iterrows():
            if remaining_to_allocate <= 0:
                break
            
            lot_id = lot["Lot_ID"]
            available_qty = lot["Remaining_Unit_Qty"]
            
            if available_qty <= 0:
                continue
            
            # Calculate quantity to take from this lot
            qty_from_lot = min(remaining_to_allocate, available_qty)
            
            # Update remaining quantity in inventory
            updated_inventory.loc[idx, "Remaining_Unit_Qty"] -= qty_from_lot
            
            # Calculate COGS for this allocation
            unit_cost = lot["Unit_Price"] + lot["Freight_Cost_Per_Unit"]
            cogs_amount = qty_from_lot * unit_cost
            
            # Record COGS attribution
            cogs_attribution.append({
                "Sales_Order_ID": sales_order_id,
                "Sale_Date": sale_date,
                "SKU": original_sku,
                "Lot_ID": lot_id,
                "PO_Number": lot["PO_Number"],
                "Received_Date": lot["Received_Date"],
                "Quantity_From_Lot": qty_from_lot,
                "Unit_Cost": unit_cost,
                "COGS_Amount": cogs_amount
            })
            
            # Update remaining to allocate
            remaining_to_allocate -= qty_from_lot
            
            # Update Supabase
            try:
                supabase.table(SUPABASE_PURCHASES_TABLE_NAME).update(
                    {"remaining_unit_qty": int(updated_inventory.loc[idx, "Remaining_Unit_Qty"])}
                ).eq("lot_id", lot_id).execute()
                logging.info(f"Updated lot {lot_id} in Supabase. New remaining quantity: {updated_inventory.loc[idx, 'Remaining_Unit_Qty']}")
            except Exception as e:
                logging.error(f"Error updating lot {lot_id} in Supabase: {e}")
        
        if remaining_to_allocate > 0:
            logging.warning(f"Could not fully allocate quantity for SKU {original_sku}. Remaining: {remaining_to_allocate}")
    
    # Create COGS attribution dataframe
    df_cogs_attribution = pd.DataFrame(cogs_attribution)
    
    if df_cogs_attribution.empty:
        logging.warning("No COGS attribution generated. Check if sales data matched any inventory.")
        return pd.DataFrame(), pd.DataFrame(), updated_inventory
    
    # Create COGS summary
    df_cogs_summary = df_cogs_attribution.groupby(["SKU", "Sale_Date"]).agg({
        "Quantity_From_Lot": "sum",
        "COGS_Amount": "sum"
    }).reset_index()
    
    df_cogs_summary.rename(columns={
        "Quantity_From_Lot": "Total_Quantity",
        "COGS_Amount": "Total_COGS"
    }, inplace=True)
    
    df_cogs_summary["Average_Unit_Cost"] = df_cogs_summary["Total_COGS"] / df_cogs_summary["Total_Quantity"]
    
    return df_cogs_attribution, df_cogs_summary, updated_inventory

# --- Main Function ---
def main():
    parser = argparse.ArgumentParser(description="FIFO Calculator with Supabase Integration")
    parser.add_argument("--sales_file", required=True, help="Path to sales data file (CSV or Excel)")
    parser.add_argument("--output_dir", required=True, help="Directory to save output files")
    parser.add_argument("--log_file", required=True, help="Path to log file")
    parser.add_argument("--validate_only", action="store_true", help="Only validate sales data against inventory, don't process FIFO")
    
    args = parser.parse_args()
    
    # Add file handler for logging
    file_handler = logging.FileHandler(args.log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)
    
    logging.info("Script started.")
    logging.info(f"Sales file: {args.sales_file}")
    logging.info(f"Output directory: {args.output_dir}")
    logging.info(f"Log file: {args.log_file}")
    logging.info(f"Validate only: {args.validate_only}")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        logging.info(f"Created output directory: {args.output_dir}")
    
    # Initialize Supabase client
    supabase = get_supabase_client()
    if not supabase:
        logging.error("Failed to initialize Supabase client. Exiting.")
        return
    
    # Load purchases data from Supabase
    df_purchases = load_and_validate_purchases_from_supabase(supabase)
    if df_purchases is None:
        logging.error("Failed to load or validate purchases data. Exiting.")
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
            logging.info("Validation completed successfully. All sales can be fulfilled from inventory.")
        else:
            logging.warning(f"Validation completed with errors. See report at: {validation_report_path}")
        return
    
    # Process FIFO
    df_cogs_attribution, df_cogs_summary, df_updated_inventory = process_fifo(df_sales, df_purchases, supabase)
    
    # Save results
    cogs_attribution_path = os.path.join(args.output_dir, "cogs_attribution_supabase.csv")
    cogs_summary_path = os.path.join(args.output_dir, "cogs_summary_supabase.csv")
    updated_inventory_path = os.path.join(args.output_dir, "updated_inventory_snapshot_supabase.csv")
    
    df_cogs_attribution.to_csv(cogs_attribution_path, index=False)
    df_cogs_summary.to_csv(cogs_summary_path, index=False)
    df_updated_inventory.to_csv(updated_inventory_path, index=False)
    
    logging.info(f"Saved COGS attribution to: {cogs_attribution_path}")
    logging.info(f"Saved COGS summary to: {cogs_summary_path}")
    logging.info(f"Saved updated inventory snapshot to: {updated_inventory_path}")
    
    logging.info("Script completed successfully.")

if __name__ == "__main__":
    main()
