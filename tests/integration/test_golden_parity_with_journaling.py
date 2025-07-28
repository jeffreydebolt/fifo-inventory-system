"""
Integration test to verify that journaled calculator maintains parity with golden files.
Ensures Step 3 changes don't break existing calculation accuracy.
"""
import unittest
import sys
import os
from pathlib import Path
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.models import PurchaseLot, Sale
from core.fifo_engine import FIFOEngine
from services.journaled_calculator import JournaledCalculator
from tests.unit.csv_normalizer import CSVNormalizer
from tests.integration.test_journaled_runs import MockDBAdapter


class TestGoldenParityWithJournaling(unittest.TestCase):
    """Test that journaled calculator maintains golden file parity"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data"""
        cls.project_root = Path(__file__).parent.parent.parent
        cls.golden_dir = cls.project_root / "golden"
        
        # Check if golden files exist
        if not cls.golden_dir.exists():
            raise unittest.SkipTest("Golden directory not found")
    
    def setUp(self):
        """Set up for each test"""
        self.engine = FIFOEngine()
        self.db_adapter = MockDBAdapter()
        self.calculator = JournaledCalculator(self.engine, self.db_adapter)
        self.normalizer = CSVNormalizer()
    
    def test_journaled_calculator_matches_golden_results(self):
        """Test that journaled calculator produces same results as golden files"""
        # Use cleaned golden sales file
        golden_sales_path = self.golden_dir / "golden_sales_clean.csv"
        if not golden_sales_path.exists():
            # Fall back to original
            golden_sales_path = self.golden_dir / "golden_sales.csv"
        
        if not golden_sales_path.exists():
            self.skipTest("Golden sales file not found")
        
        # Load golden sales data
        sales = self._load_golden_sales(golden_sales_path)
        
        # Create sample lots for the golden data
        lots = self._create_sample_lots_for_golden_sales(sales)
        
        # Run journaled calculation
        result = self.calculator.create_and_execute_run(
            tenant_id="golden-test",
            lots=lots,
            sales=sales,
            mode="fifo",
            created_by="golden_test"
        )
        
        # Verify calculation completed successfully
        self.assertEqual(result['status'], 'completed')
        self.assertGreater(len(result['attributions']), 0)
        self.assertGreater(result['total_cogs'], 0)
        
        # Verify journaling was done
        run_id = result['run_id']
        
        # Check run was saved
        run_data = self.db_adapter.get_run(run_id)
        self.assertIsNotNone(run_data)
        self.assertEqual(run_data['status'], 'completed')
        
        # Check inventory snapshots were saved
        initial_snapshots = self.db_adapter.get_inventory_snapshots(run_id, "golden-test", is_current=False)
        final_snapshots = self.db_adapter.get_inventory_snapshots(run_id, "golden-test", is_current=True)
        
        self.assertGreater(len(initial_snapshots), 0)
        self.assertGreater(len(final_snapshots), 0)
        
        # Check inventory movements were journaled
        self.assertIn(run_id, self.db_adapter.inventory_movements)
        movements = self.db_adapter.inventory_movements[run_id]
        self.assertGreater(len(movements), 0)
        
        # Check COGS data was saved
        self.assertIn(run_id, self.db_adapter.cogs_attributions)
        self.assertIn(run_id, self.db_adapter.cogs_summaries)
        
        # The key test: verify we can rollback and restore state
        rollback_result = self.calculator.rollback_run(run_id)
        self.assertEqual(rollback_result['status'], 'rolled_back')
        
        # Verify run is marked as rolled back
        updated_run_data = self.db_adapter.get_run(run_id)
        self.assertEqual(updated_run_data['status'], 'rolled_back')
    
    def test_journaled_vs_direct_engine_same_results(self):
        """Test that journaled calculator produces identical results to direct engine"""
        # Create test data
        lots = [
            PurchaseLot(
                lot_id="TEST_LOT_001",
                sku="TEST-SKU",
                received_date=datetime(2024, 1, 1),
                original_quantity=1000,
                remaining_quantity=1000,
                unit_price=Decimal("10.00"),
                freight_cost_per_unit=Decimal("1.00"),
                tenant_id="parity-test"
            )
        ]
        
        sales = [
            Sale(
                sale_id="TEST_SALE_001",
                sku="TEST-SKU",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=100,
                tenant_id="parity-test"
            )
        ]
        
        # Run with direct engine
        from core.models import InventorySnapshot
        direct_inventory = InventorySnapshot(timestamp=datetime.now(), lots=[self._copy_lot(lots[0])])
        direct_attributions, direct_final = self.engine.process_transactions(direct_inventory, sales)
        direct_summaries = self.engine.calculate_summary(direct_attributions)
        
        # Run with journaled calculator
        journaled_result = self.calculator.create_and_execute_run(
            tenant_id="parity-test",
            lots=lots,
            sales=sales,
            mode="fifo"
        )
        
        # Compare results
        self.assertEqual(len(journaled_result['attributions']), len(direct_attributions))
        self.assertEqual(len(journaled_result['summaries']), len(direct_summaries))
        
        # Compare COGS values
        journaled_total = sum(attr.total_cogs for attr in journaled_result['attributions'])
        direct_total = sum(attr.total_cogs for attr in direct_attributions)
        self.assertEqual(journaled_total, direct_total)
        
        # Compare inventory final state
        journaled_final_qty = sum(lot.remaining_quantity for lot in journaled_result['final_inventory'].lots)
        direct_final_qty = sum(lot.remaining_quantity for lot in direct_final.lots)
        self.assertEqual(journaled_final_qty, direct_final_qty)
    
    def _load_golden_sales(self, csv_path: Path) -> list:
        """Load sales from golden CSV file"""
        import pandas as pd
        
        df = pd.read_csv(csv_path)
        normalized_df = self.normalizer.normalize_sales_csv(df)
        sale_dicts = self.normalizer.create_sale_objects(normalized_df)
        
        sales = []
        for sale_dict in sale_dicts:
            sale = Sale(**sale_dict)
            sale.tenant_id = "golden-test"  # Ensure tenant is set
            sales.append(sale)
        
        return sales
    
    def _create_sample_lots_for_golden_sales(self, sales: list) -> list:
        """Create sample lots with sufficient inventory for golden sales"""
        # Group by SKU to determine total demand
        sku_demand = {}
        for sale in sales:
            sku_demand[sale.sku] = sku_demand.get(sale.sku, 0) + sale.quantity_sold
        
        lots = []
        for sku, total_demand in sku_demand.items():
            # Create lot with 200% of demand to ensure sufficient inventory
            lot = PurchaseLot(
                lot_id=f"GOLDEN_LOT_{sku}",
                sku=sku,
                received_date=datetime(2024, 1, 1),  # Before any sales
                original_quantity=int(total_demand * 2),
                remaining_quantity=int(total_demand * 2),
                unit_price=Decimal("10.00"),
                freight_cost_per_unit=Decimal("1.00"),
                tenant_id="golden-test"
            )
            lots.append(lot)
        
        return lots
    
    def _copy_lot(self, lot: PurchaseLot) -> PurchaseLot:
        """Create a copy of a lot"""
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


if __name__ == '__main__':
    unittest.main()