"""Tests for safe local month-history, reopen, append, and rollback-plan workflow."""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "firstlot_demo"


def _run_cli(tmp_path, *extra_args):
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
            "--generated-at",
            "2026-06-03T23:00:00",
            *extra_args,
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_month_history_close_reopen_and_append_prior_month_are_append_only(tmp_path):
    first = _run_cli(tmp_path, "--period", "2026-05", "--note", "initial close")
    assert first.returncode == 0, first.stderr

    duplicate = _run_cli(tmp_path, "--period", "2026-05")
    assert duplicate.returncode != 0
    assert "already has history" in duplicate.stderr

    reopen = _run_cli(
        tmp_path,
        "--period",
        "2026-05",
        "--reopen",
        "--note",
        "fix sku queue and rerun",
    )
    assert reopen.returncode == 0, reopen.stderr

    append_prior = _run_cli(
        tmp_path,
        "--period",
        "2026-04",
        "--append-prior-month",
        "--note",
        "late April invoice append",
    )
    assert append_prior.returncode == 0, append_prior.stderr

    with (tmp_path / "month_history.json").open() as handle:
        history = json.load(handle)

    assert [row["period"] for row in history] == ["2026-05", "2026-05", "2026-04"]
    assert [row["status"] for row in history] == [
        "CLOSED",
        "REOPENED",
        "APPENDED_PRIOR_MONTH",
    ]
    assert [row["run_sequence"] for row in history] == [1, 2, 1]
    assert history[0]["shortfall_sku_count"] == 1
    assert history[0]["shortfall_quantity"] == 1
    assert (tmp_path / "month_history.csv").is_file()


def test_history_and_rollback_plan_subcommands_are_read_only(tmp_path):
    close = _run_cli(tmp_path, "--period", "2026-05", "--note", "initial close")
    assert close.returncode == 0, close.stderr

    history_result = subprocess.run(
        [sys.executable, "-m", "app.local_cli", "history", "--out", str(tmp_path)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert history_result.returncode == 0, history_result.stderr
    assert json.loads(history_result.stdout)[0]["status"] == "CLOSED"

    rollback_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "rollback-plan",
            "--out",
            str(tmp_path),
            "--period",
            "2026-05",
            "--generated-at",
            "2026-06-03T23:00:00",
            "--note",
            "operator review only",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert rollback_result.returncode == 0, rollback_result.stderr
    plan = json.loads(rollback_result.stdout)
    assert plan["read_only"] is True
    assert plan["mutations_performed"] == []
    assert plan["latest_history_status"] == "CLOSED"
    assert "do not touch live data" in plan["operator_steps"][-1]
