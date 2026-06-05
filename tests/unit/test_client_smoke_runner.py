"""End-to-end tests for the local client CSV smoke runner."""
import csv
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "firstlot_client_exports"


def _run_client_smoke(tmp_path: Path, *extra_args: str):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "client-smoke",
            "--lots",
            str(FIXTURE_DIR / "sample_lots_client_shape.csv"),
            "--movement",
            str(FIXTURE_DIR / "sample_sales_client_shape.csv"),
            "--out",
            str(tmp_path),
            "--period",
            "2025-09",
            "--generated-at",
            "2026-06-03T23:00:00",
            *extra_args,
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_client_smoke_normalizes_runs_and_writes_operator_artifacts(tmp_path):
    result = _run_client_smoke(tmp_path)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    assert payload["ok"] is True
    assert payload["period"] == "2025-09"
    assert payload["mutations_performed"] == []
    assert payload["validation"]["valid"] is True
    assert payload["lots_normalization"]["rows_written"] == 5
    assert payload["movement_normalization"]["rows_written"] == 5
    assert payload["failed_sku_count"] == 0
    assert payload["total_shortfall_quantity"] == 0
    assert payload["synthetic_repair_lots_path"] is None

    expected_paths = [
        "normalized/purchase_lots.csv",
        "normalized/movement.csv",
        "cogs_summary.csv",
        "failed_sku_queue.json",
        "fix_plan.json",
        "client_smoke_summary.json",
        "close_packet.md",
    ]
    for relative_path in expected_paths:
        assert (tmp_path / relative_path).exists(), relative_path

    summary = json.loads((tmp_path / "client_smoke_summary.json").read_text())
    assert summary["safety"].startswith("local client CSV smoke only")
    fix_plan = json.loads((tmp_path / "fix_plan.json").read_text())
    assert fix_plan["read_only"] is True
    assert fix_plan["recommended_csv_fixes"] == []


def test_client_smoke_expect_clear_returns_nonzero_when_queue_remains(tmp_path):
    lots_with_missing_sku = tmp_path / "lots_missing_one_sku.csv"
    rows = list(csv.DictReader((FIXTURE_DIR / "sample_lots_client_shape.csv").open(newline="")))
    with lots_with_missing_sku.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        for row in rows:
            if row["sku"] != "DEMO-SKU-005":
                writer.writerow(row)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "client-smoke",
            "--lots",
            str(lots_with_missing_sku),
            "--movement",
            str(FIXTURE_DIR / "sample_sales_client_shape.csv"),
            "--out",
            str(tmp_path / "smoke"),
            "--period",
            "2025-09",
            "--expect-clear",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["failed_sku_count"] == 1
    assert payload["total_shortfall_quantity"] == 1
    assert payload["fix_plan"]["recommended_csv_fixes"] == [
        {
            "sku": "DEMO-SKU-005",
            "period": "2025-09",
            "minimum_additional_available_units_needed": 1,
            "reason": "NO_INVENTORY",
            "status": "NEEDS_FIX_RERUN",
        }
    ]
    repair_path = Path(payload["synthetic_repair_lots_path"])
    assert repair_path.exists()
    repair_text = repair_path.read_text()
    assert "SANDBOX ONLY" in repair_text
    assert "SYNTH-REPAIR-DEMO-SKU-005" in repair_text


def test_client_smoke_clean_output_is_limited_to_tmp_paths(tmp_path):
    reusable_tmp_out = Path("/tmp/firstlot-client-smoke-clean-test")
    reusable_tmp_out.mkdir(parents=True, exist_ok=True)
    (reusable_tmp_out / "stale.txt").write_text("stale")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "client-smoke",
            "--lots",
            str(FIXTURE_DIR / "sample_lots_client_shape.csv"),
            "--movement",
            str(FIXTURE_DIR / "sample_sales_client_shape.csv"),
            "--out",
            str(reusable_tmp_out),
            "--period",
            "2025-09",
            "--clean-output",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert not (reusable_tmp_out / "stale.txt").exists()
    assert (reusable_tmp_out / "client_smoke_summary.json").exists()
