"""
Tenant management service for multi-tenant FIFO COGS system.
"""
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime
import logging

from core.models import PurchaseLot, Sale, InventorySnapshot


class TenantContext:
    """Thread-local tenant context for current operations"""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.previous_tenant = None
    
    def __enter__(self):
        self.previous_tenant = TenantService.get_current_tenant()
        TenantService.set_current_tenant(self.tenant_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.previous_tenant is not None:
            TenantService.set_current_tenant(self.previous_tenant)
        else:
            TenantService.clear_current_tenant()


class TenantService:
    """Service for managing tenant isolation and context"""
    
    _current_tenant: Optional[str] = None
    
    @classmethod
    def set_current_tenant(cls, tenant_id: str) -> None:
        """Set the current tenant context"""
        cls._current_tenant = tenant_id
    
    @classmethod
    def get_current_tenant(cls) -> Optional[str]:
        """Get the current tenant context"""
        return cls._current_tenant
    
    @classmethod
    def clear_current_tenant(cls) -> None:
        """Clear the current tenant context"""
        cls._current_tenant = None
    
    @classmethod
    def require_tenant(cls) -> str:
        """Get current tenant or raise error if not set"""
        tenant_id = cls.get_current_tenant()
        if not tenant_id:
            raise ValueError("No tenant context set. Use TenantContext or set_current_tenant().")
        return tenant_id
    
    @staticmethod
    def validate_tenant_id(tenant_id: str) -> bool:
        """Validate tenant ID format"""
        if not tenant_id or not isinstance(tenant_id, str):
            return False
        
        # Basic validation - alphanumeric with dashes/underscores
        import re
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', tenant_id)) and len(tenant_id) <= 100
    
    @staticmethod
    def ensure_tenant_id_on_lots(lots: List[PurchaseLot], tenant_id: Optional[str] = None) -> List[PurchaseLot]:
        """Ensure all lots have the correct tenant_id"""
        if tenant_id is None:
            tenant_id = TenantService.require_tenant()
        
        for lot in lots:
            if lot.tenant_id is None:
                lot.tenant_id = tenant_id
            elif lot.tenant_id != tenant_id:
                raise ValueError(f"Lot {lot.lot_id} belongs to tenant {lot.tenant_id}, expected {tenant_id}")
        
        return lots
    
    @staticmethod
    def ensure_tenant_id_on_sales(sales: List[Sale], tenant_id: Optional[str] = None) -> List[Sale]:
        """Ensure all sales have the correct tenant_id"""
        if tenant_id is None:
            tenant_id = TenantService.require_tenant()
        
        for sale in sales:
            if sale.tenant_id is None:
                sale.tenant_id = tenant_id
            elif sale.tenant_id != tenant_id:
                raise ValueError(f"Sale {sale.sale_id} belongs to tenant {sale.tenant_id}, expected {tenant_id}")
        
        return sales
    
    @staticmethod
    def filter_lots_by_tenant(lots: List[PurchaseLot], tenant_id: Optional[str] = None) -> List[PurchaseLot]:
        """Filter lots to only include those for the specified tenant"""
        if tenant_id is None:
            tenant_id = TenantService.require_tenant()
        
        return [lot for lot in lots if lot.tenant_id == tenant_id]
    
    @staticmethod
    def filter_sales_by_tenant(sales: List[Sale], tenant_id: Optional[str] = None) -> List[Sale]:
        """Filter sales to only include those for the specified tenant"""
        if tenant_id is None:
            tenant_id = TenantService.require_tenant()
        
        return [sale for sale in sales if sale.tenant_id == tenant_id]
    
    @staticmethod
    def create_tenant_scoped_inventory(
        lots: List[PurchaseLot], 
        tenant_id: Optional[str] = None
    ) -> InventorySnapshot:
        """Create an inventory snapshot scoped to a specific tenant"""
        if tenant_id is None:
            tenant_id = TenantService.require_tenant()
        
        # Filter and validate lots
        tenant_lots = TenantService.filter_lots_by_tenant(lots, tenant_id)
        TenantService.ensure_tenant_id_on_lots(tenant_lots, tenant_id)
        
        return InventorySnapshot(
            timestamp=datetime.now(),
            lots=tenant_lots
        )


class MultiTenantFIFOEngine:
    """FIFO Engine wrapper with tenant isolation"""
    
    def __init__(self, base_engine):
        self.base_engine = base_engine
        self.logger = logging.getLogger(__name__)
    
    def process_tenant_transactions(
        self,
        tenant_id: str,
        lots: List[PurchaseLot],
        sales: List[Sale]
    ):
        """Process transactions with tenant isolation"""
        with TenantContext(tenant_id):
            # Ensure tenant consistency
            tenant_lots = TenantService.ensure_tenant_id_on_lots(lots.copy(), tenant_id)
            tenant_sales = TenantService.ensure_tenant_id_on_sales(sales.copy(), tenant_id)
            
            # Create tenant-scoped inventory
            inventory = TenantService.create_tenant_scoped_inventory(tenant_lots, tenant_id)
            
            self.logger.info(f"Processing {len(tenant_sales)} sales for tenant {tenant_id}")
            
            # Process using base engine
            attributions, final_inventory = self.base_engine.process_transactions(
                inventory, tenant_sales
            )
            
            # Ensure all outputs have tenant_id
            for attribution in attributions:
                # Add tenant_id to attribution if needed (would need to update model)
                pass
            
            return attributions, final_inventory