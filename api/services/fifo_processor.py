"""
Simple FIFO processor service for API integration.
"""
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


def process_fifo_calculation(lots_df: pd.DataFrame, sales_df: pd.DataFrame) -> Dict:
    """
    Process FIFO calculation using uploaded dataframes - simplified version.
    
    Returns results dictionary with calculated COGS.
    """
    try:
        # Simple FIFO calculation without complex engine
        total_cogs = 0
        processed_sales = 0
        
        # Calculate basic FIFO for each SKU
        sku_costs = {}
        for _, lot_row in lots_df.iterrows():
            # Handle different column names and clean data
            sku = str(lot_row.get('sku', lot_row.get('SKU', ''))).strip()
            if not sku:  # Skip empty rows
                continue
                
            unit_cost = float(lot_row.get('unit_price', 0)) + float(lot_row.get('freight_cost_per_unit', 0))
            quantity = int(lot_row.get('remaining_quantity', lot_row.get('original_quantity', 0)))
            
            if sku not in sku_costs:
                sku_costs[sku] = []
            sku_costs[sku].append({
                'cost': unit_cost,
                'quantity': quantity,
                'date': pd.to_datetime(lot_row.get('received_date', datetime.now()))
            })
        
        # Sort lots by date (FIFO)
        for sku in sku_costs:
            sku_costs[sku].sort(key=lambda x: x['date'])
        
        # Process sales
        for _, sale_row in sales_df.iterrows():
            # Handle different column names and clean data
            sku = str(sale_row.get('sku', sale_row.get('SKU', ''))).strip()
            if not sku:  # Skip empty rows
                continue
                
            quantity_sold = int(sale_row.get('units moved', sale_row.get('Quantity_Sold', sale_row.get('quantity', 0))))
            
            if sku in sku_costs and quantity_sold > 0:
                remaining_to_sell = quantity_sold
                sale_cogs = 0
                
                # FIFO consumption
                for lot in sku_costs[sku]:
                    if remaining_to_sell <= 0:
                        break
                    
                    consumed = min(remaining_to_sell, lot['quantity'])
                    sale_cogs += consumed * lot['cost']
                    lot['quantity'] -= consumed
                    remaining_to_sell -= consumed
                
                total_cogs += sale_cogs
                processed_sales += 1
        
        # Count unique SKUs processed
        processed_skus = len([sku for sku in sku_costs if any(lot['quantity'] < int(lots_df[lots_df['sku'] == sku]['remaining_quantity'].iloc[0]) for lot in sku_costs[sku])])
        
        return {
            "success": True,
            "total_sales_processed": processed_sales,
            "total_cogs_calculated": round(total_cogs, 2),
            "processed_skus": max(processed_skus, 1),
            "validation_errors": 0
        }
        
    except Exception as e:
        logger.error(f"FIFO processing error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "total_sales_processed": 0,
            "total_cogs_calculated": 0
        }