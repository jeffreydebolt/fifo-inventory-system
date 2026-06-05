"""Tests for read-only local fix/rerun comparison workflow."""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "firstlot_demo"


def _run_fifo(out_dir: Path, lots_name: str, *extra_args: str):
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
            str(out_dir),
            "--generated-at",
            "2026-06-03T23:00:00",
            "--period",
            "2026-05",
            *extra_args,
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_compare_runs_reports_read_only_sku_level_delta(tmp_path):
    before_dir = tmp_path / "v1"
    after_dir = tmp_path / "v2"
    before = _run_fifo(before_dir, "purchase_lots.csv")
    after = _run_fifo(after_dir, "purchase_lots_fixed.csv")
    assert before.returncode == 0, before.stderr
    assert after.returncode == 0, after.stderr

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "compare-runs",
            "--before",
            str(before_dir),
            "--after",
            str(after_dir),
            "--period",
            "2026-05",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["read_only"] is True
    assert payload["mutations_performed"] == []
    assert payload["period"] == "2026-05"
    assert payload["summary"] == {
        "after_failed_sku_count": 0,
        "after_total_cogs": "263.00",
        "before_failed_sku_count": 1,
        "before_total_cogs": "250.00",
        "delta_total_cogs": "13.00",
        "failed_sku_delta": -1,
        "sku_delta_count": 1,
    }
    sku_a_delta = next(row for row in payload["sku_deltas"] if row["sku"] == "SKU-A")
    assert sku_a_delta == {
        "after_average_cost": "11.74",
        "after_total_cost": "223.00",
        "after_units_sold": 19,
        "before_average_cost": "11.67",
        "before_total_cost": "210.00",
        "before_units_sold": 18,
        "changed": True,
        "delta_total_cost": "13.00",
        "delta_units_sold": 1,
        "sku": "SKU-A",
    }


def test_compare_runs_fails_fast_when_required_local_artifact_is_missing(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "compare-runs",
            "--before",
            str(tmp_path / "missing-before"),
            "--after",
            str(tmp_path / "missing-after"),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "Missing local artifact" in result.stderr
