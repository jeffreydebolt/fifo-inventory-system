#!/usr/bin/env python3

import pandas as pd
import os
import logging
from datetime import datetime
from pandas.tseries.offsets import MonthEnd
import argparse
from supabase import create_client, Client # Added for Supabase

# --- Supabase Configuration ---
SUPABASE_PURCHASES_TABLE_NAME = "purchase_lots"

# --- Logging Configuration (remains the same) ---
# Log file path will be determined by argparse or default

# --- Column Mappings (Sales remains, Purchases will be adapted for Supabase) ---
USER_SALES_COLUMNS_MAPPING = {
    "sku": "SKU",
    "units moved": "Quantity_Sold",
    "Month": "Sale_Month_Str" # Temporary column to hold month string
}

# --- Supabase Client Initialization ---
def get_supabase_client():
    """Initializes and returns the Supabase client."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        logging.error("SUPABASE_URL and SUPABASE_KEY environment variables must be set.")
        return None
    try:
        supabase: Client = create_client(url, key)
        logging.info("Supabase client initialized successfully.")
        return supabase
    except Exception as e:
        logging.error(f"Error creating Supabase client: {e}")
        return None

# --- Modified Load and Validate Purchases Function ---
def load_and_validate_purchases_from_supabase(supabase: Client):
    logging.info(f"Loading purchases data from Supabase table: {SUPABASE_PURCHASES_TABLE_NAME}")
    try:
        # Fetch all necessary columns. Assuming remaining_unit_qty > 0 lots are active.
        # Adjust select query as needed for your table structure.
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
    
    # Sort by SKU and Received_Date for FIFO processing
    df.sort_values(by=["SKU", "Received_Date"], ascending=[True, True], inplace=True)
    logging.info("Purchases data from Supabase loaded and validated successfully.")
    return df

# --- Load and Validate Sales (remains largely the same) ---
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

    df.rename(columns=USER_SALES_COLUMNS_MAPPING, inplace=True)

    required_user_cols = list(USER_SALES_COLUMNS_MAPPING.values())
    missing_cols = [col for col in required_user_cols if col not in df.columns]
    if missing_cols:
        logging.error(f"Missing required columns in user sales data: {', '.join(missing_cols)}. Expected based on mapping: {USER_SALES_COLUMNS_MAPPING}")
        return None

    try:
        df["Sale_Date"] = pd.to_datetime(df["Sale_Month_Str"], format='%B %Y', errors='coerce') + MonthEnd(0)
        original_qty_sold_series = df["Quantity_Sold"].copy()
        df["Quantity_Sold"] = df["Quantity_Sold"].astype(str).str.replace(r'[$,]', '', regex=True).str.strip()
        df["Quantity_Sold_Numeric"] = pd.to_numeric(df["Quantity_Sold"], errors='coerce')
        
        coerced_to_zero_indices = df[(df["Quantity_Sold_Numeric"].fillna(0) == 0) & (original_qty_sold_series.fillna("").str.strip() != "") & (original_qty_sold_series.fillna("").str.strip() != "0")].index
        for idx in coerced_to_zero_indices[:min(5, len(coerced_to_zero_indices))]:
            logging.warning(f"Sales quantity '{original_qty_sold_series.loc[idx]}' for SKU {df.loc[idx, 'SKU']} (Month: {df.loc[idx, 'Sale_Month_Str']}) was coerced to 0 due to non-numeric content.")
        df["Quantity_Sold"] = df["Quantity_Sold_Numeric"].fillna(0).astype(int)
        df.drop(columns=["Quantity_Sold_Numeric"], inplace=True)

    except Exception as e:
        logging.error(f"Error converting data types or month to date in user sales data: {e}")
        return None

    if (df["Quantity_Sold"] < 0).any():
        logging.warning("User sales data contains negative 'Quantity_Sold'. These will be ignored or handled by FIFO logic if zero.")

    df_summarized = df.groupby(["SKU", "Sale_Date"])["Quantity_Sold"].sum().reset_index()
    df_summarized["Sales_Order_ID"] = "MONTHLY_SUMMARY_" + df_summarized["Sale_Date"].dt.strftime('%Y%m%d') + "_" + df_summarized["SKU"]
    df_summarized = df_summarized[df_summarized["Quantity_Sold"] > 0]
    if df_summarized.empty:
        logging.warning("All sales had zero or negative quantities after processing and summarization.")
        return pd.DataFrame(columns=["SKU", "Sale_Date", "Quantity_Sold", "Sales_Order_ID"])

    logging.info("User sales data loaded, validated, and summarized successfully.")
    return df_summarized

# --- Modified Process FIFO Function ---
def process_fifo(supabase: Client, df_purchases_orig: pd.DataFrame, df_sales_orig: pd.DataFrame):
    if df_purchases_orig is None or df_sales_orig is None:
        logging.error("Input DataFrames for FIFO processing are None. Aborting.")
        return None, None, None
    if df_sales_orig.empty:
        logging.warning("Sales data is empty. No FIFO processing to perform.")
        cogs_cols = ["Sale_Date", "Sales_Order_ID", "SKU", "Lot_ID", "Attributed_Qty", "Attributed_Unit_Price", "Attributed_Freight_Cost_Per_Unit", "Attributed_Total_Unit_Cost", "Attributed_COGS", "Attributed_COGS_Unit_Only", "Attributed_COGS_Freight_Only", "Status"]
        summary_cols = ["Month", "SKU", "Total_Quantity_Sold", "Total_COGS_Blended", "Total_COGS_Unit_Only", "Total_COGS_Freight_Only"]
        return pd.DataFrame(columns=cogs_cols), pd.DataFrame(columns=summary_cols), df_purchases_orig.copy()

    df_purchases = df_purchases_orig.copy() # Work on a copy for local modifications
    df_sales = df_sales_orig.copy()
    logging.info("Starting FIFO processing with Supabase integration...")
    cogs_attribution_records = []

    for sale_idx, sale_transaction in df_sales.iterrows():
        current_sku = sale_transaction["SKU"]
        quantity_to_attribute = sale_transaction["Quantity_Sold"]
        sale_date = sale_transaction["Sale_Date"]
        sales_order_id = sale_transaction.get("Sales_Order_ID", f"SALE_{sale_idx}")

        logging.info(f"Processing sale: SKU {current_sku}, Qty {quantity_to_attribute}, Date {sale_date}, SO_ID: {sales_order_id}")
        if quantity_to_attribute <= 0: continue

        lot_mask = (df_purchases["SKU"] == current_sku) & (df_purchases["Remaining_Unit_Qty"] > 0)
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
            
            # Update local DataFrame
            new_remaining_qty_local = lot_remaining_qty_local - units_from_this_lot
            df_purchases.loc[lot_idx, "Remaining_Unit_Qty"] = new_remaining_qty_local
            quantity_to_attribute -= units_from_this_lot

            # Update Supabase
            try:
                logging.info(f"Updating Supabase: Lot_ID {lot_id_db}, SKU {current_sku}, New Remaining_Unit_Qty: {new_remaining_qty_local}")
                update_data, update_error = supabase.table(SUPABASE_PURCHASES_TABLE_NAME)\
                                     .update({"remaining_unit_qty": new_remaining_qty_local})\
                                     .eq("lot_id", lot_id_db)\
                                     .execute()
                if hasattr(update_data, 'error') and update_data.error:
                    logging.error(f"Error updating Supabase for Lot_ID {lot_id_db}: {update_data.error}")
                elif isinstance(update_data, (list, tuple)) and len(update_data) == 2 and update_data[0] == 'error' and update_data[1]: # v1.x.x error
                     logging.error(f"Error updating Supabase for Lot_ID {lot_id_db}: {update_data[1]}")
                else:
                    logging.info(f"Supabase update successful for Lot_ID {lot_id_db}.")
            except Exception as e:
                logging.error(f"Exception during Supabase update for Lot_ID {lot_id_db}: {e}")

        if quantity_to_attribute > 0:
            logging.warning(f"Insufficient stock for SKU {current_sku} on {sale_date}. SO_ID: {sales_order_id}. Requested Qty: {original_sale_qty_for_logging}, Unfulfilled Qty: {quantity_to_attribute}")
            cogs_attribution_records.append({
                "Sale_Date": sale_date, "Sales_Order_ID": sales_order_id, "SKU": current_sku,
                "Lot_ID": "UNFULFILLED_PARTIAL", "Attributed_Qty": quantity_to_attribute,
                "Attributed_Unit_Price": 0.0, "Attributed_Freight_Cost_Per_Unit": 0.0,
                "Attributed_Total_Unit_Cost": 0.0, "Attributed_COGS": 0.0,
                "Attributed_COGS_Unit_Only": 0.0, "Attributed_COGS_Freight_Only": 0.0,
                "Status": "Insufficient Stock"
            })

    df_cogs_attribution = pd.DataFrame(cogs_attribution_records)
    if not df_cogs_attribution.empty:
      df_cogs_attribution["Month"] = df_cogs_attribution["Sale_Date"].dt.strftime("%Y-%m")
    else: # Handle empty df_cogs_attribution
      df_cogs_attribution["Month"] = pd.Series(dtype='str')

    # COGS Summary Calculation (remains the same)
    df_cogs_summary = pd.DataFrame()
    if not df_cogs_attribution[df_cogs_attribution["Status"].isin(["Fulfilled", "Fulfilled_Partial"])].empty:
        summary_grouped = df_cogs_attribution[df_cogs_attribution["Status"].isin(["Fulfilled", "Fulfilled_Partial"])].groupby(["Month", "SKU"])
        df_cogs_summary = summary_grouped.agg(
            Total_Quantity_Sold=("Attributed_Qty", "sum"),
            Total_COGS_Blended=("Attributed_COGS", "sum"),
            Total_COGS_Unit_Only=("Attributed_COGS_Unit_Only", "sum"),
            Total_COGS_Freight_Only=("Attributed_COGS_Freight_Only", "sum")
        ).reset_index()

    logging.info("FIFO processing completed.")
    # The df_purchases returned here is the locally modified one. 
    # The true source of updated inventory is now Supabase.
    return df_cogs_attribution, df_cogs_summary, df_purchases 

# --- Main Execution Block (Modified) ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FIFO Inventory COGS Calculator with Supabase Integration")
    parser.add_argument("--sales_file", required=True, help="Path to the monthly sales data file (CSV or Excel).")
    parser.add_argument("--output_dir", default="./fifo_outputs", help="Directory to save output CSV files.")
    parser.add_argument("--log_file", default="./fifo_processing_log.txt", help="Path to the log file.")
    args = parser.parse_args()

    # Setup logging
    if os.path.exists(args.log_file):
        open(args.log_file, 'w').close() # Clear log file on new run
    logging.basicConfig(filename=args.log_file, 
                        level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logging.getLogger().addHandler(console_handler)

    logging.info("Script started.")
    logging.info(f"Sales file: {args.sales_file}")
    logging.info(f"Output directory: {args.output_dir}")
    logging.info(f"Log file: {args.log_file}")

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        logging.info(f"Created output directory: {args.output_dir}")

    # Initialize Supabase client
    supabase_client = get_supabase_client()
    if not supabase_client:
        logging.error("Failed to initialize Supabase client. Exiting.")
        exit(1)

    # Load data
    df_purchases_supabase = load_and_validate_purchases_from_supabase(supabase_client)
    df_sales_user = load_and_validate_sales_user_format(args.sales_file)

    if df_purchases_supabase is None or df_sales_user is None:
        logging.error("Failed to load or validate data. Exiting.")
        exit(1)
    
    if df_purchases_supabase.empty and not df_sales_user.empty:
        logging.warning("Purchase data from Supabase is empty, but sales data exists. COGS will likely be zero or reflect unfulfilled sales.")
    elif df_purchases_supabase.empty and df_sales_user.empty:
        logging.info("Both purchase data from Supabase and sales data are empty. No processing to perform.")
        # Create empty output files for consistency if needed
        pd.DataFrame().to_csv(os.path.join(args.output_dir, "cogs_attribution_supabase.csv"), index=False, float_format='%.2f')
        pd.DataFrame().to_csv(os.path.join(args.output_dir, "cogs_summary_supabase.csv"), index=False, float_format='%.2f')
        pd.DataFrame().to_csv(os.path.join(args.output_dir, "updated_inventory_snapshot_supabase.csv"), index=False, float_format='%.2f')
        logging.info("Empty output files created.")
        exit(0)

    # Process FIFO
    df_cogs_attribution, df_cogs_summary, df_updated_inventory_snapshot = process_fifo(supabase_client, df_purchases_supabase, df_sales_user)

    if df_cogs_attribution is None or df_cogs_summary is None or df_updated_inventory_snapshot is None:
        logging.error("FIFO processing failed. Exiting.")
        exit(1)

    # Save outputs
    cogs_attribution_path = os.path.join(args.output_dir, "cogs_attribution_supabase.csv")
    cogs_summary_path = os.path.join(args.output_dir, "cogs_summary_supabase.csv")
    # This updated inventory is a snapshot from the script's perspective. Supabase is the source of truth.
    updated_inventory_path = os.path.join(args.output_dir, "updated_inventory_snapshot_supabase.csv") 

    try:
        df_cogs_attribution.to_csv(cogs_attribution_path, index=False, float_format='%.2f')
        logging.info(f"COGS attribution data saved to: {cogs_attribution_path}")
        df_cogs_summary.to_csv(cogs_summary_path, index=False, float_format='%.2f')
        logging.info(f"COGS summary data saved to: {cogs_summary_path}")
        df_updated_inventory_snapshot.to_csv(updated_inventory_path, index=False, float_format='%.2f')
        logging.info(f"Updated inventory snapshot saved to: {updated_inventory_path}")
    except Exception as e:
        logging.error(f"Error saving output files: {e}")

    logging.info("Script finished.")

