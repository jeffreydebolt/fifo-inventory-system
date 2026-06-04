"""Tests for local failed-SKU queue review, fix-plan, and assert-clear workflow."""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "firstlot_demo"


def _run_fixture(tmp_path: Path, lots_name: str = "purchase_lots.csv"):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "run",
            "--lots",
            str(FIXTURE_DIR / lots_name),
            "--movement",
            str(FIXTURE_DIR / "movement.csv"),
            "--out",
            str(tmp_path),
            "--generated-at",
            "2026-06-03T23:00:00",
            "--period",
            "2026-05",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_failed_skus_review_and_fix_plan_are_read_only(tmp_path):
    run = _run_fixture(tmp_path)
    assert run.returncode == 0, run.stderr

    review = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "failed-skus",
            "--out",
            str(tmp_path),
            "--period",
            "2026-05",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert review.returncode == 0, review.stderr
    review_rows = json.loads(review.stdout)
    assert review_rows[0]["sku"] == "SKU-A"
    assert review_rows[0]["shortfall_quantity"] == 1

    plan = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "fix-plan",
            "--out",
            str(tmp_path),
            "--period",
            "2026-05",
            "--lots",
            str(FIXTURE_DIR / "purchase_lots.csv"),
            "--movement",
            str(FIXTURE_DIR / "movement.csv"),
            "--note",
            "add missing local lot and rerun",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert plan.returncode == 0, plan.stderr
    payload = json.loads(plan.stdout)
    assert payload["read_only"] is True
    assert payload["mutations_performed"] == []
    assert payload["affected_skus"] == ["SKU-A"]
    assert payload["recommended_csv_fixes"][0]["minimum_additional_available_units_needed"] == 1
    assert "--reopen" in payload["rerun_command_args"]


def test_failed_skus_assert_clear_fails_then_passes_after_fixed_local_rerun(tmp_path):
    run = _run_fixture(tmp_path)
    assert run.returncode == 0, run.stderr

    uncleared = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "failed-skus",
            "--out",
            str(tmp_path),
            "--period",
            "2026-05",
            "--assert-clear",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert uncleared.returncode == 1
    assert json.loads(uncleared.stdout)["total_shortfall_quantity"] == 1

    fixed = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "run",
            "--lots",
            str(FIXTURE_DIR / "purchase_lots_fixed.csv"),
            "--movement",
            str(FIXTURE_DIR / "movement.csv"),
            "--out",
            str(tmp_path),
            "--generated-at",
            "2026-06-03T23:00:00",
            "--period",
            "2026-05",
            "--reopen",
            "--note",
            "fixed local lot and reran",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert fixed.returncode == 0, fixed.stderr

    cleared = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "failed-skus",
            "--out",
            str(tmp_path),
            "--period",
            "2026-05",
            "--assert-clear",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert cleared.returncode == 0, cleared.stderr
    assert json.loads(cleared.stdout) == {
        "clear": True,
        "queue_record_count": 0,
        "queue_records": [],
        "total_shortfall_quantity": 0,
    }
