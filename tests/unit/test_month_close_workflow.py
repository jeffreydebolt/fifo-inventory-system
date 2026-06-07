"""Tests for read-only FIFO month-close management workflow payload."""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "firstlot_demo"


def _run_close(tmp_path, *extra_args):
    return subprocess.run(
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
            "--period",
            "2026-05",
            "--generated-at",
            "2026-06-03T23:00:00",
            *extra_args,
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _workflow(tmp_path, *extra_args):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "workflow",
            "--out",
            str(tmp_path),
            "--period",
            "2026-05",
            *extra_args,
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_workflow_payload_stays_on_core_fifo_close_process(tmp_path):
    close = _run_close(tmp_path, "--note", "initial local close")
    assert close.returncode == 0, close.stderr

    result = _workflow(tmp_path)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    assert payload["workflow_type"] == "firstlot_fifo_month_close_management"
    assert payload["safety_mode"] == "local_fixture_only_no_live_writes"
    assert payload["status"] == "NEEDS_FIX"
    assert [step["label"] for step in payload["workflow_steps"]] == [
        "Upload purchase lots CSV",
        "Upload sales CSV",
        "Run monthly COGS",
        "Review SKU-level COGS",
        "Review failed SKU queue / fix / rerun",
    ]
    assert payload["month_totals"] == {
        "failed_sku_count": 1,
        "failed_skus": ["SKU-A"],
        "shortfall_quantity": 1,
        "sku_count": 2,
        "total_cogs": "250.00",
        "total_units_sold": 20,
    }
    assert {"unit_cost", "shipping_cost", "total_cost", "average_cost"}.issubset(
        payload["sku_level_cogs"][0]
    )
    assert payload["management_actions"]["rerun_after_fix_mode"] == "--reopen"
    assert payload["management_actions"]["append_prior_month_mode"] == "--append-prior-month"
    assert payload["management_actions"]["rollback"] == "read_only_plan_only"
    assert payload["management_actions"]["live_mutations_performed"] == []
    assert "no production Amazon/Shopify calls" in payload["prohibited_scope"]


def test_workflow_can_embed_read_only_rollback_plan(tmp_path):
    close = _run_close(tmp_path, "--note", "initial local close")
    assert close.returncode == 0, close.stderr

    result = _workflow(tmp_path, "--include-rollback-plan")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    assert payload["rollback_plan"]["read_only"] is True
    assert payload["rollback_plan"]["mutations_performed"] == []
    assert payload["rollback_plan"]["latest_run_sequence"] == 1
