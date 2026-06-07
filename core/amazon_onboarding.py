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
    other_status_by_sku = {row["sku"]: row.get("count_status", "fixture_count") for row in other_counts}
    amazon_skus = {row["sku"] for row in inventory}
    guidance_by_sku = {row["sku"]: row for row in lot_guidance}
    sales_by_sku: dict[str, int] = defaultdict(int)
    for movement in sales_movements:
        sales_by_sku[movement["sku"]] += int(movement.get("quantity_sold", 0))

    inventory_tracking = []
    unmatched_inventory = []
    day_zero_blockers = [
        "Verify Amazon sales history covers the rollback window.",
        "Approve the proposed FIFO day 0 before any accounting packet is relied on.",
    ]
    for item in inventory:
        sku = item["sku"]
        amazon_available = int(item.get("amazon_available", 0))
        reserved = int(item.get("reserved", 0))
        outside_available = other_by_sku.get(sku, 0)
        total_available = amazon_available + outside_available
        guidance = guidance_by_sku.get(sku, {})
        source_units = int(guidance.get("draft_source_units_available") or 0)
        unit_cost = float(guidance.get("draft_unit_cost") or 0)
        support_gap = max(total_available - source_units, 0)
        lot_status = str(guidance.get("status", "missing_source_support"))
        freight_status = str(guidance.get("freight_allocation_status", "missing"))
        count_status = other_status_by_sku.get(sku, "missing_non_amazon_count")
        blockers = []
        if support_gap:
            blockers.append(f"Need source-backed lots for {support_gap} more unit(s).")
        if freight_status in {"missing", "partial"}:
            blockers.append(f"Freight allocation is {freight_status}.")
        if count_status not in {"operator_attested", "fixture_count"}:
            blockers.append(f"Other-warehouse count status is {count_status}.")
        if not guidance:
            blockers.append("Purchase lot/freight guidance is missing for this SKU.")
        if blockers:
            unmatched_inventory.append(
                {
                    "sku": sku,
                    "quantity_gap": support_gap,
                    "blockers": blockers,
                    "operator_guidance": "Upload/approve source docs and counts before accepting day 0 for this SKU.",
                }
            )
            day_zero_blockers.extend([f"{sku}: {blocker}" for blocker in blockers])
        inventory_tracking.append(
            {
                "sku": sku,
                "asin": item.get("asin"),
                "title": item.get("title"),
                "amazon_available": amazon_available,
                "amazon_reserved": reserved,
                "other_warehouse_available": outside_available,
                "other_warehouse_count_status": count_status,
                "total_available": total_available,
                "inbound": int(item.get("inbound", 0)),
                "recent_units_sold": sales_by_sku.get(sku, 0),
                "draft_source_units_available": source_units,
                "source_support_gap": support_gap,
                "draft_inventory_value": round(min(total_available, source_units) * unit_cost, 2),
                "lot_match_status": "blocked" if blockers else "ready_for_day_zero_review",
                "reconciliation_action": "Confirm day-0 layer" if not blockers else "Resolve blockers before day 0",
            }
        )

    warehouse_only_skus = [row for row in other_counts if row["sku"] not in amazon_skus]
    for row in warehouse_only_skus:
        unmatched_inventory.append(
            {
                "sku": row["sku"],
                "quantity_gap": int(row.get("available", 0)),
                "blockers": ["Outside-Amazon SKU is not matched to the Amazon catalog/FirstLot SKU map."],
                "operator_guidance": "Map, archive, or exclude this warehouse-only SKU before accepting day 0.",
            }
        )
        day_zero_blockers.append(f"{row['sku']}: outside-Amazon SKU must be mapped, archived, or excluded.")

    proposed_day_zero = {
        "proposed_start_date": f"{period}-01",
        "rule_draft": "Earliest close month start where current Amazon + outside-warehouse stock can be source-backed to purchase lots/freight, with every exception carried as a blocker.",
        "confidence": "blocked_review_required" if unmatched_inventory else "review_required",
        "requires_operator_confirmation": True,
        "blockers": day_zero_blockers,
        "unmatched_inventory": unmatched_inventory,
        "source_backed_units": sum(row["draft_source_units_available"] for row in inventory_tracking),
        "current_units_to_reconcile": sum(row["total_available"] for row in inventory_tracking) + sum(int(row.get("available", 0)) for row in warehouse_only_skus),
        "next_operator_action": "Resolve blockers, upload/approve source-backed purchase lots and freight, then confirm or adjust FIFO day 0.",
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
