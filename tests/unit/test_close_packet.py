"""Close packet tests for local FirstLot client-test readiness."""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "firstlot_demo"


def test_local_cli_writes_close_packet_for_month_run(tmp_path):
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
            "--period",
            "2026-05",
            "--note",
            "test close packet",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert str(tmp_path / "close_packet.json") in result.stdout
    assert str(tmp_path / "close_packet.md") in result.stdout

    packet = json.loads((tmp_path / "close_packet.json").read_text())
    assert packet["packet_type"] == "firstlot_local_month_close"
    assert packet["safety_mode"] == "local_fixture_only_no_live_writes"
    assert packet["live_mutations_performed"] == []
    assert packet["period"] == "2026-05"
    assert packet["generated_at"] == "2026-06-03T23:00:00"
    assert packet["summary"] == {
        "failed_sku_count": 1,
        "failed_skus": ["SKU-A"],
        "shortfall_quantity": 1,
        "sku_count": 2,
        "skus_processed": ["SKU-A", "SKU-B"],
        "total_cogs": "250.00",
        "total_units_sold": 20,
    }
    assert packet["history"]["status"] == "CLOSED"
    assert packet["history"]["run_sequence"] == 1
    assert packet["accountant_review_columns"]["cogs_detail"] == [
        "sku",
        "period",
        "total_quantity_sold",
        "merchandise_cost",
        "shipping_cost",
        "total_cost",
        "average_cost",
    ]
    assert packet["local_review_commands"]["failed_sku_queue"].endswith(
        f"--out {tmp_path} --period 2026-05"
    )
    assert packet["local_review_commands"]["rollback_plan_read_only"].endswith(
        f"--out {tmp_path} --period 2026-05"
    )
    assert packet["input_files"]["purchase_lots"]["name"] == "purchase_lots.csv"
    assert packet["input_files"]["movement"]["name"] == "movement.csv"
    assert "cogs_summary.csv" in packet["artifact_files"]
    assert "month_history.json" in packet["artifact_files"]

    markdown = (tmp_path / "close_packet.md").read_text()
    assert "# FirstLot local close packet" in markdown
    assert "## Local review commands" in markdown
    assert "rollback-plan" in markdown
    assert "No live database writes" in markdown
    assert "Fix local input CSVs and rerun" in markdown


def test_close_packet_can_be_disabled_for_csv_only_compatibility(tmp_path):
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
            "--csv-only",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "close_packet.json").exists()
    assert not (tmp_path / "close_packet.md").exists()
