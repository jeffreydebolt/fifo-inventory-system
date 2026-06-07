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
    rollback_reconstruction = []
    reconciliation_trace = []
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
        receipts_in_period = int(guidance.get("draft_receipts_in_rollback_period") or 0)
        unit_cost = float(guidance.get("draft_unit_cost") or 0)
        freight_per_unit = float(guidance.get("draft_freight_per_unit") or 0)
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
                    "source_documents_needed": guidance.get("source_documents_needed", ["supplier invoice", "freight allocation"]),
                    "source_documents_present": guidance.get("source_documents_present", []),
                    "freight_documents_present": guidance.get("freight_documents_present", []),
                    "reconciliation_note": guidance.get("reconciliation_note", "Fixture-only blocker; operator source review required."),
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
                "supported_lot_ids": guidance.get("supported_lot_ids", []),
                "source_documents_present": guidance.get("source_documents_present", []),
                "freight_documents_present": guidance.get("freight_documents_present", []),
                "evidence_quality": guidance.get("evidence_quality", "missing"),
                "draft_unit_cost": unit_cost,
                "draft_freight_per_unit": freight_per_unit,
                "draft_inventory_value": round(min(total_available, source_units) * (unit_cost + freight_per_unit), 2),
                "lot_match_status": "blocked" if blockers else "ready_for_day_zero_review",
                "reconciliation_action": "Confirm day-0 layer" if not blockers else "Resolve blockers before day 0",
            }
        )
        estimated_period_start_units = total_available + sales_by_sku.get(sku, 0) - receipts_in_period
        rollback_reconstruction.append(
            {
                "sku": sku,
                "current_units": total_available,
                "period_sales_units": sales_by_sku.get(sku, 0),
                "draft_receipts_in_period": receipts_in_period,
                "estimated_units_at_period_start": estimated_period_start_units,
                "source_backed_start_units": min(max(estimated_period_start_units, 0), source_units),
                "rollback_status": "blocked" if blockers or estimated_period_start_units < 0 else "ready_for_operator_review",
                "rollback_note": (
                    "Receipts exceed current plus sales; confirm inbound timing or earlier sales."
                    if estimated_period_start_units < 0
                    else "Fixture-only rollback estimate; operator must confirm sales history, purchase lots, freight, and counts."
                ),
            }
        )
        reconciliation_trace.append(
            {
                "sku": sku,
                "formula": "current_units + period_sales_units - draft_receipts_in_period",
                "current_units": total_available,
                "period_sales_units": sales_by_sku.get(sku, 0),
                "draft_receipts_in_period": receipts_in_period,
                "estimated_units_at_period_start": estimated_period_start_units,
                "evidence_quality": guidance.get("evidence_quality", "missing"),
                "oldest_supported_receipt_date": guidance.get("oldest_supported_receipt_date"),
                "operator_decision_required": "approve_day_zero_layer" if not blockers and estimated_period_start_units >= 0 else "resolve_blockers_before_day_zero",
            }
        )

    warehouse_only_skus = [row for row in other_counts if row["sku"] not in amazon_skus]
    for row in warehouse_only_skus:
        unmatched_inventory.append(
            {
                "sku": row["sku"],
                "quantity_gap": int(row.get("available", 0)),
                "blockers": ["Outside-Amazon SKU is not matched to the Amazon catalog/FirstLot SKU map."],
                "source_documents_needed": ["warehouse count", "SKU map decision"],
                "source_documents_present": [f"warehouse count at {row.get('location')}"] if row.get("counted_at") else [],
                "freight_documents_present": [],
                "reconciliation_note": "Warehouse-only fixture count cannot join FIFO until an SKU map/include/exclude decision is made.",
                "operator_guidance": "Map, archive, or exclude this warehouse-only SKU before accepting day 0.",
            }
        )
        day_zero_blockers.append(f"{row['sku']}: outside-Amazon SKU must be mapped, archived, or excluded.")

    current_units_to_reconcile = sum(row["total_available"] for row in inventory_tracking) + sum(
        int(row.get("available", 0)) for row in warehouse_only_skus
    )
    source_backed_units = sum(row["draft_source_units_available"] for row in inventory_tracking)

    proposed_day_zero = {
        "proposed_start_date": f"{period}-01",
        "rule_draft": "Earliest close month start where current Amazon + outside-warehouse stock can be source-backed to purchase lots/freight, with every exception carried as a blocker.",
        "confidence": "blocked_review_required" if unmatched_inventory else "review_required",
        "requires_operator_confirmation": True,
        "blockers": day_zero_blockers,
        "unmatched_inventory": unmatched_inventory,
        "rollback_reconstruction": rollback_reconstruction,
        "reconciliation_trace": reconciliation_trace,
        "source_support_ratio": round(source_backed_units / max(current_units_to_reconcile, 1), 4),
        "unmatched_units": current_units_to_reconcile - source_backed_units,
        "mock_readiness_score": round((source_backed_units / max(current_units_to_reconcile, 1)) * 100),
        "source_backed_units": source_backed_units,
        "current_units_to_reconcile": current_units_to_reconcile,
        "operator_decisions_required": [
            "Confirm Amazon sales/order/report history is complete for rollback period.",
            "Map, archive, or exclude warehouse-only SKUs before day 0.",
            "Attach supplier invoices and freight allocations for unsupported units.",
            "Approve or reject the proposed FIFO day 0; do not rely on COGS while blocked.",
        ],
        "readiness_checklist": [
            {"label": "Amazon sales history covers rollback window", "status": "needs_operator_confirmation"},
            {"label": "Every current SKU mapped to Amazon or explicit outside-warehouse decision", "status": "blocked"},
            {"label": "Purchase lots source-backed for all current units", "status": "blocked"},
            {"label": "Freight allocations attached or explicitly not required", "status": "blocked"},
            {"label": "FIFO day 0 approved by operator", "status": "not_started"},
        ],
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
