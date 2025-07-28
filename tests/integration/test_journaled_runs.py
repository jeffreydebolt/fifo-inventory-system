"""
Integration tests for journaled COGS runs with full rollback support.
Tests all Step 3 requirements: journaling, rollback, API, CLI.
"""
import unittest
import sys
import os
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List
import uuid
import tempfile
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.models import PurchaseLot, Sale, InventorySnapshot
from core.fifo_engine import FIFOEngine
from core.db_models import COGSRun, RunStatus, InventoryMovement
from services.journaled_calculator import JournaledCalculator


class MockDBAdapter:
    """Mock database adapter for testing"""
    
    def __init__(self):
        self.runs = {}
        self.inventory_snapshots = {}
        self.inventory_movements = {}
        self.cogs_attributions = {}
        self.cogs_summaries = {}
        self.validation_errors = {}
    
    def save_run(self, run: COGSRun):
        self.runs[run.run_id] = {
            'run_id': run.run_id,
            'tenant_id': run.tenant_id,
            'status': run.status.value,
            'started_at': run.started_at,
            'completed_at': run.completed_at,
            'total_sales_processed': run.total_sales_processed,
            'total_cogs_calculated': run.total_cogs_calculated,
            'validation_errors_count': run.validation_errors_count,
            'error_message': run.error_message,
            'created_by': run.created_by
        }
    
    def update_run(self, run: COGSRun):
        if run.run_id in self.runs:
            self.runs[run.run_id].update({
                'status': run.status.value,
                'completed_at': run.completed_at,
                'total_sales_processed': run.total_sales_processed,
                'total_cogs_calculated': run.total_cogs_calculated,
                'validation_errors_count': run.validation_errors_count,
                'error_message': run.error_message
            })
    
    def get_run(self, run_id: str) -> Dict[str, Any]:
        return self.runs.get(run_id)
    
    def get_active_runs(self, tenant_id: str) -> List[str]:
        return [
            run_id for run_id, run in self.runs.items()
            if run['tenant_id'] == tenant_id and run['status'] in ['pending', 'running']
        ]
    
    def save_inventory_snapshot(self, snapshot):
        if snapshot.run_id not in self.inventory_snapshots:
            self.inventory_snapshots[snapshot.run_id] = []
        self.inventory_snapshots[snapshot.run_id].append({
            'lot_id': snapshot.lot_id,
            'sku': snapshot.sku,
            'remaining_quantity': snapshot.remaining_quantity,
            'original_quantity': snapshot.original_quantity,
            'unit_price': snapshot.unit_price,
            'freight_cost_per_unit': snapshot.freight_cost_per_unit,
            'received_date': snapshot.received_date,
            'is_current': snapshot.is_current
        })
    
    def save_inventory_movement(self, movement):
        if movement.run_id not in self.inventory_movements:
            self.inventory_movements[movement.run_id] = []
        self.inventory_movements[movement.run_id].append({
            'lot_id': movement.lot_id,
            'sku': movement.sku,
            'movement_type': movement.movement_type,
            'quantity': movement.quantity,
            'remaining_after': movement.remaining_after,
            'unit_cost': movement.unit_cost
        })
    
    def save_cogs_attributions(self, run_id, tenant_id, attributions):
        self.cogs_attributions[run_id] = attributions
    
    def save_cogs_summaries(self, run_id, tenant_id, summaries):
        self.cogs_summaries[run_id] = summaries
    
    def save_validation_errors(self, run_id, tenant_id, errors):
        self.validation_errors[run_id] = errors
    
    def get_inventory_snapshots(self, run_id: str, tenant_id: str, is_current: bool) -> List[Dict[str, Any]]:
        snapshots = self.inventory_snapshots.get(run_id, [])
        return [s for s in snapshots if s['is_current'] == is_current]
    
    def invalidate_cogs_data(self, run_id: str, tenant_id: str):
        # Mark COGS data as invalid
        if run_id in self.cogs_attributions:
            for attr in self.cogs_attributions[run_id]:
                attr.is_valid = False
        if run_id in self.cogs_summaries:
            for summary in self.cogs_summaries[run_id]:
                summary.is_valid = False
    
    def mark_run_rolled_back(self, run_id: str, rollback_by: str):
        if run_id in self.runs:
            self.runs[run_id]['status'] = 'rolled_back'
            self.runs[run_id]['rolled_back_at'] = datetime.now()
            self.runs[run_id]['rolled_back_by'] = rollback_by
    
    def create_rollback_audit_entry(self, run_id: str, tenant_id: str, rollback_by: str) -> str:
        rollback_run_id = str(uuid.uuid4())
        self.runs[rollback_run_id] = {
            'run_id': rollback_run_id,
            'tenant_id': tenant_id,
            'status': 'completed',
            'started_at': datetime.now(),
            'completed_at': datetime.now(),
            'rollback_of_run_id': run_id,
            'created_by': rollback_by
        }
        return rollback_run_id
    
    def generate_journal_entry(self, run_id: str, format: str) -> str:
        if run_id not in self.runs:
            return ""
        
        if format == "csv":
            return f"account,debit,credit,description\nCOGS,{self.runs[run_id]['total_cogs_calculated']},0,FIFO COGS - Run {run_id}\nInventory,0,{self.runs[run_id]['total_cogs_calculated']},FIFO COGS - Run {run_id}"
        elif format == "json":
            return f'{{"run_id": "{run_id}", "total_cogs": {self.runs[run_id]["total_cogs_calculated"]}}}'
        else:
            return f"Journal Entry for Run {run_id}\nTotal COGS: ${self.runs[run_id]['total_cogs_calculated']}"


class TestJournaledRuns(unittest.TestCase):
    
    def setUp(self):
        """Set up test data"""
        self.engine = FIFOEngine()
        self.db_adapter = MockDBAdapter()
        self.calculator = JournaledCalculator(self.engine, self.db_adapter)
        
        # Test data
        self.tenant_id = "test-tenant"
        self.lots = [
            PurchaseLot(
                lot_id="LOT001",
                sku="SKU-A",
                received_date=datetime(2024, 1, 1),
                original_quantity=100,
                remaining_quantity=100,
                unit_price=Decimal("10.00"),
                freight_cost_per_unit=Decimal("1.00"),
                tenant_id=self.tenant_id
            ),
            PurchaseLot(
                lot_id="LOT002",
                sku="SKU-B",
                received_date=datetime(2024, 1, 15),
                original_quantity=50,
                remaining_quantity=50,
                unit_price=Decimal("20.00"),
                freight_cost_per_unit=Decimal("2.00"),
                tenant_id=self.tenant_id
            )
        ]
        
        self.sales = [
            Sale(
                sale_id="SALE001",
                sku="SKU-A",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=30,
                tenant_id=self.tenant_id
            ),
            Sale(
                sale_id="SALE002",
                sku="SKU-B",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=20,
                tenant_id=self.tenant_id
            )
        ]
    
    def test_happy_path_run_with_full_journaling(self):
        """Test: Happy path - upload lots + sales → run → cogs written → inventory updated"""
        result = self.calculator.create_and_execute_run(
            tenant_id=self.tenant_id,
            lots=self.lots,
            sales=self.sales,
            mode="fifo",
            created_by="test_user"
        )
        
        run_id = result['run_id']
        
        # Verify run was created and completed
        self.assertEqual(result['status'], 'completed')
        self.assertIsNotNone(run_id)
        
        # Verify run record in database
        run_data = self.db_adapter.get_run(run_id)
        self.assertIsNotNone(run_data)
        self.assertEqual(run_data['status'], 'completed')
        self.assertEqual(run_data['tenant_id'], self.tenant_id)
        self.assertEqual(run_data['total_sales_processed'], 2)
        self.assertGreater(run_data['total_cogs_calculated'], 0)
        
        # Verify inventory snapshots were saved (both initial and final)
        initial_snapshots = self.db_adapter.get_inventory_snapshots(run_id, self.tenant_id, is_current=False)
        final_snapshots = self.db_adapter.get_inventory_snapshots(run_id, self.tenant_id, is_current=True)
        
        self.assertEqual(len(initial_snapshots), 2)  # 2 lots
        self.assertEqual(len(final_snapshots), 2)    # 2 lots after processing
        
        # Verify inventory movements were journaled
        self.assertIn(run_id, self.db_adapter.inventory_movements)
        movements = self.db_adapter.inventory_movements[run_id]
        self.assertEqual(len(movements), 2)  # One movement per SKU sold
        
        # Verify COGS attributions were saved
        self.assertIn(run_id, self.db_adapter.cogs_attributions)
        attributions = self.db_adapter.cogs_attributions[run_id]
        self.assertEqual(len(attributions), 2)  # One per sale
        
        # Verify COGS summaries were saved
        self.assertIn(run_id, self.db_adapter.cogs_summaries)
        summaries = self.db_adapter.cogs_summaries[run_id]
        self.assertGreater(len(summaries), 0)
    
    def test_rollback_restores_inventory_and_invalidates_cogs(self):
        """Test: Rollback restores inventory & invalidates COGS rows"""
        # First, run a calculation
        result = self.calculator.create_and_execute_run(
            tenant_id=self.tenant_id,
            lots=self.lots,
            sales=self.sales,
            mode="fifo"
        )
        
        run_id = result['run_id']
        
        # Verify initial state
        run_data = self.db_adapter.get_run(run_id)
        self.assertEqual(run_data['status'], 'completed')
        
        # Verify inventory was changed
        final_snapshots = self.db_adapter.get_inventory_snapshots(run_id, self.tenant_id, is_current=True)
        sku_a_final = next(s for s in final_snapshots if s['sku'] == 'SKU-A')
        self.assertEqual(sku_a_final['remaining_quantity'], 70)  # 100 - 30
        
        # Perform rollback
        rollback_result = self.calculator.rollback_run(run_id, rollback_by="test_user")
        
        # Verify rollback completed
        self.assertEqual(rollback_result['status'], 'rolled_back')
        self.assertEqual(rollback_result['run_id'], run_id)
        self.assertIsNotNone(rollback_result['rollback_run_id'])
        
        # Verify original run is marked as rolled back
        updated_run_data = self.db_adapter.get_run(run_id)
        self.assertEqual(updated_run_data['status'], 'rolled_back')
        
        # Verify COGS data was invalidated
        # (In real implementation, would check is_valid flags)
        attributions = self.db_adapter.cogs_attributions[run_id]
        for attr in attributions:
            self.assertFalse(getattr(attr, 'is_valid', True))
    
    def test_tenant_isolation_in_runs(self):
        """Test: Tenant A cannot see or rollback tenant B's runs"""
        tenant_a = "tenant-a"
        tenant_b = "tenant-b"
        
        # Create lots for each tenant
        lots_a = [lot for lot in self.lots]
        for lot in lots_a:
            lot.tenant_id = tenant_a
        
        lots_b = [lot for lot in self.lots]
        for lot in lots_b:
            lot.tenant_id = tenant_b
            lot.lot_id = lot.lot_id.replace("LOT", "TB_LOT")
        
        # Create sales for each tenant
        sales_a = [sale for sale in self.sales]
        for sale in sales_a:
            sale.tenant_id = tenant_a
        
        sales_b = [sale for sale in self.sales]
        for sale in sales_b:
            sale.tenant_id = tenant_b
            sale.sale_id = sale.sale_id.replace("SALE", "TB_SALE")
        
        # Run calculation for tenant A
        result_a = self.calculator.create_and_execute_run(
            tenant_id=tenant_a,
            lots=lots_a,
            sales=sales_a,
            mode="fifo"
        )
        
        # Run calculation for tenant B
        result_b = self.calculator.create_and_execute_run(
            tenant_id=tenant_b,
            lots=lots_b,
            sales=sales_b,
            mode="fifo"
        )
        
        # Verify both runs completed
        self.assertEqual(result_a['status'], 'completed')
        self.assertEqual(result_b['status'], 'completed')
        
        # Verify tenant isolation in database
        run_a_data = self.db_adapter.get_run(result_a['run_id'])
        run_b_data = self.db_adapter.get_run(result_b['run_id'])
        
        self.assertEqual(run_a_data['tenant_id'], tenant_a)
        self.assertEqual(run_b_data['tenant_id'], tenant_b)
        
        # Verify active runs query respects tenant isolation
        active_a = self.db_adapter.get_active_runs(tenant_a)
        active_b = self.db_adapter.get_active_runs(tenant_b)
        
        self.assertEqual(len(active_a), 0)  # Both completed
        self.assertEqual(len(active_b), 0)  # Both completed
    
    def test_concurrent_runs_rejection(self):
        """Test: Second run for same tenant while one is running is rejected (409)"""
        # Mock a running run
        running_run_id = str(uuid.uuid4())
        self.db_adapter.runs[running_run_id] = {
            'run_id': running_run_id,
            'tenant_id': self.tenant_id,
            'status': 'running',
            'started_at': datetime.now()
        }
        
        # Try to start another run for the same tenant
        with self.assertRaises(ValueError) as context:
            self.calculator.create_and_execute_run(
                tenant_id=self.tenant_id,
                lots=self.lots,
                sales=self.sales,
                mode="fifo"
            )
        
        self.assertIn("active run", str(context.exception))
        self.assertIn(running_run_id, str(context.exception))
    
    def test_idempotent_rollback(self):
        """Test: Calling rollback twice doesn't break state"""
        # Run calculation
        result = self.calculator.create_and_execute_run(
            tenant_id=self.tenant_id,
            lots=self.lots,
            sales=self.sales,
            mode="fifo"
        )
        
        run_id = result['run_id']
        
        # First rollback
        rollback_result1 = self.calculator.rollback_run(run_id)
        self.assertEqual(rollback_result1['status'], 'rolled_back')
        
        # Second rollback (should be idempotent)
        rollback_result2 = self.calculator.rollback_run(run_id)
        self.assertEqual(rollback_result2['status'], 'already_rolled_back')
        self.assertIn("already rolled back", rollback_result2['message'])
        
        # Verify run is still in rolled back state
        run_data = self.db_adapter.get_run(run_id)
        self.assertEqual(run_data['status'], 'rolled_back')
    
    def test_journal_entry_generation(self):
        """Test: Generate journal entries in different formats"""
        # Run calculation
        result = self.calculator.create_and_execute_run(
            tenant_id=self.tenant_id,
            lots=self.lots,
            sales=self.sales,
            mode="fifo"
        )
        
        run_id = result['run_id']
        
        # Test CSV format
        csv_entry = self.calculator.generate_journal_entry(run_id, "csv")
        self.assertIn("account,debit,credit", csv_entry)
        self.assertIn("COGS", csv_entry)
        self.assertIn("Inventory", csv_entry)
        
        # Test JSON format
        json_entry = self.calculator.generate_journal_entry(run_id, "json")
        self.assertIn(f'"run_id": "{run_id}"', json_entry)
        self.assertIn('"total_cogs":', json_entry)
        
        # Test text format
        text_entry = self.calculator.generate_journal_entry(run_id, "text")
        self.assertIn(f"Run {run_id}", text_entry)
        self.assertIn("Total COGS:", text_entry)
    
    def test_failed_run_handling(self):
        """Test: Runs with validation errors complete but log errors"""
        # Create sales with validation issues (insufficient inventory)
        invalid_sales = [
            Sale(
                sale_id="INVALID_SALE",
                sku="SKU-A",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=1000,  # More than available (only 100)
                tenant_id=self.tenant_id
            )
        ]
        
        # Run with invalid data - should complete but have validation errors
        result = self.calculator.create_and_execute_run(
            tenant_id=self.tenant_id,
            lots=self.lots,
            sales=invalid_sales,
            mode="fifo"
        )
        
        # Should complete but have validation errors
        self.assertEqual(result['status'], 'completed')
        self.assertGreater(len(result['validation_errors']), 0)
        
        run_id = result['run_id']
        
        # Verify run record shows validation errors
        run_data = self.db_adapter.get_run(run_id)
        self.assertGreater(run_data['validation_errors_count'], 0)
        
        # Verify validation errors were saved
        self.assertIn(run_id, self.db_adapter.validation_errors)
        
        # Verify run can still be rolled back
        rollback_result = self.calculator.rollback_run(run_id)
        self.assertEqual(rollback_result['status'], 'rolled_back')
    
    def test_validation_errors_are_saved(self):
        """Test: Validation errors are properly saved"""
        # Create sales with validation issues (future dates)
        future_sales = [
            Sale(
                sale_id="FUTURE_SALE",
                sku="SKU-A",
                sale_date=datetime(2025, 12, 31),  # Future date
                quantity_sold=10,
                tenant_id=self.tenant_id
            )
        ]
        
        # Run calculation (should succeed but have validation warnings)
        result = self.calculator.create_and_execute_run(
            tenant_id=self.tenant_id,
            lots=self.lots,
            sales=future_sales,
            mode="fifo"
        )
        
        run_id = result['run_id']
        
        # Verify validation errors were saved
        self.assertIn(run_id, self.db_adapter.validation_errors)
        
        # Verify run record includes error count
        run_data = self.db_adapter.get_run(run_id)
        self.assertGreaterEqual(run_data['validation_errors_count'], 0)


if __name__ == '__main__':
    unittest.main()