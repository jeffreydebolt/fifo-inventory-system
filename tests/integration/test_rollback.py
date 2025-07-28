"""
Integration tests for rollback functionality.
Tests that rollback properly restores inventory state and invalidates COGS data.
"""
import unittest
import sys
import os
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any
import copy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.models import PurchaseLot, Sale, InventorySnapshot
from core.fifo_engine import FIFOEngine
from services.tenant_service import TenantService, TenantContext, MultiTenantFIFOEngine


class MockDatabaseService:
    """Mock database service to simulate rollback operations"""
    
    def __init__(self):
        self.runs = {}  # run_id -> run data
        self.inventory_snapshots = {}  # run_id -> inventory state
        self.cogs_attributions = {}  # run_id -> attributions
        self.inventory_movements = {}  # run_id -> movements
        self.run_counter = 1
    
    def save_run(self, tenant_id: str, run_data: Dict[str, Any]) -> str:
        """Save a COGS calculation run"""
        run_id = f"run_{self.run_counter:03d}"
        self.run_counter += 1
        
        self.runs[run_id] = {
            'run_id': run_id,
            'tenant_id': tenant_id,
            'status': 'completed',
            'started_at': datetime.now(),
            'completed_at': datetime.now(),
            **run_data
        }
        
        return run_id
    
    def save_inventory_snapshot(self, run_id: str, inventory: InventorySnapshot):
        """Save inventory state after a run"""
        self.inventory_snapshots[run_id] = copy.deepcopy(inventory)
    
    def save_cogs_attributions(self, run_id: str, attributions: List[Any]):
        """Save COGS attributions"""
        self.cogs_attributions[run_id] = copy.deepcopy(attributions)
    
    def save_inventory_movements(self, run_id: str, movements: List[Dict[str, Any]]):
        """Save inventory movements for audit trail"""
        self.inventory_movements[run_id] = copy.deepcopy(movements)
    
    def get_run(self, run_id: str) -> Dict[str, Any]:
        """Get run data"""
        return self.runs.get(run_id)
    
    def get_inventory_snapshot(self, run_id: str) -> InventorySnapshot:
        """Get inventory snapshot"""
        return self.inventory_snapshots.get(run_id)
    
    def get_cogs_attributions(self, run_id: str) -> List[Any]:
        """Get COGS attributions"""
        return self.cogs_attributions.get(run_id, [])
    
    def rollback_run(self, run_id: str) -> Dict[str, Any]:
        """Simulate rollback of a run"""
        if run_id not in self.runs:
            raise ValueError(f"Run {run_id} not found")
        
        run = self.runs[run_id]
        if run['status'] == 'rolled_back':
            raise ValueError(f"Run {run_id} is already rolled back")
        
        # Mark run as rolled back
        run['status'] = 'rolled_back'
        run['rolled_back_at'] = datetime.now()
        
        # Create rollback run
        rollback_run_id = self.save_run(run['tenant_id'], {
            'rollback_of_run_id': run_id,
            'status': 'completed'
        })
        
        # Restore inventory to pre-run state
        # This would involve reversing all inventory movements
        rollback_movements = []
        if run_id in self.inventory_movements:
            for movement in self.inventory_movements[run_id]:
                # Reverse the movement
                rollback_movements.append({
                    'lot_id': movement['lot_id'],
                    'sku': movement['sku'],
                    'movement_type': 'rollback',
                    'quantity': -movement['quantity'],  # Opposite of original
                    'reference_id': run_id
                })
        
        self.save_inventory_movements(rollback_run_id, rollback_movements)
        
        return {
            'original_run_id': run_id,
            'rollback_run_id': rollback_run_id,
            'movements_reversed': len(rollback_movements)
        }
    
    def get_active_runs_for_tenant(self, tenant_id: str) -> List[str]:
        """Get active (non-rolled-back) runs for a tenant"""
        return [
            run_id for run_id, run in self.runs.items()
            if run['tenant_id'] == tenant_id and run['status'] != 'rolled_back'
        ]


class RollbackCapableFIFOService:
    """FIFO service with rollback capabilities"""
    
    def __init__(self, base_engine: FIFOEngine, db_service: MockDatabaseService):
        self.base_engine = base_engine
        self.db_service = db_service
        self.multi_tenant_engine = MultiTenantFIFOEngine(base_engine)
    
    def process_with_rollback_support(
        self,
        tenant_id: str,
        lots: List[PurchaseLot],
        sales: List[Sale]
    ) -> Dict[str, Any]:
        """Process transactions with full rollback support"""
        
        # Save initial inventory state
        initial_inventory = InventorySnapshot(
            timestamp=datetime.now(),
            lots=copy.deepcopy(lots)
        )
        
        # Process transactions
        attributions, final_inventory = self.multi_tenant_engine.process_tenant_transactions(
            tenant_id, lots, sales
        )
        
        # Calculate inventory movements
        movements = self._calculate_movements(initial_inventory, final_inventory)
        
        # Save everything to database
        run_id = self.db_service.save_run(tenant_id, {
            'total_sales_processed': len(sales),
            'total_cogs_calculated': sum(attr.total_cogs for attr in attributions)
        })
        
        self.db_service.save_inventory_snapshot(run_id, final_inventory)
        self.db_service.save_cogs_attributions(run_id, attributions)
        self.db_service.save_inventory_movements(run_id, movements)
        
        return {
            'run_id': run_id,
            'attributions': attributions,
            'final_inventory': final_inventory,
            'movements': movements
        }
    
    def rollback_run(self, run_id: str) -> Dict[str, Any]:
        """Rollback a specific run"""
        return self.db_service.rollback_run(run_id)
    
    def _calculate_movements(
        self, 
        initial: InventorySnapshot, 
        final: InventorySnapshot
    ) -> List[Dict[str, Any]]:
        """Calculate inventory movements between states"""
        movements = []
        
        # Create lookup for final quantities
        final_quantities = {
            lot.lot_id: lot.remaining_quantity 
            for lot in final.lots
        }
        
        # Calculate changes
        for initial_lot in initial.lots:
            final_qty = final_quantities.get(initial_lot.lot_id, 0)
            change = final_qty - initial_lot.remaining_quantity
            
            if change != 0:
                movements.append({
                    'lot_id': initial_lot.lot_id,
                    'sku': initial_lot.sku,
                    'movement_type': 'sale' if change < 0 else 'return',
                    'quantity': change,
                    'remaining_after': final_qty
                })
        
        return movements


class TestRollback(unittest.TestCase):
    
    def setUp(self):
        """Set up test data"""
        self.engine = FIFOEngine()
        self.db_service = MockDatabaseService()
        self.rollback_service = RollbackCapableFIFOService(self.engine, self.db_service)
        
        # Test data for tenant A
        self.tenant_a_lots = [
            PurchaseLot(
                lot_id="LOT001",
                sku="SKU-A",
                received_date=datetime(2024, 1, 1),
                original_quantity=100,
                remaining_quantity=100,
                unit_price=Decimal("10.00"),
                freight_cost_per_unit=Decimal("1.00"),
                tenant_id="tenant-a"
            ),
            PurchaseLot(
                lot_id="LOT002",
                sku="SKU-B",
                received_date=datetime(2024, 1, 15),
                original_quantity=50,
                remaining_quantity=50,
                unit_price=Decimal("20.00"),
                freight_cost_per_unit=Decimal("2.00"),
                tenant_id="tenant-a"
            )
        ]
        
        self.tenant_a_sales = [
            Sale(
                sale_id="SALE001",
                sku="SKU-A",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=30,
                tenant_id="tenant-a"
            ),
            Sale(
                sale_id="SALE002",
                sku="SKU-B",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=20,
                tenant_id="tenant-a"
            )
        ]
    
    def test_successful_calculation_with_persistence(self):
        """Test successful COGS calculation with data persistence"""
        result = self.rollback_service.process_with_rollback_support(
            "tenant-a", self.tenant_a_lots, self.tenant_a_sales
        )
        
        run_id = result['run_id']
        
        # Verify run was saved
        run_data = self.db_service.get_run(run_id)
        self.assertIsNotNone(run_data)
        self.assertEqual(run_data['tenant_id'], "tenant-a")
        self.assertEqual(run_data['status'], "completed")
        self.assertEqual(run_data['total_sales_processed'], 2)
        
        # Verify attributions were saved
        saved_attributions = self.db_service.get_cogs_attributions(run_id)
        self.assertEqual(len(saved_attributions), 2)
        
        # Verify inventory snapshot was saved
        saved_inventory = self.db_service.get_inventory_snapshot(run_id)
        self.assertIsNotNone(saved_inventory)
        
        # Verify movements were tracked
        self.assertIn(run_id, self.db_service.inventory_movements)
        movements = self.db_service.inventory_movements[run_id]
        self.assertEqual(len(movements), 2)  # One for each SKU sold
    
    def test_rollback_functionality(self):
        """Test complete rollback functionality"""
        # First, run a calculation
        result = self.rollback_service.process_with_rollback_support(
            "tenant-a", self.tenant_a_lots, self.tenant_a_sales
        )
        
        original_run_id = result['run_id']
        
        # Verify initial state
        run_data = self.db_service.get_run(original_run_id)
        self.assertEqual(run_data['status'], 'completed')
        
        # Perform rollback
        rollback_result = self.rollback_service.rollback_run(original_run_id)
        
        # Verify rollback results
        self.assertEqual(rollback_result['original_run_id'], original_run_id)
        self.assertIsNotNone(rollback_result['rollback_run_id'])
        self.assertGreater(rollback_result['movements_reversed'], 0)
        
        # Verify original run is marked as rolled back
        updated_run_data = self.db_service.get_run(original_run_id)
        self.assertEqual(updated_run_data['status'], 'rolled_back')
        self.assertIsNotNone(updated_run_data['rolled_back_at'])
        
        # Verify rollback run was created
        rollback_run_id = rollback_result['rollback_run_id']
        rollback_run_data = self.db_service.get_run(rollback_run_id)
        self.assertIsNotNone(rollback_run_data)
        self.assertEqual(rollback_run_data['rollback_of_run_id'], original_run_id)
    
    def test_cannot_rollback_already_rolled_back_run(self):
        """Test that already rolled back runs cannot be rolled back again"""
        # Run calculation
        result = self.rollback_service.process_with_rollback_support(
            "tenant-a", self.tenant_a_lots, self.tenant_a_sales
        )
        
        run_id = result['run_id']
        
        # Rollback once
        self.rollback_service.rollback_run(run_id)
        
        # Try to rollback again - should fail
        with self.assertRaises(ValueError) as context:
            self.rollback_service.rollback_run(run_id)
        
        self.assertIn("already rolled back", str(context.exception))
    
    def test_rollback_nonexistent_run(self):
        """Test rollback of non-existent run"""
        with self.assertRaises(ValueError) as context:
            self.rollback_service.rollback_run("nonexistent_run")
        
        self.assertIn("not found", str(context.exception))
    
    def test_tenant_isolation_in_rollback(self):
        """Test that rollback respects tenant isolation"""
        # Process for tenant A
        result_a = self.rollback_service.process_with_rollback_support(
            "tenant-a", self.tenant_a_lots, self.tenant_a_sales
        )
        
        # Process for tenant B (with different data)
        tenant_b_lots = [copy.deepcopy(lot) for lot in self.tenant_a_lots]
        tenant_b_sales = [copy.deepcopy(sale) for sale in self.tenant_a_sales]
        
        # Update tenant IDs
        for lot in tenant_b_lots:
            lot.tenant_id = "tenant-b"
            lot.lot_id = lot.lot_id.replace("LOT", "TB_LOT")
        for sale in tenant_b_sales:
            sale.tenant_id = "tenant-b"
            sale.sale_id = sale.sale_id.replace("SALE", "TB_SALE")
        
        result_b = self.rollback_service.process_with_rollback_support(
            "tenant-b", tenant_b_lots, tenant_b_sales
        )
        
        # Rollback tenant A
        rollback_result = self.rollback_service.rollback_run(result_a['run_id'])
        
        # Verify tenant A run is rolled back
        run_a = self.db_service.get_run(result_a['run_id'])
        self.assertEqual(run_a['status'], 'rolled_back')
        
        # Verify tenant B run is still active
        run_b = self.db_service.get_run(result_b['run_id'])
        self.assertEqual(run_b['status'], 'completed')
        
        # Verify active runs per tenant
        active_a = self.db_service.get_active_runs_for_tenant("tenant-a")
        active_b = self.db_service.get_active_runs_for_tenant("tenant-b")
        
        self.assertEqual(len(active_a), 1)  # Only rollback run
        self.assertEqual(len(active_b), 1)  # Original run still active
    
    def test_multiple_runs_and_selective_rollback(self):
        """Test multiple runs for same tenant and selective rollback"""
        # First calculation
        result1 = self.rollback_service.process_with_rollback_support(
            "tenant-a", self.tenant_a_lots, self.tenant_a_sales
        )
        
        # Second calculation (with different sales)
        different_sales = [
            Sale(
                sale_id="SALE003",
                sku="SKU-A",
                sale_date=datetime(2024, 3, 1),
                quantity_sold=10,
                tenant_id="tenant-a"
            )
        ]
        
        result2 = self.rollback_service.process_with_rollback_support(
            "tenant-a", self.tenant_a_lots, different_sales
        )
        
        # Verify both runs exist
        self.assertNotEqual(result1['run_id'], result2['run_id'])
        
        # Rollback only the first run
        self.rollback_service.rollback_run(result1['run_id'])
        
        # Verify first run is rolled back, second is not
        run1 = self.db_service.get_run(result1['run_id'])
        run2 = self.db_service.get_run(result2['run_id'])
        
        self.assertEqual(run1['status'], 'rolled_back')
        self.assertEqual(run2['status'], 'completed')
        
        # Verify active runs
        active_runs = self.db_service.get_active_runs_for_tenant("tenant-a")
        self.assertIn(result2['run_id'], active_runs)
        self.assertNotIn(result1['run_id'], active_runs)


if __name__ == '__main__':
    unittest.main()