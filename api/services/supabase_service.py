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
            self.supabase = create_client(url, key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
    
    def save_uploaded_file(self, tenant_id: str, filename: str, file_type: str, file_size: int, df: pd.DataFrame) -> str:
        """Save uploaded file metadata to database"""
        if not self.supabase:
            return f"demo_file_{uuid.uuid4()}"
            
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
            
            logger.info(f"Saved uploaded file {filename} for tenant {tenant_id}")
            return file_id
            
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {e}")
            return f"demo_file_{uuid.uuid4()}"
    
    def _store_file_data(self, file_id: str, df: pd.DataFrame):
        """Temporarily store file data (would use proper file storage in production)"""
        if not hasattr(self, '_file_cache'):
            self._file_cache = {}
        self._file_cache[file_id] = df
    
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
        try:
            # Create new run record
            run_id = str(uuid.uuid4())
            
            if self.supabase:
                self.supabase.table('cogs_runs').insert({
                    'run_id': run_id,
                    'tenant_id': tenant_id,
                    'status': 'running',
                    'started_at': datetime.now().isoformat()
                }).execute()
            
            # Get current inventory from database
            current_inventory = self.get_current_inventory(tenant_id)
            
            # Get uploaded sales data
            sales_df = getattr(self, '_file_cache', {}).get(sales_file_id, pd.DataFrame())
            
            # Add new lots if provided
            if lots_file_id and lots_file_id in getattr(self, '_file_cache', {}):
                new_lots = getattr(self, '_file_cache', {}).get(lots_file_id, pd.DataFrame())
                # Combine with existing inventory
                if not current_inventory.empty and not new_lots.empty:
                    current_inventory = pd.concat([current_inventory, new_lots], ignore_index=True)
                elif not new_lots.empty:
                    current_inventory = new_lots
            
            # Process FIFO calculation
            result = self._calculate_fifo(tenant_id, run_id, current_inventory, sales_df)
            
            # Update run status
            if self.supabase:
                self.supabase.table('cogs_runs').update({
                    'status': 'completed',
                    'completed_at': datetime.now().isoformat(),
                    'total_sales_processed': result.get('total_sales_processed', 0),
                    'total_cogs_calculated': result.get('total_cogs_calculated', 0)
                }).eq('run_id', run_id).execute()
            
            result['run_id'] = run_id
            return result
            
        except Exception as e:
            logger.error(f"FIFO processing failed: {e}")
            if self.supabase:
                self.supabase.table('cogs_runs').update({
                    'status': 'failed',
                    'completed_at': datetime.now().isoformat(),
                    'error_message': str(e)
                }).eq('run_id', run_id).execute()
            
            return {
                "success": False,
                "error": str(e),
                "total_sales_processed": 0,
                "total_cogs_calculated": 0
            }
    
    def _calculate_fifo(self, tenant_id: str, run_id: str, inventory_df: pd.DataFrame, sales_df: pd.DataFrame) -> Dict:
        """Calculate FIFO with proper inventory tracking"""
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
        
        # Sort inventory by date (FIFO)
        working_inventory['received_date'] = pd.to_datetime(working_inventory['received_date'])
        working_inventory = working_inventory.sort_values('received_date')
        
        # Process each sale
        for _, sale_row in sales_df.iterrows():
            sku = str(sale_row.get('sku', sale_row.get('SKU', ''))).strip()
            if not sku:
                continue
                
            quantity_sold = int(sale_row.get('units moved', sale_row.get('Quantity_Sold', sale_row.get('quantity', 0))))
            if quantity_sold <= 0:
                continue
            
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
            logger.error(f"Failed to save COGS attribution: {e}")
    
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
            logger.error(f"Failed to update inventory snapshot: {e}")


# Global instance
supabase_service = SupabaseService()