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
    assert payload["current_in_stock_vs_lot_matching"][0]["amazon_reserved"] == 3
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


def test_day_zero_proposal_blocks_until_inventory_is_source_backed():
    payload = build_amazon_onboarding_mock(fixture_dir=FIXTURE_DIR, period="2026-05")
    proposal = payload["proposed_fifo_day_0"]

    assert proposal["confidence"] == "blocked_review_required"
    assert proposal["rule_draft"].startswith("Earliest close month start")
    assert proposal["current_units_to_reconcile"] == 92
    assert proposal["source_backed_units"] == 65
    assert proposal["source_support_ratio"] == 0.7065
    assert proposal["readiness_checklist"][0] == {
        "label": "Amazon sales history covers rollback window",
        "status": "needs_operator_confirmation",
    }
    assert "STRAP-BUNDLE: Freight allocation is missing." in proposal["blockers"]
    assert "LENS-CAP-ONLY: outside-Amazon SKU must be mapped, archived, or excluded." in proposal["blockers"]


def test_unmatched_inventory_explains_quantity_gaps_and_operator_actions():
    payload = build_amazon_onboarding_mock(fixture_dir=FIXTURE_DIR, period="2026-05")
    unmatched_by_sku = {
        row["sku"]: row for row in payload["proposed_fifo_day_0"]["unmatched_inventory"]
    }

    assert unmatched_by_sku["CAMERA-KIT"]["quantity_gap"] == 6
    assert "Freight allocation is partial." in unmatched_by_sku["CAMERA-KIT"]["blockers"]
    assert unmatched_by_sku["CAMERA-KIT"]["source_documents_needed"] == [
        "supplier invoice",
        "freight bill",
    ]
    assert unmatched_by_sku["TRIPOD"]["quantity_gap"] == 0
    assert unmatched_by_sku["TRIPOD"]["blockers"] == [
        "Other-warehouse count status is needs_supervisor_signoff."
    ]
    assert unmatched_by_sku["LENS-CAP-ONLY"]["operator_guidance"].startswith("Map, archive")


def test_source_backed_purchase_lot_and_freight_guidance_feeds_reconciliation_rows():
    payload = build_amazon_onboarding_mock(fixture_dir=FIXTURE_DIR, period="2026-05")
    rows = {row["sku"]: row for row in payload["current_in_stock_vs_lot_matching"]}

    assert rows["CAMERA-KIT"]["draft_source_units_available"] == 47
    assert rows["CAMERA-KIT"]["source_support_gap"] == 6
    assert rows["CAMERA-KIT"]["supported_lot_ids"] == ["PO-1842-CAM-01", "PO-1904-CAM-02"]
    assert rows["CAMERA-KIT"]["draft_inventory_value"] == 669.75
    assert rows["TRIPOD"]["lot_match_status"] == "blocked"
    assert rows["STRAP-BUNDLE"]["reconciliation_action"] == "Resolve blockers before day 0"


def test_rollback_reconstruction_estimates_day_zero_units_from_current_sales_and_receipts():
    payload = build_amazon_onboarding_mock(fixture_dir=FIXTURE_DIR, period="2026-05")
    rollback = {
        row["sku"]: row for row in payload["proposed_fifo_day_0"]["rollback_reconstruction"]
    }

    assert rollback["CAMERA-KIT"] == {
        "sku": "CAMERA-KIT",
        "current_units": 53,
        "period_sales_units": 5,
        "draft_receipts_in_period": 12,
        "estimated_units_at_period_start": 46,
        "source_backed_start_units": 46,
        "rollback_status": "blocked",
        "rollback_note": "Fixture-only rollback estimate; operator must confirm sales history, purchase lots, freight, and counts.",
    }
    assert rollback["TRIPOD"]["rollback_status"] == "blocked"
    assert rollback["STRAP-BUNDLE"]["estimated_units_at_period_start"] == -9
    assert rollback["STRAP-BUNDLE"]["rollback_note"].startswith("Receipts exceed current plus sales")
