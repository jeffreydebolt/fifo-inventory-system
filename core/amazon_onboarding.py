"""Amazon mock onboarding orchestration for FirstLot.

Local/fixture only: no credentials, OAuth, HTTP, Supabase, API, or database writes.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .connectors.amazon_sp_api_mock import AmazonSPAPIMockConnector


def build_amazon_onboarding_mock(*, fixture_dir: str | Path, period: str) -> dict:
    connector = AmazonSPAPIMockConnector(fixture_dir)
    account = connector.account()
    inventory = connector.inventory()
    sales_movements = connector.sales_movements(period=period)
    other_counts = connector.other_warehouse_counts()
    lot_guidance = connector.purchase_lot_guidance()

    other_by_sku = {row["sku"]: int(row.get("available", 0)) for row in other_counts}
    sales_by_sku: dict[str, int] = defaultdict(int)
    for movement in sales_movements:
        sales_by_sku[movement["sku"]] += int(movement.get("quantity_sold", 0))

    inventory_tracking = []
    unmatched_skus = []
    for item in inventory:
        sku = item["sku"]
        amazon_available = int(item.get("amazon_available", 0))
        outside_available = other_by_sku.get(sku, 0)
        total_available = amazon_available + outside_available
        needs_lots = not any(row.get("sku") == sku and row.get("source_documents_needed") for row in lot_guidance)
        if needs_lots:
            unmatched_skus.append(sku)
        inventory_tracking.append(
            {
                "sku": sku,
                "asin": item.get("asin"),
                "title": item.get("title"),
                "amazon_available": amazon_available,
                "other_warehouse_available": outside_available,
                "total_available": total_available,
                "inbound": int(item.get("inbound", 0)),
                "recent_units_sold": sales_by_sku.get(sku, 0),
                "lot_match_status": "needs_source_lots" if needs_lots else "ready_for_matching",
            }
        )

    proposed_day_zero = {
        "proposed_start_date": f"{period}-01",
        "confidence": "review_required",
        "requires_operator_confirmation": True,
        "blockers": [
            "Confirm non-Amazon warehouse counts are complete.",
            "Upload source-backed purchase lots/freight before relying on FIFO COGS.",
            "Verify Amazon sales history covers the rollback window.",
        ],
        "unmatched_skus": unmatched_skus,
        "next_operator_action": "Review inventory counts, upload source-backed purchase lots/freight, then confirm or adjust FIFO day 0.",
    }

    payload = {
        **connector.safety_payload(),
        "period": period,
        "mock_amazon_connection": account,
        "available_skus_inventory": inventory,
        "recent_sales_movements": sales_movements,
        "other_warehouse_prompt": {
            "prompt": "Do you hold inventory outside Amazon FBA/FBM for these SKUs?",
            "fixture_counts": other_counts,
            "operator_can_upload_sku_counts_csv": True,
        },
        "source_backed_purchase_lots_freight_guidance": lot_guidance,
        "current_in_stock_vs_lot_matching": inventory_tracking,
        "proposed_fifo_day_0": proposed_day_zero,
        "workflow_timeline": [
            "Connect Amazon",
            "Pull SKUs and available inventory",
            "Confirm other warehouses",
            "Upload outside-Amazon SKU/counts",
            "Upload source-backed purchase lots/freight",
            "Match current in-stock to lots",
            "Propose FIFO day 0",
        ],
    }
    return payload
