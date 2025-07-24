"""
Journaled FIFO calculator that tracks all operations for rollback support.
"""
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from decimal import Decimal
import logging

from core.models import PurchaseLot, Sale, InventorySnapshot
from core.fifo_engine import FIFOEngine
from core.db_models import COGSRun, RunStatus, InventoryMovement, InventorySnapshot as DBInventorySnapshot
from services.tenant_service import TenantService, TenantContext


class JournaledCalculator:
    """FIFO calculator with complete journaling and rollback support"""
    
    def __init__(self, engine: FIFOEngine, db_adapter=None):
        self.engine = engine
        self.db_adapter = db_adapter  # Database adapter for persistence
        self.logger = logging.getLogger(__name__)
    
    def create_and_execute_run(
        self,
        tenant_id: str,
        lots: List[PurchaseLot],
        sales: List[Sale],
        mode: str = "fifo",
        start_month: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create and execute a fully journaled COGS run.
        
        Args:
            tenant_id: Tenant identifier
            lots: Purchase lots for inventory
            sales: Sales transactions to process
            mode: Calculation mode ('fifo' or 'avg')
            start_month: Starting month for calculation (YYYY-MM)
            created_by: User who initiated the run
            
        Returns:
            Dict with run results and metadata
        """
        with TenantContext(tenant_id):
            # Check for concurrent runs
            active_runs = self._get_active_runs(tenant_id)
            if active_runs:
                raise ValueError(f"Tenant {tenant_id} has active run {active_runs[0]}. Wait for completion or rollback.")
            
            # Create run record
            run_id = str(uuid.uuid4())
            run = COGSRun(
                run_id=run_id,
                tenant_id=tenant_id,
                status=RunStatus.PENDING,
                started_at=datetime.now(),
                completed_at=None,
                input_file_id=None,
                error_message=None,
                created_by=created_by,
                rollback_of_run_id=None
            )
            
            try:
                # Save initial run
                self._save_run(run)
                
                # Update status to running
                run.status = RunStatus.RUNNING
                self._update_run(run)
                
                # Execute calculation with journaling
                result = self._execute_with_journaling(run_id, tenant_id, lots, sales, mode)
                
                # Update run with results
                run.status = RunStatus.COMPLETED
                run.completed_at = datetime.now()
                run.total_sales_processed = len(sales)
                run.total_cogs_calculated = result['total_cogs']
                run.validation_errors_count = len(result['validation_errors'])
                
                self._update_run(run)
                
                self.logger.info(f"Run {run_id} completed successfully for tenant {tenant_id}")
                
                return {
                    'run_id': run_id,
                    'status': 'completed',
                    'attributions': result['attributions'],
                    'summaries': result['summaries'],
                    'final_inventory': result['final_inventory'],
                    'validation_errors': result['validation_errors'],
                    'total_cogs': result['total_cogs']
                }
                
            except Exception as e:
                # Mark run as failed
                run.status = RunStatus.FAILED
                run.completed_at = datetime.now()
                run.error_message = str(e)
                self._update_run(run)
                
                self.logger.error(f"Run {run_id} failed for tenant {tenant_id}: {e}")
                raise
    
    def _execute_with_journaling(
        self,
        run_id: str,
        tenant_id: str,
        lots: List[PurchaseLot],
        sales: List[Sale],
        mode: str
    ) -> Dict[str, Any]:
        """Execute calculation with full journaling"""
        
        # Save initial inventory snapshots
        self._save_initial_inventory_snapshots(run_id, tenant_id, lots)
        
        # Create working inventory
        initial_inventory = InventorySnapshot(
            timestamp=datetime.now(),
            lots=[self._copy_lot(lot) for lot in lots]
        )
        
        # Process transactions
        attributions, final_inventory = self.engine.process_transactions(
            initial_inventory, sales
        )
        
        # Journal all inventory movements
        self._journal_inventory_movements(run_id, tenant_id, initial_inventory, final_inventory, sales)
        
        # Save final inventory snapshots
        self._save_final_inventory_snapshots(run_id, tenant_id, final_inventory)
        
        # Save COGS attributions
        self._save_cogs_attributions(run_id, tenant_id, attributions)
        
        # Generate and save summaries
        summaries = self.engine.calculate_summary(attributions)
        self._save_cogs_summaries(run_id, tenant_id, summaries)
        
        # Save validation errors
        validation_errors = self.engine.get_validation_errors()
        self._save_validation_errors(run_id, tenant_id, validation_errors)
        
        total_cogs = sum(attr.total_cogs for attr in attributions)
        
        return {
            'attributions': attributions,
            'summaries': summaries,
            'final_inventory': final_inventory,
            'validation_errors': validation_errors,
            'total_cogs': total_cogs
        }
    
    def rollback_run(self, run_id: str, rollback_by: Optional[str] = None) -> Dict[str, Any]:
        """
        Rollback a run using inventory snapshots (idempotent).
        
        Args:
            run_id: Run to rollback
            rollback_by: User performing rollback
            
        Returns:
            Dict with rollback results
        """
        # Get run info
        run = self._get_run(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")
        
        if run['status'] == 'rolled_back':
            # Idempotent - already rolled back
            return {
                'run_id': run_id,
                'status': 'already_rolled_back',
                'message': f"Run {run_id} was already rolled back"
            }
        
        if run['status'] not in ['completed', 'failed']:
            raise ValueError(f"Cannot rollback run {run_id} with status {run['status']}")
        
        tenant_id = run['tenant_id']
        
        with TenantContext(tenant_id):
            try:
                # Restore inventory from snapshots
                restored_lots = self._restore_inventory_from_snapshots(run_id, tenant_id)
                
                # Mark COGS data as invalid
                self._invalidate_cogs_data(run_id, tenant_id)
                
                # Mark run as rolled back
                self._mark_run_rolled_back(run_id, rollback_by)
                
                # Create rollback audit entry
                rollback_run_id = self._create_rollback_audit_entry(run_id, tenant_id, rollback_by)
                
                self.logger.info(f"Run {run_id} successfully rolled back for tenant {tenant_id}")
                
                return {
                    'run_id': run_id,
                    'rollback_run_id': rollback_run_id,
                    'status': 'rolled_back',
                    'restored_lots_count': len(restored_lots),
                    'message': f"Run {run_id} successfully rolled back"
                }
                
            except Exception as e:
                self.logger.error(f"Failed to rollback run {run_id}: {e}")
                raise
    
    def _save_initial_inventory_snapshots(self, run_id: str, tenant_id: str, lots: List[PurchaseLot]):
        """Save inventory state before processing"""
        for lot in lots:
            snapshot = DBInventorySnapshot(
                snapshot_id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                run_id=run_id,
                lot_id=lot.lot_id,
                sku=lot.sku,
                remaining_quantity=lot.remaining_quantity,
                original_quantity=lot.original_quantity,
                unit_price=lot.unit_price,
                freight_cost_per_unit=lot.freight_cost_per_unit,
                received_date=lot.received_date.date(),
                is_current=False,  # Pre-run snapshot
                created_at=datetime.now()
            )
            self._save_inventory_snapshot(snapshot)
    
    def _save_final_inventory_snapshots(self, run_id: str, tenant_id: str, inventory: InventorySnapshot):
        """Save inventory state after processing"""
        for lot in inventory.lots:
            snapshot = DBInventorySnapshot(
                snapshot_id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                run_id=run_id,
                lot_id=lot.lot_id,
                sku=lot.sku,
                remaining_quantity=lot.remaining_quantity,
                original_quantity=lot.original_quantity,
                unit_price=lot.unit_price,
                freight_cost_per_unit=lot.freight_cost_per_unit,
                received_date=lot.received_date.date(),
                is_current=True,  # Post-run snapshot
                created_at=datetime.now()
            )
            self._save_inventory_snapshot(snapshot)
    
    def _journal_inventory_movements(
        self,
        run_id: str,
        tenant_id: str,
        initial: InventorySnapshot,
        final: InventorySnapshot,
        sales: List[Sale]
    ):
        """Journal all inventory movements"""
        # Create lookup for final quantities
        final_quantities = {lot.lot_id: lot.remaining_quantity for lot in final.lots}
        
        # Track changes per lot
        for initial_lot in initial.lots:
            final_qty = final_quantities.get(initial_lot.lot_id, 0)
            change = final_qty - initial_lot.remaining_quantity
            
            if change != 0:
                movement = InventoryMovement(
                    movement_id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    run_id=run_id,
                    lot_id=initial_lot.lot_id,
                    sku=initial_lot.sku,
                    movement_type='sale' if change < 0 else 'return',
                    quantity=change,
                    remaining_after=final_qty,
                    unit_cost=initial_lot.total_unit_cost,
                    reference_id=None,  # Could link to specific sale
                    created_at=datetime.now()
                )
                self._save_inventory_movement(movement)
    
    def _restore_inventory_from_snapshots(self, run_id: str, tenant_id: str) -> List[Dict[str, Any]]:
        """Restore inventory to pre-run state using snapshots"""
        # Get pre-run snapshots (is_current=False)
        pre_run_snapshots = self._get_inventory_snapshots(run_id, tenant_id, is_current=False)
        
        restored_lots = []
        for snapshot in pre_run_snapshots:
            # This would update the actual inventory table
            restored_lots.append({
                'lot_id': snapshot['lot_id'],
                'sku': snapshot['sku'],
                'restored_quantity': snapshot['remaining_quantity']
            })
            
            # Create rollback movement
            rollback_movement = InventoryMovement(
                movement_id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                run_id=run_id,
                lot_id=snapshot['lot_id'],
                sku=snapshot['sku'],
                movement_type='rollback',
                quantity=0,  # Restoration, not a change
                remaining_after=snapshot['remaining_quantity'],
                unit_cost=snapshot['unit_price'] + snapshot['freight_cost_per_unit'],
                reference_id=run_id,
                created_at=datetime.now()
            )
            self._save_inventory_movement(rollback_movement)
        
        return restored_lots
    
    def _copy_lot(self, lot: PurchaseLot) -> PurchaseLot:
        """Create a deep copy of a lot"""
        return PurchaseLot(
            lot_id=lot.lot_id,
            sku=lot.sku,
            received_date=lot.received_date,
            original_quantity=lot.original_quantity,
            remaining_quantity=lot.remaining_quantity,
            unit_price=lot.unit_price,
            freight_cost_per_unit=lot.freight_cost_per_unit,
            tenant_id=lot.tenant_id
        )
    
    # Database adapter methods (would be implemented based on your DB choice)
    def _save_run(self, run: COGSRun):
        """Save run to database"""
        if self.db_adapter:
            self.db_adapter.save_run(run)
    
    def _update_run(self, run: COGSRun):
        """Update run in database"""
        if self.db_adapter:
            self.db_adapter.update_run(run)
    
    def _get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get run from database"""
        if self.db_adapter:
            return self.db_adapter.get_run(run_id)
        return None
    
    def _get_active_runs(self, tenant_id: str) -> List[str]:
        """Get active runs for tenant"""
        if self.db_adapter:
            return self.db_adapter.get_active_runs(tenant_id)
        return []
    
    def _save_inventory_snapshot(self, snapshot: DBInventorySnapshot):
        """Save inventory snapshot"""
        if self.db_adapter:
            self.db_adapter.save_inventory_snapshot(snapshot)
    
    def _save_inventory_movement(self, movement: InventoryMovement):
        """Save inventory movement"""
        if self.db_adapter:
            self.db_adapter.save_inventory_movement(movement)
    
    def _save_cogs_attributions(self, run_id: str, tenant_id: str, attributions):
        """Save COGS attributions"""
        if self.db_adapter:
            self.db_adapter.save_cogs_attributions(run_id, tenant_id, attributions)
    
    def _save_cogs_summaries(self, run_id: str, tenant_id: str, summaries):
        """Save COGS summaries"""
        if self.db_adapter:
            self.db_adapter.save_cogs_summaries(run_id, tenant_id, summaries)
    
    def _save_validation_errors(self, run_id: str, tenant_id: str, errors):
        """Save validation errors"""
        if self.db_adapter:
            self.db_adapter.save_validation_errors(run_id, tenant_id, errors)
    
    def _get_inventory_snapshots(self, run_id: str, tenant_id: str, is_current: bool) -> List[Dict[str, Any]]:
        """Get inventory snapshots"""
        if self.db_adapter:
            return self.db_adapter.get_inventory_snapshots(run_id, tenant_id, is_current)
        return []
    
    def _invalidate_cogs_data(self, run_id: str, tenant_id: str):
        """Mark COGS data as invalid"""
        if self.db_adapter:
            self.db_adapter.invalidate_cogs_data(run_id, tenant_id)
    
    def _mark_run_rolled_back(self, run_id: str, rollback_by: Optional[str]):
        """Mark run as rolled back"""
        if self.db_adapter:
            self.db_adapter.mark_run_rolled_back(run_id, rollback_by)
    
    def _create_rollback_audit_entry(self, run_id: str, tenant_id: str, rollback_by: Optional[str]) -> str:
        """Create audit entry for rollback"""
        if self.db_adapter:
            return self.db_adapter.create_rollback_audit_entry(run_id, tenant_id, rollback_by)
        return str(uuid.uuid4())
    
    def generate_journal_entry(self, run_id: str, format: str = "csv") -> str:
        """Generate journal entry for accounting systems"""
        if self.db_adapter:
            return self.db_adapter.generate_journal_entry(run_id, format)
        return ""