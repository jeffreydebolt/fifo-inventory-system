"""
Supabase database service for FirstLot FIFO system.
Connects to existing multi-tenant production database.
"""
import os
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from supabase import create_client, Client
import uuid
import logging

logger = logging.getLogger(__name__)

# Global file cache (temporary solution - use Redis/database in production)
_global_file_cache = {}

class SupabaseService:
    """Service for interacting with Supabase database"""
    
    def __init__(self):
        self.supabase: Client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Supabase client"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        
        if not url or not key:
            logger.warning("Supabase credentials not found, using demo mode")
            return
            
        try:
            # Simple Supabase client initialization
            self.supabase = create_client(url, key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self.supabase = None
    
    def save_uploaded_file(self, tenant_id: str, filename: str, file_type: str, file_size: int, df: pd.DataFrame) -> str:
        """Save uploaded file metadata to database"""
        if not self.supabase:
            file_id = f"demo_file_{uuid.uuid4()}"
            # Still store in global cache for demo mode
            self._store_file_data(file_id, df)
            logger.warning(f"Using demo mode for file {filename}")
            return file_id
            
        try:
            file_id = str(uuid.uuid4())
            
            result = self.supabase.table('uploaded_files').insert({
                'file_id': file_id,
                'tenant_id': tenant_id,
                'filename': filename,
                'file_type': file_type,
                'file_size': file_size,
                'uploaded_at': datetime.now().isoformat(),
                'processed': False
            }).execute()
            
            # Also store the dataframe data temporarily (in production would use file storage)
            self._store_file_data(file_id, df)
            
            logger.info(f"✅ Saved uploaded file {filename} for tenant {tenant_id} to database")
            return file_id
            
        except Exception as e:
            logger.error(f"❌ Database save failed, using demo mode for {filename}: {type(e).__name__}: {e}")
            # Fallback to demo mode
            file_id = f"demo_file_{uuid.uuid4()}"
            self._store_file_data(file_id, df)
            return file_id
    
    def _store_file_data(self, file_id: str, df: pd.DataFrame):
        """Temporarily store file data (would use proper file storage in production)"""
        global _global_file_cache
        _global_file_cache[file_id] = df
    
    def get_current_inventory(self, tenant_id: str) -> pd.DataFrame:
        """Get current inventory snapshot for tenant"""
        if not self.supabase:
            # Return demo inventory
            return pd.DataFrame({
                'lot_id': ['LOT001', 'LOT002'],
                'sku': ['ABC-123', 'DEF-456'],
                'remaining_quantity': [100, 75],
                'unit_price': [10.0, 12.0],
                'freight_cost_per_unit': [1.0, 1.5],
                'received_date': ['2024-01-01', '2024-01-15']
            })
        
        try:
            # Get current inventory snapshot
            result = self.supabase.table('inventory_snapshots').select(
                'lot_id, sku, remaining_quantity, unit_price, freight_cost_per_unit, received_date'
            ).eq('tenant_id', tenant_id).eq('is_current', True).execute()
            
            if result.data:
                return pd.DataFrame(result.data)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Failed to get current inventory: {e}")
            return pd.DataFrame()
    
    def process_fifo_with_database(self, tenant_id: str, lots_file_id: str, sales_file_id: str) -> Dict:
        """Process FIFO calculation using database inventory"""
        run_id = str(uuid.uuid4())
        
        try:
            # Try to create run record in database
            if self.supabase:
                try:
                    self.supabase.table('cogs_runs').insert({
                        'run_id': run_id,
                        'tenant_id': tenant_id,
                        'status': 'running',
                        'started_at': datetime.now().isoformat()
                    }).execute()
                    logger.info(f"✅ Created run record {run_id} in database")
                except Exception as db_error:
                    logger.error(f"❌ Failed to create run record in database: {type(db_error).__name__}: {db_error}")
                    logger.info(f"Continuing with demo mode for run {run_id}")
            else:
                logger.info(f"Demo mode: Creating run {run_id} for tenant {tenant_id}")
            
            # Get current inventory from database
            current_inventory = self.get_current_inventory(tenant_id)
            
            # Get uploaded sales data
            global _global_file_cache
            sales_df = _global_file_cache.get(sales_file_id, pd.DataFrame())
            logger.info(f"Retrieved sales data: {len(sales_df)} rows for file_id {sales_file_id}")
            
            # Add new lots if provided
            if lots_file_id and lots_file_id in _global_file_cache:
                new_lots = _global_file_cache.get(lots_file_id, pd.DataFrame())
                logger.info(f"Retrieved lots data: {len(new_lots)} rows for file_id {lots_file_id}")
                # Combine with existing inventory
                if not current_inventory.empty and not new_lots.empty:
                    current_inventory = pd.concat([current_inventory, new_lots], ignore_index=True)
                elif not new_lots.empty:
                    current_inventory = new_lots
            
            # Process FIFO calculation
            logger.info(f"Starting FIFO calculation with {len(current_inventory)} inventory rows and {len(sales_df)} sales rows")
            result = self._calculate_fifo(tenant_id, run_id, current_inventory, sales_df)
            
            # Try to update run status in database
            if self.supabase:
                try:
                    self.supabase.table('cogs_runs').update({
                        'status': 'completed',
                        'completed_at': datetime.now().isoformat(),
                        'total_sales_processed': result.get('total_sales_processed', 0),
                        'total_cogs_calculated': result.get('total_cogs_calculated', 0)
                    }).eq('run_id', run_id).execute()
                    logger.info(f"✅ Updated run status to completed in database")
                except Exception as db_error:
                    logger.error(f"❌ Failed to update run status: {type(db_error).__name__}: {db_error}")
            
            result['run_id'] = run_id
            return result
            
        except Exception as e:
            logger.error(f"❌ FIFO processing failed: {type(e).__name__}: {e}", exc_info=True)
            error_msg = str(e) if str(e) else f"Unknown error: {type(e).__name__}"
            
            # Try to update run status to failed
            if self.supabase:
                try:
                    self.supabase.table('cogs_runs').update({
                        'status': 'failed',
                        'completed_at': datetime.now().isoformat(),
                        'error_message': error_msg
                    }).eq('run_id', run_id).execute()
                except Exception as db_error:
                    logger.error(f"❌ Failed to update run status to failed: {db_error}")
            
            return {
                "success": False,
                "error": error_msg,
                "total_sales_processed": 0,
                "total_cogs_calculated": 0,
                "run_id": run_id
            }
    
    def _calculate_fifo(self, tenant_id: str, run_id: str, inventory_df: pd.DataFrame, sales_df: pd.DataFrame) -> Dict:
        """Calculate FIFO with proper inventory tracking"""
        logger.info(f"_calculate_fifo called with inventory_df: {len(inventory_df)} rows, sales_df: {len(sales_df)} rows")
        
        if inventory_df.empty:
            logger.info("Inventory DataFrame is empty")
        else:
            logger.info(f"Inventory SKUs: {inventory_df['sku'].tolist() if 'sku' in inventory_df.columns else 'No SKU column'}")
            
        if sales_df.empty:
            logger.info("Sales DataFrame is empty") 
        else:
            logger.info(f"Sales columns: {sales_df.columns.tolist()}")
            logger.info(f"Sales data: {sales_df.head()}")
        
        if inventory_df.empty or sales_df.empty:
            return {
                "success": True,
                "total_sales_processed": 0,
                "total_cogs_calculated": 0,
                "processed_skus": 0
            }
        
        total_cogs = 0
        processed_sales = 0
        
        # Create working inventory copy
        working_inventory = inventory_df.copy()
        working_inventory['total_cost_per_unit'] = working_inventory['unit_price'] + working_inventory['freight_cost_per_unit']
        
        # Sort inventory by date (FIFO) - handle multiple date formats
        working_inventory['received_date'] = pd.to_datetime(working_inventory['received_date'], format='mixed')
        working_inventory = working_inventory.sort_values('received_date')
        
        # Process each sale
        for _, sale_row in sales_df.iterrows():
            sku = str(sale_row.get('sku', sale_row.get('SKU', ''))).strip()
            if not sku:
                continue
                
            quantity_raw = sale_row.get('units moved', sale_row.get('Quantity_Sold', sale_row.get('quantity', 0)))
            # Handle NaN values and convert to int
            try:
                quantity_sold = int(float(quantity_raw))
                if quantity_sold <= 0:
                    continue
            except (ValueError, TypeError):
                continue  # Skip invalid quantity values
            
            # Find available lots for this SKU
            available_lots = working_inventory[
                (working_inventory['sku'] == sku) & 
                (working_inventory['remaining_quantity'] > 0)
            ].copy()
            
            if available_lots.empty:
                continue
            
            remaining_to_sell = quantity_sold
            sale_cogs = 0
            
            # FIFO consumption - oldest lots first
            for idx, lot in available_lots.iterrows():
                if remaining_to_sell <= 0:
                    break
                    
                available_qty = lot['remaining_quantity']
                consumed_qty = min(remaining_to_sell, available_qty)
                
                lot_cogs = consumed_qty * lot['total_cost_per_unit']
                sale_cogs += lot_cogs
                
                # Update remaining quantity
                working_inventory.loc[idx, 'remaining_quantity'] -= consumed_qty
                remaining_to_sell -= consumed_qty
                
                # Save attribution to database if possible
                if self.supabase:
                    self._save_cogs_attribution(tenant_id, run_id, sale_row, sku, consumed_qty, lot_cogs)
            
            total_cogs += sale_cogs
            processed_sales += 1
        
        # Update inventory snapshots in database
        if self.supabase:
            self._update_inventory_snapshot(tenant_id, run_id, working_inventory)
        
        return {
            "success": True,
            "total_sales_processed": processed_sales,
            "total_cogs_calculated": round(total_cogs, 2),
            "processed_skus": len(working_inventory['sku'].unique())
        }
    
    def _save_cogs_attribution(self, tenant_id: str, run_id: str, sale_row: pd.Series, sku: str, quantity: int, cogs: float):
        """Save COGS attribution to database"""
        try:
            attribution_id = str(uuid.uuid4())
            
            self.supabase.table('cogs_attribution').insert({
                'attribution_id': attribution_id,
                'tenant_id': tenant_id,
                'run_id': run_id,
                'sale_id': f"SALE_{uuid.uuid4()}",
                'sku': sku,
                'sale_date': datetime.now().isoformat(),
                'quantity_sold': quantity,
                'total_cogs': cogs,
                'average_unit_cost': cogs / quantity if quantity > 0 else 0,
                'is_valid': True
            }).execute()
            
        except Exception as e:
            logger.error(f"❌ Failed to save COGS attribution: {type(e).__name__}: {e}")
    
    def _update_inventory_snapshot(self, tenant_id: str, run_id: str, inventory_df: pd.DataFrame):
        """Update inventory snapshot in database"""
        try:
            # Mark previous snapshots as not current
            self.supabase.table('inventory_snapshots').update({
                'is_current': False
            }).eq('tenant_id', tenant_id).execute()
            
            # Insert new current snapshot
            for _, lot in inventory_df.iterrows():
                self.supabase.table('inventory_snapshots').insert({
                    'snapshot_id': str(uuid.uuid4()),
                    'tenant_id': tenant_id,
                    'run_id': run_id,
                    'lot_id': lot['lot_id'],
                    'sku': lot['sku'],
                    'remaining_quantity': lot['remaining_quantity'],
                    'original_quantity': lot.get('original_quantity', lot['remaining_quantity']),
                    'unit_price': lot['unit_price'],
                    'freight_cost_per_unit': lot['freight_cost_per_unit'],
                    'received_date': lot['received_date'].isoformat() if pd.notnull(lot['received_date']) else None,
                    'is_current': True
                }).execute()
                
        except Exception as e:
            logger.error(f"❌ Failed to update inventory snapshot: {type(e).__name__}: {e}")


# Global instance
supabase_service = SupabaseService()