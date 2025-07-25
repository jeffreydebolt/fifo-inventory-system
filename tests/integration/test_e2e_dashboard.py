"""
End-to-end tests for the dashboard integration.
Tests the full flow: upload → run → rollback → run again.
"""
import unittest
import sys
import os
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.models import PurchaseLot, Sale
from core.fifo_engine import FIFOEngine
from services.journaled_calculator import JournaledCalculator
from tests.integration.test_journaled_runs import MockDBAdapter


class TestE2EDashboard(unittest.TestCase):
    """End-to-end tests for dashboard integration"""
    
    def setUp(self):
        """Set up test data"""
        self.engine = FIFOEngine()
        self.db_adapter = MockDBAdapter()
        self.calculator = JournaledCalculator(self.engine, self.db_adapter)
        
        # Test data for tenant A
        self.tenant_a = "tenant-a"
        self.tenant_b = "tenant-b"
        
        self.lots_a = [
            PurchaseLot(
                lot_id="A_LOT001",
                sku="SKU-A",
                received_date=datetime(2024, 1, 1),
                original_quantity=100,
                remaining_quantity=100,
                unit_price=Decimal("10.00"),
                freight_cost_per_unit=Decimal("1.00"),
                tenant_id=self.tenant_a
            )
        ]
        
        self.sales_a = [
            Sale(
                sale_id="A_SALE001",
                sku="SKU-A",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=30,
                tenant_id=self.tenant_a
            )
        ]
        
        self.lots_b = [
            PurchaseLot(
                lot_id="B_LOT001",
                sku="SKU-A",
                received_date=datetime(2024, 1, 1),
                original_quantity=200,
                remaining_quantity=200,
                unit_price=Decimal("15.00"),
                freight_cost_per_unit=Decimal("1.50"),
                tenant_id=self.tenant_b
            )
        ]
        
        self.sales_b = [
            Sale(
                sale_id="B_SALE001",
                sku="SKU-A",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=50,
                tenant_id=self.tenant_b
            )
        ]
    
    def test_full_run_rollback_run_again_flow(self):
        """Test: Run → Rollback → Run again flow passes"""
        
        # Step 1: First run for tenant A
        result1 = self.calculator.create_and_execute_run(
            tenant_id=self.tenant_a,
            lots=self.lots_a,
            sales=self.sales_a,
            mode="fifo"
        )
        
        run_id1 = result1['run_id']
        self.assertEqual(result1['status'], 'completed')
        
        # Verify run was saved
        run_data1 = self.db_adapter.get_run(run_id1)
        self.assertIsNotNone(run_data1)
        self.assertEqual(run_data1['status'], 'completed')
        
        # Step 2: Rollback the run
        rollback_result = self.calculator.rollback_run(run_id1)
        self.assertEqual(rollback_result['status'], 'rolled_back')
        
        # Verify rollback marked the original run
        updated_run_data1 = self.db_adapter.get_run(run_id1)
        self.assertEqual(updated_run_data1['status'], 'rolled_back')
        
        # Step 3: Run again with same data
        result2 = self.calculator.create_and_execute_run(
            tenant_id=self.tenant_a,
            lots=self.lots_a,
            sales=self.sales_a,
            mode="fifo"
        )
        
        run_id2 = result2['run_id']
        self.assertEqual(result2['status'], 'completed')
        self.assertNotEqual(run_id1, run_id2)  # Different run IDs
        
        # Verify results are identical
        self.assertEqual(result1['total_cogs'], result2['total_cogs'])
        self.assertEqual(len(result1['attributions']), len(result2['attributions']))
        
        print("✅ Full Run → Rollback → Run again flow completed successfully")
    
    def test_tenant_isolation_in_runs_and_rollback(self):
        """Test: A tenant cannot see or rollback another tenant's runs"""
        
        # Run for tenant A
        result_a = self.calculator.create_and_execute_run(
            tenant_id=self.tenant_a,
            lots=self.lots_a,
            sales=self.sales_a,
            mode="fifo"
        )
        
        # Run for tenant B
        result_b = self.calculator.create_and_execute_run(
            tenant_id=self.tenant_b,
            lots=self.lots_b,
            sales=self.sales_b,
            mode="fifo"
        )
        
        # Verify both completed
        self.assertEqual(result_a['status'], 'completed')
        self.assertEqual(result_b['status'], 'completed')
        
        # Verify different COGS (different costs)
        self.assertNotEqual(result_a['total_cogs'], result_b['total_cogs'])
        
        # Verify tenant A's run data is isolated
        run_a_data = self.db_adapter.get_run(result_a['run_id'])
        run_b_data = self.db_adapter.get_run(result_b['run_id'])
        
        self.assertEqual(run_a_data['tenant_id'], self.tenant_a)
        self.assertEqual(run_b_data['tenant_id'], self.tenant_b)
        
        # Verify active runs query respects tenant isolation
        active_a = self.db_adapter.get_active_runs(self.tenant_a)
        active_b = self.db_adapter.get_active_runs(self.tenant_b)
        
        # Both runs completed, so no active runs
        self.assertEqual(len(active_a), 0)
        self.assertEqual(len(active_b), 0)
        
        # Rollback tenant A's run
        rollback_result = self.calculator.rollback_run(result_a['run_id'])
        self.assertEqual(rollback_result['status'], 'rolled_back')
        
        # Verify tenant B's run is unaffected
        updated_run_b = self.db_adapter.get_run(result_b['run_id'])
        self.assertEqual(updated_run_b['status'], 'completed')
        
        print("✅ Tenant isolation verified for runs and rollback")
    
    def test_api_error_scenarios(self):
        """Test common API error scenarios"""
        
        # Test concurrent run rejection
        # First, create a "running" run
        self.db_adapter.runs['concurrent_test'] = {
            'run_id': 'concurrent_test',
            'tenant_id': self.tenant_a,
            'status': 'running',
            'started_at': datetime.now()
        }
        
        # Try to start another run - should fail
        with self.assertRaises(ValueError) as context:
            self.calculator.create_and_execute_run(
                tenant_id=self.tenant_a,
                lots=self.lots_a,
                sales=self.sales_a,
                mode="fifo"
            )
        
        self.assertIn("active run", str(context.exception))
        
        # Test rollback of non-existent run
        with self.assertRaises(ValueError) as context:
            self.calculator.rollback_run("nonexistent-run-id")
        
        self.assertIn("not found", str(context.exception))
        
        # Test idempotent rollback
        result = self.calculator.create_and_execute_run(
            tenant_id=self.tenant_b,
            lots=self.lots_b,
            sales=self.sales_b,
            mode="fifo"
        )
        
        run_id = result['run_id']
        
        # First rollback
        rollback1 = self.calculator.rollback_run(run_id)
        self.assertEqual(rollback1['status'], 'rolled_back')
        
        # Second rollback (idempotent)
        rollback2 = self.calculator.rollback_run(run_id)
        self.assertEqual(rollback2['status'], 'already_rolled_back')
        
        print("✅ API error scenarios handled correctly")
    
    def test_validation_and_error_handling(self):
        """Test validation and error handling"""
        
        # Test with insufficient inventory
        insufficient_sales = [
            Sale(
                sale_id="INSUFFICIENT_SALE",
                sku="SKU-A",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=1000,  # More than available
                tenant_id=self.tenant_a
            )
        ]
        
        result = self.calculator.create_and_execute_run(
            tenant_id=self.tenant_a,
            lots=self.lots_a,
            sales=insufficient_sales,
            mode="fifo"
        )
        
        # Should complete but have validation errors
        self.assertEqual(result['status'], 'completed')
        self.assertGreater(len(result['validation_errors']), 0)
        
        # Verify validation errors were saved
        run_data = self.db_adapter.get_run(result['run_id'])
        self.assertGreater(run_data['validation_errors_count'], 0)
        
        print("✅ Validation and error handling working correctly")


if __name__ == '__main__':
    unittest.main()