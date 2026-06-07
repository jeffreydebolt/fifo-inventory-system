"""Amazon SP-API onboarding contract shapes.

These dataclasses define the payload FirstLot expects from a future live Amazon
connector. They are local-only contracts today; importing this module performs no
credential loading and no network work.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AmazonAccount:
    seller_id: str
    marketplace_id: str
    account_name: str
    connected_at: str


@dataclass(frozen=True)
class AmazonInventoryItem:
    sku: str
    asin: str
    title: str
    amazon_available: int
    inbound: int = 0


@dataclass(frozen=True)
class AmazonSalesMovement:
    sale_id: str
    sku: str
    sale_date: str
    quantity_sold: int
    marketplace: str


@dataclass(frozen=True)
class AmazonConnectorSafety:
    connector_mode: str = "mock"
    credentials_loaded: bool = False
    live_api_calls_performed: list[str] = field(default_factory=list)
    mutations_performed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "connector_mode": self.connector_mode,
            "credentials_loaded": self.credentials_loaded,
            "live_api_calls_performed": self.live_api_calls_performed,
            "mutations_performed": self.mutations_performed,
        }
