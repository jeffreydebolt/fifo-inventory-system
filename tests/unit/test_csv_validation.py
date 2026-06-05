"""Validation tests for local FirstLot client-test CSV readiness."""
import json
import subprocess
import sys
from pathlib import Path

from core.csv_validation import validate_firstlot_csvs

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "firstlot_demo"
BAD_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "firstlot_validation"


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
