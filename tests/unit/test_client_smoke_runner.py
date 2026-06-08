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
    assert payload["missing_lot_request_path"] is None
    assert payload["synthetic_repair_lots_path"] is None

    expected_paths = [
        "normalized/purchase_lots.csv",
        "normalized/movement.csv",
        "cogs_summary.csv",
        "failed_sku_queue.json",
        "fix_plan.json",
        "client_smoke_summary.json",
        "client_smoke_summary.md",
        "close_packet.md",
    ]
    for relative_path in expected_paths:
        assert (tmp_path / relative_path).exists(), relative_path

    summary = json.loads((tmp_path / "client_smoke_summary.json").read_text())
    assert summary["safety"].startswith("local client CSV smoke only")
    summary_md = (tmp_path / "client_smoke_summary.md").read_text()
    assert "PASS — failed SKU queue clear" in summary_md
    assert "no .env, no Supabase/API imports, no live DB writes" in summary_md
    assert "python3 -m app.local_cli failed-skus" in summary_md
    fix_plan = json.loads((tmp_path / "fix_plan.json").read_text())
    assert fix_plan["read_only"] is True
    assert fix_plan["recommended_csv_fixes"] == []


def _write_lots_with_missing_sku(tmp_path: Path) -> Path:
    lots_with_missing_sku = tmp_path / "lots_missing_one_sku.csv"
    rows = list(csv.DictReader((FIXTURE_DIR / "sample_lots_client_shape.csv").open(newline="")))
    with lots_with_missing_sku.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        for row in rows:
            if row["sku"] != "DEMO-SKU-005":
                writer.writerow(row)
    return lots_with_missing_sku


def test_client_smoke_expect_clear_returns_nonzero_when_queue_remains(tmp_path):
    lots_with_missing_sku = _write_lots_with_missing_sku(tmp_path)

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
    missing_lot_request_path = Path(payload["missing_lot_request_path"])
    assert missing_lot_request_path.exists()
    with missing_lot_request_path.open(newline="") as handle:
        missing_rows = list(csv.DictReader(handle))
    assert missing_rows == [
        {
            "sku": "DEMO-SKU-005",
            "period": "2025-09",
            "minimum_units_needed": "1",
            "first_sale_date": "2025-09-01T00:00:00",
            "last_sale_date": "2025-09-01T00:00:00",
            "reason": "NO_INVENTORY",
            "source_document_needed": "Source-backed purchase lot with received date on/before first sale date, available units, unit cost, and freight cost",
            "operator_note": "Do not invent COGS: add only purchase-lot data supported by source exports/invoices, then rerun client-smoke or local FIFO.",
        }
    ]
    repair_path = Path(payload["synthetic_repair_lots_path"])
    assert repair_path.exists()
    repair_text = repair_path.read_text()
    assert "SANDBOX ONLY" in repair_text
    assert "SYNTH-REPAIR-DEMO-SKU-005" in repair_text
    summary_md = (tmp_path / "smoke" / "client_smoke_summary.md").read_text()
    assert "NEEDS FIX — failed SKU queue remains" in summary_md
    assert "missing_lot_request.csv" in summary_md
    assert "DEMO-SKU-005 2025-09" in summary_md


def test_client_smoke_json_out_writes_same_payload_and_prints_human_summary(tmp_path):
    json_out = tmp_path / "operator" / "summary.json"
    result = _run_client_smoke(tmp_path / "smoke", "--json-out", str(json_out))

    assert result.returncode == 0, result.stderr
    assert json_out.exists()
    explicit_payload = json.loads(json_out.read_text())
    generated_payload = json.loads((tmp_path / "smoke" / "client_smoke_summary.json").read_text())
    assert explicit_payload == generated_payload
    assert "FirstLot client-smoke complete" in result.stdout
    assert "Period: 2025-09" in result.stdout
    assert "Total COGS:" in result.stdout
    assert "Failed SKU count: 0" in result.stdout
    assert "Output folder:" in result.stdout
    assert "JSON summary:" in result.stdout
    assert "client-smoke" not in result.stderr


def test_client_smoke_expect_clear_json_out_prints_clear_failure_summary(tmp_path):
    lots_with_missing_sku = _write_lots_with_missing_sku(tmp_path)
    json_out = tmp_path / "operator" / "failed-summary.json"

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
            str(tmp_path / "smoke-json"),
            "--period",
            "2025-09",
            "--expect-clear",
            "--json-out",
            str(json_out),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert json_out.exists()
    payload = json.loads(json_out.read_text())
    assert payload["ok"] is False
    assert payload["failed_sku_count"] == 1
    assert "FAILED SKU queue remains" in result.stdout
    assert "Next command: python3 -m app.local_cli fix-plan" in result.stdout
    assert "DEMO-SKU-005" in json.dumps(payload["fix_plan"])


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


def test_csv_doctor_reports_combined_readiness_without_writing_artifacts(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "csv-doctor",
            "--lots",
            str(FIXTURE_DIR / "sample_lots_client_shape.csv"),
            "--movement",
            str(FIXTURE_DIR / "sample_sales_client_shape.csv"),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ready_to_normalize"] is True
    assert payload["blockers"] == []
    assert payload["lots"]["row_count"] == 5
    assert payload["movement"]["row_count"] == 5
    assert payload["movement"]["generated_sale_ids"] is True
    assert "client-smoke" in "\n".join(payload["next_commands"])
    assert "read-only inspection" in payload["safety"]
    assert list(tmp_path.iterdir()) == []


def test_csv_doctor_human_summary_surfaces_blocking_header_fixes(tmp_path):
    bad_lots = tmp_path / "bad_lots.csv"
    bad_lots.write_text(
        "sku,received_date,original_quantity,remaining_quantity,unit_price,freight_cost_per_unit\n"
        "DEMO-SKU-001,2025-09-01,1,1,10.00,1.00\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "csv-doctor",
            "--lots",
            str(bad_lots),
            "--movement",
            str(FIXTURE_DIR / "sample_sales_client_shape.csv"),
            "--human",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "FirstLot CSV doctor" in result.stdout
    assert "Status: NEEDS FIX" in result.stdout
    assert "purchase_lots missing mappable column for lot_id" in result.stdout
    assert "Fix the missing/mismapped CSV headers" in result.stdout
    assert "no artifacts written" in result.stdout
