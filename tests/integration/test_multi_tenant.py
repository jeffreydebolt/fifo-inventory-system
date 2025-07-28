"""
Integration tests for multi-tenant functionality.
Tests tenant isolation, cross-tenant security, and rollback mechanisms.
"""
import unittest
import sys
import os
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.models import PurchaseLot, Sale, InventorySnapshot
from core.fifo_engine import FIFOEngine
from services.tenant_service import TenantService, TenantContext, MultiTenantFIFOEngine


class TestMultiTenant(unittest.TestCase):
    
    def setUp(self):
        """Set up test data for multiple tenants"""
        self.engine = FIFOEngine()
        self.multi_tenant_engine = MultiTenantFIFOEngine(self.engine)
        
        # Clear any existing tenant context
        TenantService.clear_current_tenant()
        
        # Create test data for Tenant A
        self.tenant_a_lots = [
            PurchaseLot(
                lot_id="TA_LOT001",
                sku="SKU-A",
                received_date=datetime(2024, 1, 1),
                original_quantity=100,
                remaining_quantity=100,
                unit_price=Decimal("10.00"),
                freight_cost_per_unit=Decimal("1.00"),
                tenant_id="tenant-a"
            ),
            PurchaseLot(
                lot_id="TA_LOT002",
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
                sale_id="TA_SALE001",
                sku="SKU-A",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=30,
                tenant_id="tenant-a"
            ),
            Sale(
                sale_id="TA_SALE002",
                sku="SKU-B",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=20,
                tenant_id="tenant-a"
            )
        ]
        
        # Create test data for Tenant B
        self.tenant_b_lots = [
            PurchaseLot(
                lot_id="TB_LOT001",
                sku="SKU-A",  # Same SKU as Tenant A
                received_date=datetime(2024, 1, 1),
                original_quantity=200,
                remaining_quantity=200,
                unit_price=Decimal("15.00"),  # Different price
                freight_cost_per_unit=Decimal("1.50"),
                tenant_id="tenant-b"
            ),
            PurchaseLot(
                lot_id="TB_LOT002",
                sku="SKU-C",
                received_date=datetime(2024, 1, 10),
                original_quantity=75,
                remaining_quantity=75,
                unit_price=Decimal("25.00"),
                freight_cost_per_unit=Decimal("2.50"),
                tenant_id="tenant-b"
            )
        ]
        
        self.tenant_b_sales = [
            Sale(
                sale_id="TB_SALE001",
                sku="SKU-A",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=50,
                tenant_id="tenant-b"
            ),
            Sale(
                sale_id="TB_SALE002",
                sku="SKU-C",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=25,
                tenant_id="tenant-b"
            )
        ]
    
    def test_tenant_context_manager(self):
        """Test tenant context manager functionality"""
        # Initially no tenant
        self.assertIsNone(TenantService.get_current_tenant())
        
        # Set tenant A context
        with TenantContext("tenant-a"):
            self.assertEqual(TenantService.get_current_tenant(), "tenant-a")
            
            # Nested context
            with TenantContext("tenant-b"):
                self.assertEqual(TenantService.get_current_tenant(), "tenant-b")
            
            # Back to tenant A
            self.assertEqual(TenantService.get_current_tenant(), "tenant-a")
        
        # Back to no tenant
        self.assertIsNone(TenantService.get_current_tenant())
    
    def test_tenant_isolation_processing(self):
        """Test that tenants can't see each other's data"""
        # Process Tenant A
        attributions_a, inventory_a = self.multi_tenant_engine.process_tenant_transactions(
            "tenant-a", self.tenant_a_lots, self.tenant_a_sales
        )
        
        # Process Tenant B
        attributions_b, inventory_b = self.multi_tenant_engine.process_tenant_transactions(
            "tenant-b", self.tenant_b_lots, self.tenant_b_sales
        )
        
        # Verify Tenant A results
        self.assertEqual(len(attributions_a), 2)
        tenant_a_skus = {attr.sku for attr in attributions_a}
        self.assertEqual(tenant_a_skus, {"SKU-A", "SKU-B"})
        
        # Verify Tenant B results
        self.assertEqual(len(attributions_b), 2)
        tenant_b_skus = {attr.sku for attr in attributions_b}
        self.assertEqual(tenant_b_skus, {"SKU-A", "SKU-C"})
        
        # Verify different COGS for same SKU (different costs)
        sku_a_attr_a = next(attr for attr in attributions_a if attr.sku == "SKU-A")
        sku_a_attr_b = next(attr for attr in attributions_b if attr.sku == "SKU-A")
        
        # Tenant A: 30 units @ $11.00 = $330
        # Tenant B: 50 units @ $16.50 = $825
        self.assertEqual(sku_a_attr_a.total_cogs, Decimal("330.00"))
        self.assertEqual(sku_a_attr_b.total_cogs, Decimal("825.00"))
    
    def test_cross_tenant_data_validation(self):
        """Test that tenants can't access each other's lots/sales"""
        # Try to process Tenant A sales with Tenant B lots (should fail)
        with self.assertRaises(ValueError) as context:
            self.multi_tenant_engine.process_tenant_transactions(
                "tenant-a", self.tenant_b_lots, self.tenant_a_sales
            )
        
        self.assertIn("belongs to tenant", str(context.exception))
    
    def test_tenant_scoped_inventory_filtering(self):
        """Test inventory filtering by tenant"""
        # Mix lots from both tenants
        mixed_lots = self.tenant_a_lots + self.tenant_b_lots
        
        # Filter for Tenant A
        with TenantContext("tenant-a"):
            filtered_a = TenantService.filter_lots_by_tenant(mixed_lots)
            self.assertEqual(len(filtered_a), 2)
            self.assertTrue(all(lot.tenant_id == "tenant-a" for lot in filtered_a))
        
        # Filter for Tenant B
        with TenantContext("tenant-b"):
            filtered_b = TenantService.filter_lots_by_tenant(mixed_lots)
            self.assertEqual(len(filtered_b), 2)
            self.assertTrue(all(lot.tenant_id == "tenant-b" for lot in filtered_b))
    
    def test_tenant_id_validation(self):
        """Test tenant ID validation"""
        # Valid tenant IDs
        self.assertTrue(TenantService.validate_tenant_id("tenant-a"))
        self.assertTrue(TenantService.validate_tenant_id("tenant_b"))
        self.assertTrue(TenantService.validate_tenant_id("tenant123"))
        self.assertTrue(TenantService.validate_tenant_id("TENANT-A"))
        
        # Invalid tenant IDs
        self.assertFalse(TenantService.validate_tenant_id(""))
        self.assertFalse(TenantService.validate_tenant_id(None))
        self.assertFalse(TenantService.validate_tenant_id("tenant with spaces"))
        self.assertFalse(TenantService.validate_tenant_id("tenant@special"))
        self.assertFalse(TenantService.validate_tenant_id("a" * 101))  # Too long
    
    def test_lots_without_tenant_id_assignment(self):
        """Test automatic tenant_id assignment for lots without one"""
        # Create lots without tenant_id
        lots_no_tenant = [
            PurchaseLot(
                lot_id="NT_LOT001",
                sku="SKU-TEST",
                received_date=datetime(2024, 1, 1),
                original_quantity=100,
                remaining_quantity=100,
                unit_price=Decimal("10.00"),
                freight_cost_per_unit=Decimal("1.00"),
                tenant_id=None
            )
        ]
        
        with TenantContext("test-tenant"):
            # Should assign tenant_id automatically
            assigned_lots = TenantService.ensure_tenant_id_on_lots(lots_no_tenant)
            self.assertEqual(assigned_lots[0].tenant_id, "test-tenant")
    
    def test_sales_without_tenant_id_assignment(self):
        """Test automatic tenant_id assignment for sales without one"""
        # Create sales without tenant_id
        sales_no_tenant = [
            Sale(
                sale_id="NT_SALE001",
                sku="SKU-TEST",
                sale_date=datetime(2024, 2, 1),
                quantity_sold=50,
                tenant_id=None
            )
        ]
        
        with TenantContext("test-tenant"):
            # Should assign tenant_id automatically
            assigned_sales = TenantService.ensure_tenant_id_on_sales(sales_no_tenant)
            self.assertEqual(assigned_sales[0].tenant_id, "test-tenant")
    
    def test_require_tenant_context(self):
        """Test that operations requiring tenant context fail without it"""
        # Clear tenant context
        TenantService.clear_current_tenant()
        
        # Should raise error when no tenant is set
        with self.assertRaises(ValueError) as context:
            TenantService.require_tenant()
        
        self.assertIn("No tenant context set", str(context.exception))
    
    def test_concurrent_tenant_processing_simulation(self):
        """Test processing for multiple tenants (simulates concurrent processing)"""
        results = {}
        
        # Process each tenant in sequence (simulating separate threads/requests)
        for tenant_id, lots, sales in [
            ("tenant-a", self.tenant_a_lots, self.tenant_a_sales),
            ("tenant-b", self.tenant_b_lots, self.tenant_b_sales)
        ]:
            with TenantContext(tenant_id):
                attributions, inventory = self.multi_tenant_engine.process_tenant_transactions(
                    tenant_id, lots, sales
                )
                results[tenant_id] = {
                    'attributions': attributions,
                    'inventory': inventory,
                    'total_cogs': sum(attr.total_cogs for attr in attributions)
                }
        
        # Verify each tenant has correct results
        self.assertEqual(len(results["tenant-a"]["attributions"]), 2)
        self.assertEqual(len(results["tenant-b"]["attributions"]), 2)
        
        # Different total COGS due to different pricing
        self.assertNotEqual(
            results["tenant-a"]["total_cogs"],
            results["tenant-b"]["total_cogs"]
        )
        
        # Verify specific calculations
        # Tenant A: SKU-A (30 @ $11) + SKU-B (20 @ $22) = $330 + $440 = $770
        # Tenant B: SKU-A (50 @ $16.50) + SKU-C (25 @ $27.50) = $825 + $687.50 = $1512.50
        self.assertEqual(results["tenant-a"]["total_cogs"], Decimal("770.00"))
        self.assertEqual(results["tenant-b"]["total_cogs"], Decimal("1512.50"))


if __name__ == '__main__':
    unittest.main()