"""Validation tests for local FirstLot client-test CSV readiness."""
import json
import subprocess
import sys
from pathlib import Path

from core.csv_validation import human_validation_report, validate_firstlot_csvs

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "firstlot_demo"
BAD_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "firstlot_validation"
SECOND_SYNTHETIC_FIXTURE_DIR = (
    Path(__file__).resolve().parents[1] / "fixtures" / "firstlot_second_synthetic_client"
)


def test_validate_firstlot_csvs_accepts_good_demo_inputs():
    result = validate_firstlot_csvs(
        FIXTURE_DIR / "purchase_lots.csv",
        FIXTURE_DIR / "movement.csv",
    )

    assert result.valid is True
    assert result.errors == []
    assert result.to_dict()["summary"].startswith("CSV validation passed")


def test_validate_firstlot_csvs_reports_operator_errors_for_bad_inputs():
    result = validate_firstlot_csvs(
        BAD_FIXTURE_DIR / "bad_purchase_lots.csv",
        BAD_FIXTURE_DIR / "bad_movement.csv",
    )

    payload = result.to_dict()
    codes = {error["code"] for error in payload["errors"]}
    assert result.valid is False
    assert "duplicate_lot_id" in codes
    assert "duplicate_sale_id" in codes
    assert "invalid_date" in codes
    assert "non_positive_quantity" in codes
    assert "negative_freight" in codes
    assert "remaining_exceeds_original" in codes
    assert "CSV validation failed" in payload["summary"]
    first_error = payload["errors"][0]
    assert first_error["severity"] == "error"
    assert first_error["title"]
    assert first_error["details"]
    assert first_error["suggested_action"]
    assert first_error["blocking"] is True


def test_validate_firstlot_csvs_reports_cross_file_operator_guidance(tmp_path):
    lots = tmp_path / "purchase_lots.csv"
    movement = tmp_path / "movement.csv"
    lots.write_text(
        "lot_id,sku,received_date,original_quantity,remaining_quantity,unit_price,freight_cost_per_unit\n"
        "LOT-1,KNOWN,2026-05-10,3,3,10.00,1.00\n",
        encoding="utf-8",
    )
    movement.write_text(
        "sale_id,sku,sale_date,quantity_sold\n"
        "SALE-1,MISSING,2026-05-12,1\n"
        "SALE-2,KNOWN,2026-05-01,1\n",
        encoding="utf-8",
    )

    payload = validate_firstlot_csvs(lots, movement).to_dict()

    assert payload["valid"] is False
    codes = {error["code"] for error in payload["errors"]}
    assert "movement_sku_missing_from_purchase_lots" in codes
    assert "sale_before_first_received_lot" in codes
    missing_sku = next(error for error in payload["errors"] if error["code"] == "movement_sku_missing_from_purchase_lots")
    assert missing_sku["title"] == "Movement SKU has no purchase lot"
    assert "source-backed purchase lots" in missing_sku["suggested_action"]


def test_human_validation_report_summarizes_next_operator_action():
    result = validate_firstlot_csvs(
        BAD_FIXTURE_DIR / "bad_purchase_lots.csv",
        BAD_FIXTURE_DIR / "bad_movement.csv",
    )

    report = human_validation_report(result)

    assert "Next action: fix blocking CSV issues" in report
    assert "Suggested action:" in report
    assert "Duplicate purchase lot ID" in report


def test_local_cli_validate_prints_json_and_returns_nonzero_for_bad_inputs():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "validate",
            "--lots",
            str(BAD_FIXTURE_DIR / "bad_purchase_lots.csv"),
            "--movement",
            str(BAD_FIXTURE_DIR / "bad_movement.csv"),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["valid"] is False
    assert payload["errors"]


def test_local_cli_run_stops_before_artifact_writes_when_validation_fails(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "run",
            "--lots",
            str(BAD_FIXTURE_DIR / "bad_purchase_lots.csv"),
            "--movement",
            str(BAD_FIXTURE_DIR / "bad_movement.csv"),
            "--out",
            str(tmp_path),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["valid"] is False
    assert list(tmp_path.iterdir()) == []


def test_second_synthetic_client_fixture_validates_cleanly():
    result = validate_firstlot_csvs(
        SECOND_SYNTHETIC_FIXTURE_DIR / "purchase_lots.csv",
        SECOND_SYNTHETIC_FIXTURE_DIR / "movement.csv",
    )

    assert result.valid is True
    assert result.errors == []
    assert result.warnings == []


def test_generic_client_fixture_workflow_runs_second_synthetic_client(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_firstlot_client_fixture.py",
            "--fixture-dir",
            str(SECOND_SYNTHETIC_FIXTURE_DIR),
            "--out",
            str(tmp_path / "second-client-output"),
            "--period",
            "2026-06",
            "--expect-clear",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["read_only_local_fixture_workflow"] is True
    assert payload["mutations_performed"] == []
    assert payload["validation"]["valid"] is True
    assert payload["failed_sku_check"]["clear"] is True
    assert payload["total_cogs"] == "723.00"
    assert payload["remaining_inventory_value"] == "485.50"
    assert payload["skus"] == ["CAMERA-KIT", "STRAP-BUNDLE", "TRIPOD"]
