"""Narrow tests for safe local CSV ingest and CLI output writing."""
import csv
import subprocess
import sys
from pathlib import Path

from core.csv_ingest import load_movement_csv, load_purchase_lots_csv
from core.output_files import write_fifo_report
from core.outputs import run_fifo_report

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "firstlot_demo"


def _rows(path: Path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_csv_ingest_loads_demo_purchase_lots_and_movement():
    inventory = load_purchase_lots_csv(FIXTURE_DIR / "purchase_lots.csv")
    sales = load_movement_csv(FIXTURE_DIR / "movement.csv")

    assert [lot.lot_id for lot in inventory.lots] == ["LOT-A-001", "LOT-A-002", "LOT-B-001"]
    assert [sale.sale_id for sale in sales] == ["SALE-001", "SALE-002", "SALE-003"]


def test_output_writer_generates_canonical_csv_and_json_files(tmp_path):
    inventory = load_purchase_lots_csv(FIXTURE_DIR / "purchase_lots.csv")
    sales = load_movement_csv(FIXTURE_DIR / "movement.csv")
    report = run_fifo_report(inventory, sales)

    written = write_fifo_report(report, tmp_path)

    assert {path.name for path in written} == {
        "audit_trail.csv",
        "audit_trail.json",
        "cogs_summary.csv",
        "cogs_summary.json",
        "remaining_layers.csv",
        "remaining_layers.json",
        "shortfalls.csv",
        "shortfalls.json",
    }
    assert _rows(tmp_path / "cogs_summary.csv") == _rows(FIXTURE_DIR / "expected_cogs_summary.csv")
    assert _rows(tmp_path / "remaining_layers.csv") == _rows(FIXTURE_DIR / "expected_remaining_layers.csv")
    assert _rows(tmp_path / "audit_trail.csv") == _rows(FIXTURE_DIR / "expected_audit_trail.csv")
    assert _rows(tmp_path / "shortfalls.csv") == _rows(FIXTURE_DIR / "expected_shortfalls.csv")
    assert (tmp_path / "cogs_summary.csv").read_bytes() == (
        FIXTURE_DIR / "expected_cogs_summary.csv"
    ).read_bytes()


def test_local_cli_runs_fixture_to_output_dir(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "run",
            "--lots",
            str(FIXTURE_DIR / "purchase_lots.csv"),
            "--movement",
            str(FIXTURE_DIR / "movement.csv"),
            "--out",
            str(tmp_path),
            "--generated-at",
            "2026-06-03T23:00:00",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "no live DB writes" in result.stdout
    assert _rows(tmp_path / "cogs_summary.csv") == _rows(FIXTURE_DIR / "expected_cogs_summary.csv")
    assert _rows(tmp_path / "shortfalls.csv") == _rows(FIXTURE_DIR / "expected_shortfalls.csv")
