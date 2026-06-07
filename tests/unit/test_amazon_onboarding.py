"""Tests for Amazon mock onboarding workflow payload."""
from pathlib import Path

from core.amazon_onboarding import build_amazon_onboarding_mock

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "amazon_sp_api_mock"


def test_amazon_onboarding_mock_builds_safe_operator_payload():
    payload = build_amazon_onboarding_mock(fixture_dir=FIXTURE_DIR, period="2026-05")

    assert payload["connector_mode"] == "mock"
    assert payload["credentials_loaded"] is False
    assert payload["live_api_calls_performed"] == []
    assert payload["mutations_performed"] == []
    assert payload["mock_amazon_connection"]["seller_id"] == "A1FIRSTLOTMOCK"
    assert len(payload["available_skus_inventory"]) == 3
    assert len(payload["recent_sales_movements"]) == 3
    assert payload["other_warehouse_prompt"]["operator_can_upload_sku_counts_csv"] is True
    assert "source_backed_purchase_lots_freight_guidance" in payload
    assert payload["current_in_stock_vs_lot_matching"][0]["total_available"] == 53
    assert payload["proposed_fifo_day_0"]["proposed_start_date"] == "2026-05-01"
    assert payload["proposed_fifo_day_0"]["requires_operator_confirmation"] is True
    assert payload["workflow_timeline"] == [
        "Connect Amazon",
        "Pull SKUs and available inventory",
        "Confirm other warehouses",
        "Upload outside-Amazon SKU/counts",
        "Upload source-backed purchase lots/freight",
        "Match current in-stock to lots",
        "Propose FIFO day 0",
    ]
