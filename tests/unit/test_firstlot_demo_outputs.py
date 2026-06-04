"""Fixture-backed tests for deterministic FirstLot MVP outputs."""
import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from core.models import InventorySnapshot, PurchaseLot, Sale
from core.outputs import dataclass_row_dict, run_fifo_report

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "firstlot_demo"
DETERMINISTIC_TS = datetime(2026, 6, 3, 23, 0, 0)


def _read_csv(name):
    with (FIXTURE_DIR / name).open(newline="") as handle:
        return list(csv.DictReader(handle))


def _demo_lots():
    lots = []
    for row in _read_csv("purchase_lots.csv"):
        lots.append(
            PurchaseLot(
                lot_id=row["lot_id"],
                sku=row["sku"],
                received_date=datetime.fromisoformat(row["received_date"]),
                original_quantity=int(row["original_quantity"]),
                remaining_quantity=int(row["remaining_quantity"]),
                unit_price=Decimal(row["unit_price"]),
                freight_cost_per_unit=Decimal(row["freight_cost_per_unit"]),
            )
        )
    return lots


def _demo_sales():
    sales = []
    for row in _read_csv("movement.csv"):
        sales.append(
            Sale(
                sale_id=row["sale_id"],
                sku=row["sku"],
                sale_date=datetime.fromisoformat(row["sale_date"]),
                quantity_sold=int(row["quantity_sold"]),
            )
        )
    return sales


def _report():
    return run_fifo_report(
        InventorySnapshot(timestamp=DETERMINISTIC_TS, lots=_demo_lots()),
        _demo_sales(),
        generated_at=DETERMINISTIC_TS,
        allow_partial_shortfalls=True,
    )


def test_demo_fixture_cogs_summary_matches_expected_csv():
    report = _report()

    actual = [dataclass_row_dict(row) for row in report.cogs_summary]

    assert actual == [
        {
            "sku": row["sku"],
            "period": row["period"],
            "total_quantity_sold": int(row["total_quantity_sold"]),
            "total_cogs": row["total_cogs"],
            "average_unit_cost": row["average_unit_cost"],
        }
        for row in _read_csv("expected_cogs_summary.csv")
    ]


def test_demo_fixture_remaining_layers_matches_expected_csv():
    report = _report()

    actual = [dataclass_row_dict(row) for row in report.remaining_layers]

    assert actual == [
        {
            "lot_id": row["lot_id"],
            "sku": row["sku"],
            "received_date": row["received_date"],
            "original_quantity": int(row["original_quantity"]),
            "remaining_quantity": int(row["remaining_quantity"]),
            "unit_cost": row["unit_cost"],
            "remaining_value": row["remaining_value"],
        }
        for row in _read_csv("expected_remaining_layers.csv")
    ]


def test_demo_fixture_audit_trail_matches_expected_csv():
    report = _report()

    actual = [dataclass_row_dict(row) for row in report.audit_trail]

    assert actual == [
        {
            "sale_id": row["sale_id"],
            "sku": row["sku"],
            "sale_date": row["sale_date"],
            "lot_id": row["lot_id"],
            "lot_received_date": row["lot_received_date"],
            "quantity": int(row["quantity"]),
            "unit_cost": row["unit_cost"],
            "total_cost": row["total_cost"],
        }
        for row in _read_csv("expected_audit_trail.csv")
    ]


def test_demo_fixture_shortfalls_match_expected_csv():
    report = _report()

    actual = [dataclass_row_dict(row) for row in report.shortfalls]

    assert actual == [
        {
            "sale_id": row["sale_id"],
            "sku": row["sku"],
            "sale_date": row["sale_date"],
            "requested_quantity": int(row["requested_quantity"]),
            "allocated_quantity": int(row["allocated_quantity"]),
            "shortfall_quantity": int(row["shortfall_quantity"]),
            "available_quantity": int(row["available_quantity"]),
            "reason": row["reason"],
            "message": row["message"],
        }
        for row in _read_csv("expected_shortfalls.csv")
    ]


def test_demo_fixture_failed_sku_queue_matches_expected_csv():
    report = _report()

    actual = [dataclass_row_dict(row) for row in report.failed_sku_queue]

    assert actual == [
        {
            "sku": row["sku"],
            "period": row["period"],
            "failure_count": int(row["failure_count"]),
            "first_sale_date": row["first_sale_date"],
            "last_sale_date": row["last_sale_date"],
            "requested_quantity": int(row["requested_quantity"]),
            "allocated_quantity": int(row["allocated_quantity"]),
            "shortfall_quantity": int(row["shortfall_quantity"]),
            "reasons": row["reasons"],
            "status": row["status"],
        }
        for row in _read_csv("expected_failed_sku_queue.csv")
    ]


def test_demo_fixture_cogs_detail_matches_expected_csv():
    report = _report()

    actual = [dataclass_row_dict(row) for row in report.cogs_detail]

    assert actual == [
        {
            "sku": row["sku"],
            "period": row["period"],
            "total_quantity_sold": int(row["total_quantity_sold"]),
            "merchandise_cost": row["merchandise_cost"],
            "shipping_cost": row["shipping_cost"],
            "total_cost": row["total_cost"],
            "average_cost": row["average_cost"],
        }
        for row in _read_csv("expected_cogs_detail.csv")
    ]


def test_demo_fixture_generated_at_is_deterministic():
    report = _report()

    assert report.generated_at == DETERMINISTIC_TS
