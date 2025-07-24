"""
Unit tests for the FIFO engine core logic.
Tests ensure parity with the existing fifo_calculator_enhanced.py behavior.
"""
import unittest
from datetime import datetime
from decimal import Decimal
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.models import PurchaseLot, Sale, InventorySnapshot
from core.fifo_engine import FIFOEngine


class TestFIFOEngine(unittest.TestCase):
    
    def setUp(self):
        """Set up test data"""
        self.engine = FIFOEngine()
        
        # Create test purchase lots
        self.test_lots = [
            PurchaseLot(
                lot_id="LOT001",
                sku="SKU-A",
                received_date=datetime(2024, 1, 1),
                original_quantity=100,
                remaining_quantity=100,
                unit_price=Decimal("10.00"),
                freight_cost_per_unit=Decimal("1.00")
            ),
            PurchaseLot(
                lot_id="LOT002",
                sku="SKU-A",
                received_date=datetime(2024, 1, 15),
                original_quantity=50,
                remaining_quantity=50,
                unit_price=Decimal("12.00"),
                freight_cost_per_unit=Decimal("1.50")
            ),
            PurchaseLot(
                lot_id="LOT003",
                sku="SKU-B",
                received_date=datetime(2024, 1, 10),
                original_quantity=200,
                remaining_quantity=200,
                unit_price=Decimal("5.00"),
                freight_cost_per_unit=Decimal("0.50")
            )
        ]
        
        self.initial_inventory = InventorySnapshot(
            timestamp=datetime.now(),
            lots=self.test_lots
        )
    
    def test_simple_fifo_allocation(self):
        """Test basic FIFO allocation from oldest lot first"""
        sales = [
            Sale(
                sale_id="SALE001",
                sku="SKU-A",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=80
            )
        ]
        
        attributions, final_inventory = self.engine.process_transactions(
            self.initial_inventory, sales
        )
        
        # Verify we got one attribution
        self.assertEqual(len(attributions), 1)
        attribution = attributions[0]
        
        # Verify correct quantity and SKU
        self.assertEqual(attribution.sku, "SKU-A")
        self.assertEqual(attribution.quantity_sold, 80)
        
        # Verify allocation came from LOT001 (oldest)
        self.assertEqual(len(attribution.allocations), 1)
        self.assertEqual(attribution.allocations[0].lot_id, "LOT001")
        self.assertEqual(attribution.allocations[0].quantity, 80)
        
        # Verify COGS calculation (80 units * $11.00)
        expected_cogs = Decimal("880.00")
        self.assertEqual(attribution.total_cogs, expected_cogs)
        
        # Verify inventory was updated
        lot1 = next(lot for lot in final_inventory.lots if lot.lot_id == "LOT001")
        self.assertEqual(lot1.remaining_quantity, 20)
    
    def test_multi_lot_allocation(self):
        """Test allocation spanning multiple lots"""
        sales = [
            Sale(
                sale_id="SALE002",
                sku="SKU-A",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=120
            )
        ]
        
        attributions, final_inventory = self.engine.process_transactions(
            self.initial_inventory, sales
        )
        
        attribution = attributions[0]
        
        # Verify allocation came from both lots
        self.assertEqual(len(attribution.allocations), 2)
        
        # First allocation should exhaust LOT001
        self.assertEqual(attribution.allocations[0].lot_id, "LOT001")
        self.assertEqual(attribution.allocations[0].quantity, 100)
        
        # Second allocation should take 20 from LOT002
        self.assertEqual(attribution.allocations[1].lot_id, "LOT002")
        self.assertEqual(attribution.allocations[1].quantity, 20)
        
        # Verify total COGS
        expected_cogs = (100 * Decimal("11.00")) + (20 * Decimal("13.50"))
        self.assertEqual(attribution.total_cogs, expected_cogs)
    
    def test_return_processing(self):
        """Test that returns add inventory back to oldest lot"""
        # First do a sale to reduce inventory
        sales = [
            Sale(
                sale_id="SALE003",
                sku="SKU-A",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=50
            ),
            Sale(
                sale_id="RETURN001",
                sku="SKU-A",
                sale_date=datetime(2024, 2, 5),
                quantity_sold=-20  # Negative indicates return
            )
        ]
        
        attributions, final_inventory = self.engine.process_transactions(
            self.initial_inventory, sales
        )
        
        # Only regular sales should have attributions
        self.assertEqual(len(attributions), 1)
        
        # Verify inventory reflects sale minus return
        lot1 = next(lot for lot in final_inventory.lots if lot.lot_id == "LOT001")
        # Started with 100, sold 50, returned 20 = 70
        self.assertEqual(lot1.remaining_quantity, 70)
    
    def test_insufficient_inventory_error(self):
        """Test handling of insufficient inventory"""
        sales = [
            Sale(
                sale_id="SALE004",
                sku="SKU-A",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=200  # More than available (150 total)
            )
        ]
        
        attributions, final_inventory = self.engine.process_transactions(
            self.initial_inventory, sales
        )
        
        # Should have no attributions due to insufficient inventory
        self.assertEqual(len(attributions), 0)
        
        # Should have validation error
        errors = self.engine.get_validation_errors()
        self.assertTrue(any(e.error_type == "INSUFFICIENT_INVENTORY" for e in errors))
    
    def test_sale_before_inventory_error(self):
        """Test validation of sales before inventory received"""
        sales = [
            Sale(
                sale_id="SALE005",
                sku="SKU-A",
                sale_date=datetime(2023, 12, 1),  # Before any lots received
                quantity_sold=10
            )
        ]
        
        attributions, final_inventory = self.engine.process_transactions(
            self.initial_inventory, sales
        )
        
        # Should have no attributions
        self.assertEqual(len(attributions), 0)
        
        # Should have validation error
        errors = self.engine.get_validation_errors()
        self.assertTrue(any(e.error_type == "NO_INVENTORY" for e in errors))
    
    def test_multiple_skus(self):
        """Test processing sales for multiple SKUs"""
        sales = [
            Sale(
                sale_id="SALE006",
                sku="SKU-A",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=30
            ),
            Sale(
                sale_id="SALE007",
                sku="SKU-B",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=50
            )
        ]
        
        attributions, final_inventory = self.engine.process_transactions(
            self.initial_inventory, sales
        )
        
        # Should have two attributions
        self.assertEqual(len(attributions), 2)
        
        # Verify each SKU was processed correctly
        sku_a_attr = next(a for a in attributions if a.sku == "SKU-A")
        sku_b_attr = next(a for a in attributions if a.sku == "SKU-B")
        
        self.assertEqual(sku_a_attr.total_cogs, 30 * Decimal("11.00"))
        self.assertEqual(sku_b_attr.total_cogs, 50 * Decimal("5.50"))
    
    def test_cogs_summary_calculation(self):
        """Test COGS summary generation"""
        sales = [
            Sale(
                sale_id="SALE008",
                sku="SKU-A",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=30
            ),
            Sale(
                sale_id="SALE009",
                sku="SKU-A",
                sale_date=datetime(2024, 2, 15),
                quantity_sold=40
            ),
            Sale(
                sale_id="SALE010",
                sku="SKU-A",
                sale_date=datetime(2024, 3, 1),
                quantity_sold=50
            )
        ]
        
        attributions, _ = self.engine.process_transactions(
            self.initial_inventory, sales
        )
        
        summaries = self.engine.calculate_summary(attributions)
        
        # Should have 2 summaries (Feb and Mar)
        self.assertEqual(len(summaries), 2)
        
        # Verify February summary
        feb_summary = next(s for s in summaries if s.period == "2024-02")
        self.assertEqual(feb_summary.total_quantity_sold, 70)
        self.assertEqual(feb_summary.total_cogs, 70 * Decimal("11.00"))
        
        # Verify March summary  
        mar_summary = next(s for s in summaries if s.period == "2024-03")
        self.assertEqual(mar_summary.total_quantity_sold, 50)
        # 30 from LOT001 at $11, 20 from LOT002 at $13.50
        expected_march_cogs = (30 * Decimal("11.00")) + (20 * Decimal("13.50"))
        self.assertEqual(mar_summary.total_cogs, expected_march_cogs)


if __name__ == '__main__':
    unittest.main()