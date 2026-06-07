"""Tests for fixture-backed Amazon SP-API mock connector."""
from pathlib import Path

from core.connectors.amazon_sp_api_mock import AmazonSPAPIMockConnector

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "amazon_sp_api_mock"


def test_amazon_sp_api_mock_connector_reads_fixture_payloads_without_live_calls():
    connector = AmazonSPAPIMockConnector(FIXTURE_DIR)

    assert connector.account()["account_name"] == "FirstLot Mock Seller Central"
    assert [row["sku"] for row in connector.inventory()] == ["CAMERA-KIT", "TRIPOD", "STRAP-BUNDLE"]
    assert [row["sale_id"] for row in connector.sales_movements(period="2026-05")] == [
        "AMZ-2026-05-001",
        "AMZ-2026-05-002",
        "AMZ-2026-05-003",
    ]
    assert connector.safety_payload() == {
        "connector_mode": "mock",
        "credentials_loaded": False,
        "live_api_calls_performed": [],
        "mutations_performed": [],
    }
