#!/usr/bin/env python3
"""
SAFE SUPABASE DATABASE ADAPTER
Provides safe database operations with comprehensive error handling,
connection management, and protection for production data.
"""

import os
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import pandas as pd

# Supabase imports with error handling
try:
    from supabase import create_client, Client
except ImportError as e:
    print(f"CRITICAL: Supabase client not available: {e}")
    print("Install with: pip install supabase")
    raise

@dataclass
class DatabaseSnapshot:
    """Represents a point-in-time database state for rollback purposes"""
    snapshot_id: str
    timestamp: datetime
    tables_affected: List[str]
    record_counts: Dict[str, int]
    backup_data: Dict[str, List[Dict]]

class SafeSupabaseAdapter:
    """
    Safe Supabase database adapter with comprehensive error handling,
    connection management, and production data protection.
    """
    
    def __init__(self, 
                 url: str = None, 
                 key: str = None,
                 tenant_id: str = None,
                 dry_run: bool = False):
        """
        Initialize safe Supabase adapter.
        
        Args:
            url: Supabase URL (from env if not provided)
            key: Supabase key (from env if not provided)  
            tenant_id: Tenant ID for multi-tenant isolation
            dry_run: If True, no actual database changes are made
        """
        self.tenant_id = tenant_id or "default"
        self.dry_run = dry_run
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize connection
        self.client = None
        self._initialize_connection(url, key)
        
        # Track operations for rollback
        self.operation_log = []
        self.snapshots = []
        
        # Safety limits
        self.max_batch_size = 1000
        self.max_update_count = 10000
        self.require_confirmation = os.getenv('REQUIRE_CONFIRMATION', 'true').lower() == 'true'
        
    def _initialize_connection(self, url: str = None, key: str = None):
        """Initialize Supabase connection with error handling"""
        try:
            # Use provided credentials or environment variables
            supabase_url = url or os.getenv('SUPABASE_URL')
            supabase_key = key or os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                raise ValueError("Supabase URL and KEY must be provided via parameters or environment variables")
            
            # Test environment detection
            is_test_env = os.getenv('TEST_MODE', 'false').lower() == 'true'
            
            if not is_test_env and 'test' not in supabase_url.lower():
                self.logger.warning("🔴 PRODUCTION DATABASE DETECTED!")
                self.logger.warning("Ensure you have proper backups before making changes")
                
                if self.require_confirmation:
                    confirmation = input("Type 'CONFIRM' to proceed with production database: ")
                    if confirmation != 'CONFIRM':
                        raise ValueError("Production database access cancelled by user")
            
            # Create client
            self.client = create_client(supabase_url, supabase_key)
            
            # Test connection
            self._test_connection()
            
            self.logger.info(f"✅ Connected to Supabase (tenant: {self.tenant_id}, dry_run: {self.dry_run})")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to Supabase: {e}")
            raise
    
    def _test_connection(self):
        """Test database connection"""
        try:
            # Test with a simple query that should work on any setup
            result = self.client.table('purchase_lots').select('lot_id').limit(1).execute()
            
            if hasattr(result, 'data'):
                self.logger.info("✅ Database connection test successful")
            else:
                raise Exception("Unexpected response format")
                
        except Exception as e:
            raise Exception(f"Database connection test failed: {e}")
    
    def create_snapshot(self, tables: List[str], description: str = None) -> str:
        """
        Create a snapshot of specified tables before making changes.
        Essential for rollback capability.
        """
        snapshot_id = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.snapshots)}"
        
        try:
            self.logger.info(f"📸 Creating snapshot {snapshot_id}...")
            
            backup_data = {}
            record_counts = {}
            
            for table in tables:
                self.logger.info(f"  Backing up table: {table}")
                
                # Get current data
                result = self.client.table(table).select('*').execute()
                
                if hasattr(result, 'data') and result.data:
                    backup_data[table] = result.data
                    record_counts[table] = len(result.data)
                    self.logger.info(f"    ✅ {record_counts[table]} records backed up")
                else:
                    backup_data[table] = []
                    record_counts[table] = 0
                    self.logger.info(f"    ⚠️ Table {table} is empty or not found")
            
            snapshot = DatabaseSnapshot(
                snapshot_id=snapshot_id,
                timestamp=datetime.now(),
                tables_affected=tables,
                record_counts=record_counts,
                backup_data=backup_data
            )
            
            self.snapshots.append(snapshot)
            
            # Save snapshot to file for persistence
            snapshot_file = f"snapshots/snapshot_{snapshot_id}.json"
            os.makedirs("snapshots", exist_ok=True)
            
            with open(snapshot_file, 'w') as f:
                json.dump({
                    'snapshot_id': snapshot_id,
                    'timestamp': snapshot.timestamp.isoformat(),
                    'tables_affected': snapshot.tables_affected,
                    'record_counts': snapshot.record_counts,
                    'backup_data': snapshot.backup_data,
                    'description': description
                }, f, indent=2, default=str)
            
            self.logger.info(f"✅ Snapshot {snapshot_id} created ({sum(record_counts.values())} total records)")
            return snapshot_id
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create snapshot: {e}")
            raise
    
    def get_purchase_lots_safe(self, 
                              sku_filter: List[str] = None,
                              active_only: bool = True) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Safely retrieve purchase lots with comprehensive error handling.
        
        Returns:
            (DataFrame, metadata) where metadata contains query info and warnings
        """
        try:
            self.logger.info("📦 Fetching purchase lots...")
            
            # Build query
            query = self.client.table('purchase_lots').select('*')
            
            # Apply filters
            if active_only:
                query = query.gt('remaining_unit_qty', 0)
            
            if sku_filter:
                query = query.in_('sku', sku_filter)
            
            # Execute query
            result = query.execute()
            
            if not hasattr(result, 'data'):
                raise Exception(f"Unexpected response format: {result}")
            
            data = result.data or []
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Create metadata
            metadata = {
                'query_timestamp': datetime.now().isoformat(),
                'total_records': len(data),
                'filters_applied': {
                    'active_only': active_only,
                    'sku_filter': sku_filter
                },
                'warnings': []
            }
            
            if df.empty:
                metadata['warnings'].append("No purchase lots found with current filters")
                self.logger.warning("⚠️ No purchase lots found")
            else:
                # Data quality checks
                if 'remaining_unit_qty' in df.columns:
                    negative_qty = (df['remaining_unit_qty'] < 0).sum()
                    if negative_qty > 0:
                        metadata['warnings'].append(f"{negative_qty} lots have negative remaining quantities")
                
                if 'remaining_unit_qty' in df.columns and 'original_unit_qty' in df.columns:
                    impossible_qty = (df['remaining_unit_qty'] > df['original_unit_qty']).sum()
                    if impossible_qty > 0:
                        metadata['warnings'].append(f"{impossible_qty} lots have remaining > original quantities")
                
                unique_skus = df['sku'].nunique() if 'sku' in df.columns else 0
                self.logger.info(f"✅ Retrieved {len(df)} lots for {unique_skus} SKUs")
            
            return df, metadata
            
        except Exception as e:
            self.logger.error(f"❌ Failed to fetch purchase lots: {e}")
            raise
    
    def update_inventory_safe(self, 
                            updates: List[Dict[str, Any]], 
                            create_snapshot: bool = True) -> Dict[str, Any]:
        """
        Safely update inventory with comprehensive validation and rollback support.
        
        Args:
            updates: List of dicts with 'lot_id' and 'remaining_unit_qty'
            create_snapshot: Whether to create snapshot before changes
            
        Returns:
            Results dictionary with success/failure details
        """
        if self.dry_run:
            self.logger.info("🧪 DRY RUN: No actual database changes will be made")
            return self._simulate_inventory_update(updates)
        
        if not updates:
            return {'success': True, 'updated_count': 0, 'message': 'No updates provided'}
        
        # Safety check - limit update size
        if len(updates) > self.max_update_count:
            raise ValueError(f"Update batch too large: {len(updates)} > {self.max_update_count}")
        
        snapshot_id = None
        try:
            # Create snapshot if requested
            if create_snapshot:
                snapshot_id = self.create_snapshot(['purchase_lots'], f"Before inventory update of {len(updates)} lots")
            
            self.logger.info(f"🔄 Updating {len(updates)} inventory records...")
            
            # Validate updates before applying
            validation_result = self._validate_inventory_updates(updates)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': 'Validation failed',
                    'validation_errors': validation_result['errors'],
                    'snapshot_id': snapshot_id
                }
            
            # Apply updates in batches
            batch_size = min(self.max_batch_size, 100)  # Conservative batch size
            updated_count = 0
            failed_updates = []
            
            for i in range(0, len(updates), batch_size):
                batch = updates[i:i + batch_size]
                
                try:
                    batch_result = self._update_inventory_batch(batch)
                    updated_count += batch_result['updated_count']
                    failed_updates.extend(batch_result.get('failed_updates', []))
                    
                    self.logger.info(f"  Batch {i//batch_size + 1}: {batch_result['updated_count']}/{len(batch)} updated")
                    
                except Exception as e:
                    self.logger.error(f"❌ Batch {i//batch_size + 1} failed: {e}")
                    failed_updates.extend([{**update, 'error': str(e)} for update in batch])
            
            # Log operation
            operation = {
                'timestamp': datetime.now().isoformat(),
                'operation': 'update_inventory',
                'snapshot_id': snapshot_id,
                'updates_attempted': len(updates),
                'updates_successful': updated_count,
                'updates_failed': len(failed_updates)
            }
            self.operation_log.append(operation)
            
            result = {
                'success': updated_count > 0,
                'updated_count': updated_count,
                'failed_count': len(failed_updates),
                'failed_updates': failed_updates,
                'snapshot_id': snapshot_id,
                'operation_id': len(self.operation_log) - 1
            }
            
            if updated_count > 0:
                self.logger.info(f"✅ Successfully updated {updated_count}/{len(updates)} inventory records")
            
            if failed_updates:
                self.logger.warning(f"⚠️ {len(failed_updates)} updates failed")
                
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Inventory update failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'snapshot_id': snapshot_id,
                'updated_count': 0
            }
    
    def _validate_inventory_updates(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate inventory updates before applying"""
        errors = []
        
        for i, update in enumerate(updates):
            # Check required fields
            if 'lot_id' not in update:
                errors.append(f"Update {i}: Missing lot_id")
                continue
                
            if 'remaining_unit_qty' not in update:
                errors.append(f"Update {i}: Missing remaining_unit_qty")
                continue
            
            # Check data types
            try:
                remaining_qty = float(update['remaining_unit_qty'])
                if remaining_qty < 0:
                    errors.append(f"Update {i}: Negative remaining quantity: {remaining_qty}")
            except (ValueError, TypeError):
                errors.append(f"Update {i}: Invalid remaining_unit_qty: {update['remaining_unit_qty']}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _update_inventory_batch(self, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update a batch of inventory records"""
        updated_count = 0
        failed_updates = []
        
        for update in batch:
            try:
                lot_id = update['lot_id']
                remaining_qty = update['remaining_unit_qty']
                
                # Perform update
                result = self.client.table('purchase_lots').update({
                    'remaining_unit_qty': remaining_qty
                }).eq('lot_id', lot_id).execute()
                
                if hasattr(result, 'data') and result.data:
                    updated_count += 1
                else:
                    failed_updates.append({**update, 'error': 'No rows updated'})
                    
            except Exception as e:
                failed_updates.append({**update, 'error': str(e)})
        
        return {
            'updated_count': updated_count,
            'failed_updates': failed_updates
        }
    
    def _simulate_inventory_update(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simulate inventory update for dry run"""
        self.logger.info(f"🧪 SIMULATION: Would update {len(updates)} inventory records")
        
        for i, update in enumerate(updates[:5]):  # Show first 5
            self.logger.info(f"  Would set lot {update.get('lot_id')} remaining_qty = {update.get('remaining_unit_qty')}")
        
        if len(updates) > 5:
            self.logger.info(f"  ... and {len(updates) - 5} more updates")
        
        return {
            'success': True,
            'updated_count': len(updates),
            'dry_run': True,
            'message': 'Simulation completed successfully'
        }
    
    def rollback_to_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        """
        Rollback database to a previous snapshot state.
        CRITICAL OPERATION - use with extreme caution.
        """
        if self.dry_run:
            self.logger.info("🧪 DRY RUN: Would rollback to snapshot")
            return {'success': True, 'dry_run': True}
        
        try:
            # Find snapshot
            snapshot = None
            for snap in self.snapshots:
                if snap.snapshot_id == snapshot_id:
                    snapshot = snap
                    break
            
            if not snapshot:
                # Try loading from file
                snapshot_file = f"snapshots/snapshot_{snapshot_id}.json"
                if os.path.exists(snapshot_file):
                    with open(snapshot_file, 'r') as f:
                        snapshot_data = json.load(f)
                    
                    snapshot = DatabaseSnapshot(
                        snapshot_id=snapshot_data['snapshot_id'],
                        timestamp=datetime.fromisoformat(snapshot_data['timestamp']),
                        tables_affected=snapshot_data['tables_affected'],
                        record_counts=snapshot_data['record_counts'],
                        backup_data=snapshot_data['backup_data']
                    )
                else:
                    raise ValueError(f"Snapshot {snapshot_id} not found")
            
            self.logger.warning(f"🚨 ROLLING BACK TO SNAPSHOT: {snapshot_id}")
            self.logger.warning(f"This will restore data from {snapshot.timestamp}")
            
            if self.require_confirmation:
                confirmation = input("Type 'ROLLBACK' to confirm this dangerous operation: ")
                if confirmation != 'ROLLBACK':
                    return {'success': False, 'message': 'Rollback cancelled by user'}
            
            # Perform rollback
            restored_counts = {}
            
            for table in snapshot.tables_affected:
                self.logger.info(f"  Rolling back table: {table}")
                
                # Delete current data (dangerous!)
                delete_result = self.client.table(table).delete().neq('lot_id', '').execute()
                
                # Restore snapshot data
                if snapshot.backup_data.get(table):
                    # Insert in batches
                    batch_size = 100
                    data = snapshot.backup_data[table]
                    
                    for i in range(0, len(data), batch_size):
                        batch = data[i:i + batch_size]
                        insert_result = self.client.table(table).insert(batch).execute()
                    
                    restored_counts[table] = len(data)
                else:
                    restored_counts[table] = 0
                
                self.logger.info(f"    ✅ Restored {restored_counts[table]} records")
            
            # Log rollback operation
            operation = {
                'timestamp': datetime.now().isoformat(),
                'operation': 'rollback',
                'snapshot_id': snapshot_id,
                'tables_restored': list(restored_counts.keys()),
                'records_restored': sum(restored_counts.values())
            }
            self.operation_log.append(operation)
            
            self.logger.info(f"✅ Rollback completed: {sum(restored_counts.values())} records restored")
            
            return {
                'success': True,
                'snapshot_id': snapshot_id,
                'tables_restored': restored_counts,
                'total_records_restored': sum(restored_counts.values())
            }
            
        except Exception as e:
            self.logger.error(f"❌ Rollback failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Rollback failed - database may be in inconsistent state!'
            }
    
    def get_operation_log(self) -> List[Dict[str, Any]]:
        """Get log of all database operations"""
        return self.operation_log.copy()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Check database health and connection status"""
        try:
            # Test basic connectivity
            start_time = datetime.now()
            result = self.client.table('purchase_lots').select('lot_id').limit(1).execute()
            response_time = (datetime.now() - start_time).total_seconds()
            
            # Get table counts
            lots_count = len(self.client.table('purchase_lots').select('lot_id').execute().data or [])
            
            return {
                'status': 'healthy',
                'connection': 'active',
                'response_time_seconds': response_time,
                'purchase_lots_count': lots_count,
                'snapshots_available': len(self.snapshots),
                'operations_logged': len(self.operation_log),
                'dry_run_mode': self.dry_run,
                'tenant_id': self.tenant_id
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'connection': 'failed'
            }

# Usage examples and integration helpers
def create_safe_adapter(tenant_id: str = None, dry_run: bool = False) -> SafeSupabaseAdapter:
    """Create a safe Supabase adapter with recommended settings"""
    return SafeSupabaseAdapter(
        tenant_id=tenant_id or "production-client",
        dry_run=dry_run
    )

def demo_safe_operations():
    """Demonstrate safe database operations"""
    
    # Create adapter in dry run mode for safety
    adapter = SafeSupabaseAdapter(tenant_id="demo", dry_run=True)
    
    # Test health
    health = adapter.get_health_status()
    print(f"Database Health: {health['status']}")
    
    # Get purchase lots
    try:
        lots_df, metadata = adapter.get_purchase_lots_safe(active_only=True)
        print(f"Retrieved {metadata['total_records']} active lots")
        
        if metadata['warnings']:
            print("Warnings:")
            for warning in metadata['warnings']:
                print(f"  ⚠️ {warning}")
        
    except Exception as e:
        print(f"Failed to retrieve lots: {e}")
    
    # Demo snapshot creation
    snapshot_id = adapter.create_snapshot(['purchase_lots'], "Demo snapshot")
    print(f"Created snapshot: {snapshot_id}")
    
    # Demo inventory update
    sample_updates = [
        {'lot_id': 'LOT001', 'remaining_unit_qty': 100},
        {'lot_id': 'LOT002', 'remaining_unit_qty': 50}
    ]
    
    result = adapter.update_inventory_safe(sample_updates)
    print(f"Update result: {result['success']} ({result.get('message', '')})")

if __name__ == "__main__":
    demo_safe_operations()