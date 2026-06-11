"""Pure output helpers for local FIFO/FirstLot runs.

These helpers deliberately avoid Supabase, dotenv, API imports, and file system
side effects unless a caller explicitly writes the returned rows elsewhere.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable, List, Optional, cast

from .fifo_engine import FIFOEngine
from .models import (
    AuditTrailRow,
    COGSAttribution,
    COGSDetail,
    COGSSummary,
    FailedSKUQueueRow,
    InventorySnapshot,
    PurchaseLot,
    RemainingLayer,
    Sale,
    Shortfall,
)


@dataclass
class FIFOReport:
    """Deterministic report bundle for a local FIFO run."""

    generated_at: datetime
    cogs_summary: List[COGSSummary]
    remaining_layers: List[RemainingLayer]
    audit_trail: List[AuditTrailRow]
    shortfalls: List[Shortfall]
    failed_sku_queue: List[FailedSKUQueueRow]
    cogs_detail: List[COGSDetail]


def remaining_layers(snapshot: InventorySnapshot) -> List[RemainingLayer]:
    """Return non-empty layers sorted deterministically by SKU, date, lot id."""
    layers = [
        RemainingLayer(
            lot_id=lot.lot_id,
            sku=lot.sku,
            received_date=lot.received_date,
            original_quantity=lot.original_quantity,
            remaining_quantity=lot.remaining_quantity,
            unit_cost=lot.total_unit_cost,
            remaining_value=lot.total_unit_cost * Decimal(lot.remaining_quantity),
        )
        for lot in snapshot.lots
        if lot.remaining_quantity > 0
    ]
    return sorted(layers, key=lambda row: (row.sku, row.received_date, row.lot_id))


def audit_trail_rows(
    attributions: Iterable[COGSAttribution],
    lots: Iterable[PurchaseLot],
) -> List[AuditTrailRow]:
    """Flatten sale attributions into sale-to-lot rows with lot dates included."""
    received_by_lot_id = {lot.lot_id: lot.received_date for lot in lots}
    rows: List[AuditTrailRow] = []
    for attr in attributions:
        for allocation in attr.allocations:
            rows.append(
                AuditTrailRow(
                    sale_id=attr.sale_id,
                    sku=attr.sku,
                    sale_date=attr.sale_date,
                    lot_id=allocation.lot_id,
                    lot_received_date=received_by_lot_id[allocation.lot_id],
                    quantity=allocation.quantity,
                    unit_cost=allocation.unit_cost,
                    total_cost=allocation.total_cost,
                )
            )
    return sorted(rows, key=lambda row: (row.sale_date, row.sale_id, row.lot_id))


def failed_sku_queue_rows(shortfalls: Iterable[Shortfall]) -> List[FailedSKUQueueRow]:
    """Aggregate sale shortfalls into a SKU/month fix-and-rerun queue."""
    grouped: dict[tuple[str, str], list[Shortfall]] = {}
    for shortfall in shortfalls:
        period = shortfall.sale_date.strftime("%Y-%m")
        grouped.setdefault((shortfall.sku, period), []).append(shortfall)

    rows: List[FailedSKUQueueRow] = []
    for (sku, period), sku_shortfalls in grouped.items():
        sorted_shortfalls = sorted(sku_shortfalls, key=lambda row: (row.sale_date, row.sale_id))
        rows.append(
            FailedSKUQueueRow(
                sku=sku,
                period=period,
                failure_count=len(sorted_shortfalls),
                first_sale_date=sorted_shortfalls[0].sale_date,
                last_sale_date=sorted_shortfalls[-1].sale_date,
                requested_quantity=sum(row.requested_quantity for row in sorted_shortfalls),
                allocated_quantity=sum(row.allocated_quantity for row in sorted_shortfalls),
                shortfall_quantity=sum(row.shortfall_quantity for row in sorted_shortfalls),
                reasons="|".join(sorted({row.reason for row in sorted_shortfalls})),
            )
        )
    return sorted(rows, key=lambda row: (row.period, row.sku))


def cogs_detail_rows(
    attributions: Iterable[COGSAttribution],
    lots: Iterable[PurchaseLot],
) -> List[COGSDetail]:
    """Return SKU/month unit, shipping, total, and average costs for month close."""

    lots_by_id = {lot.lot_id: lot for lot in lots}
    grouped: dict[tuple[str, str], dict[str, Decimal | int]] = {}
    for attr in attributions:
        period = attr.sale_date.strftime("%Y-%m")
        bucket = grouped.setdefault(
            (attr.sku, period),
            {
                "quantity": 0,
                "merchandise_cost": Decimal("0"),
                "shipping_cost": Decimal("0"),
            },
        )
        for allocation in attr.allocations:
            lot = lots_by_id[allocation.lot_id]
            bucket["quantity"] += allocation.quantity
            bucket["merchandise_cost"] += lot.unit_price * Decimal(allocation.quantity)
            bucket["shipping_cost"] += lot.freight_cost_per_unit * Decimal(allocation.quantity)

    rows: List[COGSDetail] = []
    for (sku, period), bucket in grouped.items():
        quantity = int(bucket["quantity"])
        merchandise_cost = cast(Decimal, bucket["merchandise_cost"])
        shipping_cost = cast(Decimal, bucket["shipping_cost"])
        total_cost = merchandise_cost + shipping_cost
        rows.append(
            COGSDetail(
                sku=sku,
                period=period,
                total_quantity_sold=quantity,
                merchandise_cost=merchandise_cost,
                shipping_cost=shipping_cost,
                total_cost=total_cost,
                average_cost=total_cost / Decimal(quantity) if quantity > 0 else Decimal("0"),
            )
        )
    return sorted(rows, key=lambda row: (row.period, row.sku))


def run_fifo_report(
    initial_inventory: InventorySnapshot,
    sales: List[Sale],
    generated_at: Optional[datetime] = None,
    allow_partial_shortfalls: bool = True,
) -> FIFOReport:
    """Run FIFO and return all MVP output sections in one pure object."""
    timestamp = generated_at or datetime.now()
    engine = FIFOEngine()
    attributions, final_inventory = engine.process_transactions(
        initial_inventory,
        sales,
        snapshot_timestamp=timestamp,
        allow_partial_shortfalls=allow_partial_shortfalls,
    )
    shortfalls = engine.get_shortfalls()
    return FIFOReport(
        generated_at=timestamp,
        cogs_summary=engine.calculate_summary(attributions),
        remaining_layers=remaining_layers(final_inventory),
        audit_trail=audit_trail_rows(attributions, final_inventory.lots),
        shortfalls=shortfalls,
        failed_sku_queue=failed_sku_queue_rows(shortfalls),
        cogs_detail=cogs_detail_rows(attributions, final_inventory.lots),
    )


def decimal_to_string(value: Decimal) -> str:
    """Format decimals predictably for CSV/JSON fixture comparisons."""
    return format(value.quantize(Decimal("0.01")), "f")


def iso_datetime(value: datetime) -> str:
    """Serialize datetimes without locale-specific formatting."""
    return value.isoformat()


def dataclass_row_dict(row) -> dict:
    """Convert output dataclass row to primitive string-friendly values."""
    converted = {}
    for key, value in asdict(row).items():
        if isinstance(value, Decimal):
            converted[key] = decimal_to_string(value)
        elif isinstance(value, datetime):
            converted[key] = iso_datetime(value)
        else:
            converted[key] = value
    return converted
