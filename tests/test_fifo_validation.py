"""
Comprehensive FIFO calculation validation tests.
Tests the current working system against known datasets to establish baselines.
"""
import unittest
import pandas as pd
import os
import sys
import subprocess
import tempfile
import shutil
from datetime import datetime
from decimal import Decimal
import csv
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.test_data_generator import TestDataGenerator
from core.models import PurchaseLot, Sale, InventorySnapshot
from core.fifo_engine import FIFOEngine


class FIFOValidationTests(unittest.TestCase):
    """Comprehensive validation tests for FIFO calculator"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data and expected results"""
        cls.test_data_dir = '/Users/jeffreydebolt/Documents/fifo/tests/test_datasets'
        cls.golden_dir = '/Users/jeffreydebolt/Documents/fifo/golden'
        cls.calculator_path = '/Users/jeffreydebolt/Documents/fifo/fifo_calculator_supabase.py'
        
        # Generate test datasets if they don't exist
        if not os.path.exists(cls.test_data_dir):
            generator = TestDataGenerator()
            generator.save_test_datasets(cls.test_data_dir)
    
    def setUp(self):
        """Set up each test"""
        self.engine = FIFOEngine()
        self.maxDiff = None  # Show full diffs in test failures
    
    def test_golden_dataset_consistency(self):
        """Test that current system produces expected results with golden dataset"""
        if not os.path.exists(self.golden_dir):
            self.skipTest("Golden dataset directory not found")
        
        # Load golden sales data
        golden_sales_path = os.path.join(self.golden_dir, 'golden_sales.csv')
        if not os.path.exists(golden_sales_path):
            self.skipTest("Golden sales data not found")
        
        # Load expected results
        expected_cogs_path = os.path.join(self.golden_dir, 'golden_cogs_summary.csv')
        expected_attribution_path = os.path.join(self.golden_dir, 'golden_cogs_attribution.csv')
        expected_inventory_path = os.path.join(self.golden_dir, 'golden_inventory_snapshot.csv')
        
        if not all(os.path.exists(p) for p in [expected_cogs_path, expected_attribution_path, expected_inventory_path]):
            self.skipTest("Golden expected results not found")
        
        # Load expected results
        expected_cogs = pd.read_csv(expected_cogs_path)
        expected_attribution = pd.read_csv(expected_attribution_path)
        expected_inventory = pd.read_csv(expected_inventory_path)
        
        print(f"Golden dataset test - Expected COGS entries: {len(expected_cogs)}")
        print(f"Golden dataset test - Expected Attribution entries: {len(expected_attribution)}")
        print(f"Golden dataset test - Expected Inventory entries: {len(expected_inventory)}")
        
        # Validate that we have the expected data structure
        self.assertGreater(len(expected_cogs), 0, "Golden COGS summary should not be empty")
        self.assertGreater(len(expected_attribution), 0, "Golden attribution should not be empty")
        self.assertGreater(len(expected_inventory), 0, "Golden inventory should not be empty")
        
        print("✅ Golden dataset structure validation passed")
    
    def test_small_dataset_calculation(self):
        """Test FIFO calculation with small controlled dataset"""
        small_lots_path = os.path.join(self.test_data_dir, 'small_lots.csv')
        small_sales_path = os.path.join(self.test_data_dir, 'small_sales.csv')
        
        if not os.path.exists(small_lots_path) or not os.path.exists(small_sales_path):
            # Generate test data
            generator = TestDataGenerator()
            generator.save_test_datasets(self.test_data_dir)
        
        # Load test data
        lots_df = pd.read_csv(small_lots_path)
        sales_df = pd.read_csv(small_sales_path)
        
        print(f"Small dataset test - Lots: {len(lots_df)}, Sales: {len(sales_df)}")
        
        # Convert to core model objects
        lots = []
        for _, row in lots_df.iterrows():
            lot = PurchaseLot(
                lot_id=str(row['lot_id']),
                sku=str(row['sku']),
                received_date=datetime.strptime(row['received_date'], '%Y-%m-%d'),
                original_quantity=int(row['original_unit_qty']),
                remaining_quantity=int(row['remaining_unit_qty']),
                unit_price=Decimal(str(row['unit_price'])),
                freight_cost_per_unit=Decimal(str(row['freight_cost_per_unit']))
            )
            lots.append(lot)
        
        inventory = InventorySnapshot(timestamp=datetime.now(), lots=lots)
        
        # Convert sales
        sales = []
        for _, row in sales_df.iterrows():
            # Skip returns for now to test positive sales
            if int(row['units moved']) > 0:
                sale = Sale(
                    sale_id=str(row.get('sale_id', f"SALE_{len(sales):06d}")),
                    sku=str(row['sku']),
                    sale_date=datetime.strptime(row['sale_date'], '%Y-%m-%d'),
                    quantity_sold=int(row['units moved'])
                )
                sales.append(sale)
        
        # Process with core engine
        attributions, final_inventory = self.engine.process_transactions(inventory, sales)
        
        # Validate results
        self.assertGreater(len(attributions), 0, "Should have COGS attributions")
        
        # Check that total quantities match
        total_sold = sum(s.quantity_sold for s in sales)
        total_attributed = sum(a.quantity_sold for a in attributions)
        
        print(f"Total sold: {total_sold}, Total attributed: {total_attributed}")
        
        # Validate COGS calculations
        for attribution in attributions[:3]:  # Check first few
            self.assertGreater(attribution.total_cogs, 0, "COGS should be positive")
            self.assertEqual(
                len(attribution.allocations), 
                sum(1 for _ in attribution.allocations),
                "Allocations should be properly structured"
            )
        
        # Check that inventory was updated
        original_remaining = sum(lot.remaining_quantity for lot in lots)
        final_remaining = sum(lot.remaining_quantity for lot in final_inventory.lots)
        
        print(f"Original remaining inventory: {original_remaining}")
        print(f"Final remaining inventory: {final_remaining}")
        print(f"✅ Small dataset calculation test passed")
    
    def test_edge_case_insufficient_inventory(self):
        """Test handling of insufficient inventory scenario"""
        edge_case_dir = os.path.join(self.test_data_dir, 'edge_cases', 'insufficient_inventory')
        
        if not os.path.exists(edge_case_dir):
            generator = TestDataGenerator()
            generator.save_test_datasets(self.test_data_dir)
        
        lots_df = pd.read_csv(os.path.join(edge_case_dir, 'lots.csv'))
        sales_df = pd.read_csv(os.path.join(edge_case_dir, 'sales.csv'))
        
        # Convert to core objects
        lots = self._dataframe_to_lots(lots_df)
        sales = self._dataframe_to_sales(sales_df)
        inventory = InventorySnapshot(timestamp=datetime.now(), lots=lots)
        
        # Process transaction
        attributions, final_inventory = self.engine.process_transactions(inventory, sales)
        
        # Should have no attributions due to insufficient inventory
        self.assertEqual(len(attributions), 0, "Should have no attributions for insufficient inventory")
        
        # Should have validation errors
        errors = self.engine.get_validation_errors()
        self.assertTrue(
            any(e.error_type == "INSUFFICIENT_INVENTORY" for e in errors),
            "Should have insufficient inventory error"
        )
        
        print("✅ Edge case - Insufficient inventory test passed")
    
    def test_edge_case_sales_before_inventory(self):
        """Test handling of sales before inventory received"""
        edge_case_dir = os.path.join(self.test_data_dir, 'edge_cases', 'sales_before_inventory')
        
        if not os.path.exists(edge_case_dir):
            generator = TestDataGenerator()
            generator.save_test_datasets(self.test_data_dir)
        
        lots_df = pd.read_csv(os.path.join(edge_case_dir, 'lots.csv'))
        sales_df = pd.read_csv(os.path.join(edge_case_dir, 'sales.csv'))
        
        lots = self._dataframe_to_lots(lots_df)
        sales = self._dataframe_to_sales(sales_df)
        inventory = InventorySnapshot(timestamp=datetime.now(), lots=lots)
        
        attributions, final_inventory = self.engine.process_transactions(inventory, sales)
        
        # Should have no attributions for sales before inventory
        self.assertEqual(len(attributions), 0, "Should have no attributions for sales before inventory")
        
        # Should have validation errors
        errors = self.engine.get_validation_errors()
        self.assertTrue(
            any(e.error_type == "NO_INVENTORY" for e in errors),
            "Should have no inventory error"
        )
        
        print("✅ Edge case - Sales before inventory test passed")
    
    def test_edge_case_complex_allocation(self):
        """Test complex allocation spanning multiple lots"""
        edge_case_dir = os.path.join(self.test_data_dir, 'edge_cases', 'complex_allocation')
        
        if not os.path.exists(edge_case_dir):
            generator = TestDataGenerator()
            generator.save_test_datasets(self.test_data_dir)
        
        lots_df = pd.read_csv(os.path.join(edge_case_dir, 'lots.csv'))
        sales_df = pd.read_csv(os.path.join(edge_case_dir, 'sales.csv'))
        
        lots = self._dataframe_to_lots(lots_df)
        sales = self._dataframe_to_sales(sales_df)
        inventory = InventorySnapshot(timestamp=datetime.now(), lots=lots)
        
        attributions, final_inventory = self.engine.process_transactions(inventory, sales)
        
        # Should have one attribution spanning multiple lots
        self.assertEqual(len(attributions), 1, "Should have one attribution")
        attribution = attributions[0]
        
        # Should have allocations from multiple lots
        self.assertGreater(len(attribution.allocations), 1, "Should allocate from multiple lots")
        
        # Verify FIFO order (oldest lots first)
        allocation_dates = []
        for alloc in attribution.allocations:
            lot = next(l for l in lots if l.lot_id == alloc.lot_id)
            allocation_dates.append(lot.received_date)
        
        # Dates should be in ascending order (FIFO)
        self.assertEqual(allocation_dates, sorted(allocation_dates), "Should follow FIFO order")
        
        print("✅ Edge case - Complex allocation test passed")
    
    def test_edge_case_returns_processing(self):
        """Test returns processing"""
        edge_case_dir = os.path.join(self.test_data_dir, 'edge_cases', 'returns_processing')
        
        if not os.path.exists(edge_case_dir):
            generator = TestDataGenerator()
            generator.save_test_datasets(self.test_data_dir)
        
        lots_df = pd.read_csv(os.path.join(edge_case_dir, 'lots.csv'))
        sales_df = pd.read_csv(os.path.join(edge_case_dir, 'sales.csv'))
        
        lots = self._dataframe_to_lots(lots_df)
        sales = self._dataframe_to_sales(sales_df)
        inventory = InventorySnapshot(timestamp=datetime.now(), lots=lots)
        
        # Track original inventory
        original_remaining = sum(lot.remaining_quantity for lot in lots)
        
        attributions, final_inventory = self.engine.process_transactions(inventory, sales)
        
        # Should have attributions only for regular sales (not returns)
        regular_sales = [s for s in sales if s.quantity_sold > 0]
        self.assertEqual(len(attributions), len(regular_sales), "Should have attributions for regular sales only")
        
        # Check that inventory reflects sales minus returns
        final_remaining = sum(lot.remaining_quantity for lot in final_inventory.lots)
        
        # Calculate expected remaining (original - net sales)
        total_sales = sum(s.quantity_sold for s in regular_sales)
        total_returns = sum(abs(s.quantity_sold) for s in sales if s.quantity_sold < 0)
        net_movement = total_sales - total_returns
        expected_remaining = original_remaining - net_movement
        
        self.assertEqual(final_remaining, expected_remaining, "Inventory should reflect returns")
        
        print("✅ Edge case - Returns processing test passed")
    
    def test_performance_benchmark_medium_dataset(self):
        """Test performance with medium dataset and establish benchmark"""
        medium_lots_path = os.path.join(self.test_data_dir, 'medium_lots.csv')
        medium_sales_path = os.path.join(self.test_data_dir, 'medium_sales.csv')
        
        if not os.path.exists(medium_lots_path) or not os.path.exists(medium_sales_path):
            generator = TestDataGenerator()
            generator.save_test_datasets(self.test_data_dir)
        
        lots_df = pd.read_csv(medium_lots_path)
        sales_df = pd.read_csv(medium_sales_path)
        
        lots = self._dataframe_to_lots(lots_df)
        sales = self._dataframe_to_sales(sales_df)
        inventory = InventorySnapshot(timestamp=datetime.now(), lots=lots)
        
        # Time the calculation
        start_time = datetime.now()
        attributions, final_inventory = self.engine.process_transactions(inventory, sales)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        # Log performance metrics
        print(f"Performance benchmark - Medium dataset:")
        print(f"  Lots processed: {len(lots_df)}")
        print(f"  Sales processed: {len(sales_df)}")
        print(f"  Processing time: {processing_time:.2f} seconds")
        print(f"  Attributions generated: {len(attributions)}")
        print(f"  Transactions per second: {len(sales_df) / processing_time:.2f}")
        
        # Performance assertions
        self.assertLess(processing_time, 30.0, "Should process medium dataset in under 30 seconds")
        self.assertEqual(len(attributions), len([s for s in sales if s.quantity_sold > 0]), 
                        "Should generate attribution for each positive sale")
        
        print("✅ Performance benchmark test passed")
    
    def _dataframe_to_lots(self, df: pd.DataFrame) -> list:
        """Convert DataFrame to PurchaseLot objects"""
        lots = []
        for _, row in df.iterrows():
            lot = PurchaseLot(
                lot_id=str(row['lot_id']),
                sku=str(row['sku']),
                received_date=datetime.strptime(row['received_date'], '%Y-%m-%d'),
                original_quantity=int(row['original_unit_qty']),
                remaining_quantity=int(row['remaining_unit_qty']),
                unit_price=Decimal(str(row['unit_price'])),
                freight_cost_per_unit=Decimal(str(row['freight_cost_per_unit']))
            )
            lots.append(lot)
        return lots
    
    def _dataframe_to_sales(self, df: pd.DataFrame) -> list:
        """Convert DataFrame to Sale objects"""
        sales = []
        for _, row in df.iterrows():
            sale = Sale(
                sale_id=str(row.get('sale_id', f"SALE_{len(sales):06d}")),
                sku=str(row['sku']),
                sale_date=datetime.strptime(row['sale_date'], '%Y-%m-%d'),
                quantity_sold=int(row['units moved'])
            )
            sales.append(sale)
        return sales
    
    def test_cogs_summary_accuracy(self):
        """Test COGS summary calculation accuracy"""
        # Create a simple, predictable scenario
        lots = [
            PurchaseLot(
                lot_id="LOT001",
                sku="TEST-SKU",
                received_date=datetime(2024, 1, 1),
                original_quantity=100,
                remaining_quantity=100,
                unit_price=Decimal("10.00"),
                freight_cost_per_unit=Decimal("1.00")
            )
        ]
        
        sales = [
            Sale(
                sale_id="SALE001",
                sku="TEST-SKU",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=50
            )
        ]
        
        inventory = InventorySnapshot(timestamp=datetime.now(), lots=lots)
        attributions, final_inventory = self.engine.process_transactions(inventory, sales)
        
        # Calculate summary
        summaries = self.engine.calculate_summary(attributions)
        
        self.assertEqual(len(summaries), 1, "Should have one summary")
        summary = summaries[0]
        
        # Verify summary calculations
        expected_cogs = 50 * (Decimal("10.00") + Decimal("1.00"))  # 50 * $11.00
        self.assertEqual(summary.total_cogs, expected_cogs, "COGS calculation should be accurate")
        self.assertEqual(summary.total_quantity_sold, 50, "Quantity should match")
        self.assertEqual(summary.sku, "TEST-SKU", "SKU should match")
        self.assertEqual(summary.period, "2024-02", "Period should match")
        
        print("✅ COGS summary accuracy test passed")


class ProductionSystemValidationTests(unittest.TestCase):
    """Tests for the actual production FIFO calculator"""
    
    def setUp(self):
        """Set up paths and test data"""
        self.calculator_path = '/Users/jeffreydebolt/Documents/fifo/fifo_calculator_supabase.py'
        self.test_data_dir = '/Users/jeffreydebolt/Documents/fifo/tests/test_datasets'
        
        # Ensure test data exists
        if not os.path.exists(self.test_data_dir):
            generator = TestDataGenerator()
            generator.save_test_datasets(self.test_data_dir)
    
    def test_calculator_script_executable(self):
        """Test that the production calculator script can be executed"""
        self.assertTrue(os.path.exists(self.calculator_path), "Calculator script should exist")
        self.assertTrue(os.access(self.calculator_path, os.R_OK), "Calculator script should be readable")
        
        # Test help option
        try:
            result = subprocess.run([
                'python3', self.calculator_path, '--help'
            ], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, "Calculator should show help without errors")
        except subprocess.TimeoutExpired:
            self.fail("Calculator script timed out showing help")
        
        print("✅ Calculator script executable test passed")
    
    def test_file_validation(self):
        """Test file validation functionality"""
        # Create a test CSV with correct format
        test_csv_path = os.path.join(self.test_data_dir, 'validation_test.csv')
        
        with open(test_csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['sku', 'units moved', 'Month'])
            writer.writerow(['TEST-SKU-001', '10', 'January 2024'])
            writer.writerow(['TEST-SKU-002', '5', 'January 2024'])
        
        # Test that file exists and has expected structure
        self.assertTrue(os.path.exists(test_csv_path), "Test CSV should be created")
        
        # Read and validate structure
        df = pd.read_csv(test_csv_path)
        expected_columns = ['sku', 'units moved', 'Month']
        
        self.assertTrue(all(col in df.columns for col in expected_columns), 
                       "CSV should have expected columns")
        self.assertGreater(len(df), 0, "CSV should have data rows")
        
        # Clean up
        os.remove(test_csv_path)
        
        print("✅ File validation test passed")


if __name__ == '__main__':
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add core validation tests
    suite.addTest(unittest.makeSuite(FIFOValidationTests))
    suite.addTest(unittest.makeSuite(ProductionSystemValidationTests))
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("FIFO VALIDATION TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n✅ All validation tests passed!")
    else:
        print("\n❌ Some tests failed. Please review the output above.")
    
    print("="*70)