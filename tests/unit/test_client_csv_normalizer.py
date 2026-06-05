"""Tests for local-only client-shaped CSV normalizers."""
import csv
import json
import subprocess
import sys
from pathlib import Path

from core.csv_validation import validate_firstlot_csvs
from core.lots_normalizer import (
    inspect_lot_csv,
    inspect_movement_csv,
    normalize_lot_csv,
    normalize_movement_csv,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "firstlot_client_exports"


def test_inspect_lot_csv_maps_client_shape_and_warns_about_po_number():
    inspection = inspect_lot_csv(FIXTURE_DIR / "sample_lots_client_shape.csv")

    assert inspection.ready_to_normalize is True
    assert inspection.mapping["lot_id"] == "po_number"
    assert inspection.mapping["original_quantity"] == "original_unit_qty"
    assert inspection.mapping["remaining_quantity"] == "remaining_unit_qty"
    assert inspection.ignored_blank_headers == 4
    assert any(warning.code == "mapped_po_number_to_lot_id" for warning in inspection.warnings)
    assert inspection.sample_rows[0]["unit_price"] == "$7.00"


def test_normalize_lot_csv_converts_currency_commas_and_dates(tmp_path):
    out = tmp_path / "purchase_lots.csv"
    result = normalize_lot_csv(FIXTURE_DIR / "sample_lots_client_shape.csv", out)

    assert result.ok is True
    assert result.rows_written == 5
    assert result.validation["valid"] is True
    with out.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0] == {
        "lot_id": "ST0001",
        "sku": "DEMO-SKU-001",
        "received_date": "2022-12-01",
        "original_quantity": "1002",
        "remaining_quantity": "1002",
        "unit_price": "7.00",
        "freight_cost_per_unit": "2.69",
    }


def test_inspect_movement_csv_generates_sale_ids_when_missing():
    inspection = inspect_movement_csv(FIXTURE_DIR / "sample_sales_client_shape.csv")

    assert inspection.ready_to_normalize is True
    assert inspection.generated_sale_ids is True
    assert inspection.mapping["sku"] == "SKU"
    assert inspection.mapping["quantity_sold"] == "Quantity_Sold"
    assert inspection.mapping["sale_date"] == "Sale_Month_Str"
    assert inspection.sample_rows[0]["sale_id"] == "SALE-0001"


def test_normalize_movement_csv_converts_sales_export_shape(tmp_path):
    out = tmp_path / "movement.csv"
    result = normalize_movement_csv(FIXTURE_DIR / "sample_sales_client_shape.csv", out)

    assert result.ok is True
    assert result.rows_written == 5
    assert result.validation["valid"] is True
    with out.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0] == {
        "sale_id": "SALE-0001",
        "sku": "DEMO-SKU-001",
        "sale_date": "2025-09-01",
        "quantity_sold": "1",
    }


def test_cli_normalizers_create_valid_files_that_run_fifo(tmp_path):
    lots_out = tmp_path / "purchase_lots.csv"
    movement_out = tmp_path / "movement.csv"
    run_out = tmp_path / "run"

    for command in (
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "normalize-lots",
            "--lots",
            str(FIXTURE_DIR / "sample_lots_client_shape.csv"),
            "--out",
            str(lots_out),
        ],
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "normalize-movement",
            "--movement",
            str(FIXTURE_DIR / "sample_sales_client_shape.csv"),
            "--out",
            str(movement_out),
        ],
    ):
        result = subprocess.run(command, cwd=REPO_ROOT, check=False, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr + result.stdout
        payload = json.loads(result.stdout)
        assert payload["ok"] is True

    validation = validate_firstlot_csvs(lots_out, movement_out)
    assert validation.valid is True

    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "run",
            "--lots",
            str(lots_out),
            "--movement",
            str(movement_out),
            "--out",
            str(run_out),
            "--period",
            "2025-09",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr + run.stdout
    assert (run_out / "close_packet.json").exists()
    packet = json.loads((run_out / "close_packet.json").read_text())
    assert packet["period"] == "2025-09"
    assert packet["summary"]["failed_sku_count"] == 0
