"""Fixture-backed tests for deterministic FirstLot MVP outputs."""
import csv
import json
import subprocess
import sys
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


def _demo_lots(name="purchase_lots.csv"):
    lots = []
    for row in _read_csv(name):
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


def _report(lots_name="purchase_lots.csv"):
    return run_fifo_report(
        InventorySnapshot(timestamp=DETERMINISTIC_TS, lots=_demo_lots(lots_name)),
        _demo_sales(),
        generated_at=DETERMINISTIC_TS,
        allow_partial_shortfalls=True,
    )


def _artifact_json(path: Path, name: str):
    with (path / name).open() as handle:
        return json.load(handle)


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


def test_fixed_rerun_fixture_clears_failed_queue_and_completes_sku_a():
    report = _report("purchase_lots_fixed.csv")

    assert [dataclass_row_dict(row) for row in report.failed_sku_queue] == []
    assert [dataclass_row_dict(row) for row in report.shortfalls] == []
    assert [dataclass_row_dict(row) for row in report.cogs_detail] == [
        {
            "sku": "SKU-A",
            "period": "2026-05",
            "total_quantity_sold": 19,
            "merchandise_cost": "209.00",
            "shipping_cost": "14.00",
            "total_cost": "223.00",
            "average_cost": "11.74",
        },
        {
            "sku": "SKU-B",
            "period": "2026-05",
            "total_quantity_sold": 2,
            "merchandise_cost": "40.00",
            "shipping_cost": "0.00",
            "total_cost": "40.00",
            "average_cost": "20.00",
        },
    ]


def test_regenerate_demo_artifacts_can_write_fixed_rerun_folder(tmp_path):
    v1_out = tmp_path / "firstlot_demo"
    fixed_out = tmp_path / "firstlot_demo_fixed"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/regenerate_firstlot_demo_artifacts.py",
            "--out",
            str(v1_out),
            "--fixed-out",
            str(fixed_out),
        ],
        cwd=Path(__file__).resolve().parents[2],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert _artifact_json(v1_out, "failed_sku_queue.json")[0]["sku"] == "SKU-A"
    assert _artifact_json(fixed_out, "failed_sku_queue.json") == []
    assert _artifact_json(fixed_out, "shortfalls.json") == []
    history = _artifact_json(fixed_out, "month_history.json")
    assert [(row["run_sequence"], row["status"], row["shortfall_quantity"]) for row in history] == [
        (1, "CLOSED", 1),
        (2, "REOPENED", 0),
    ]
    assert _artifact_json(fixed_out, "cogs_detail.json")[0] == {
        "average_cost": "11.74",
        "merchandise_cost": "209.00",
        "period": "2026-05",
        "shipping_cost": "14.00",
        "sku": "SKU-A",
        "total_cost": "223.00",
        "total_quantity_sold": 19,
    }
