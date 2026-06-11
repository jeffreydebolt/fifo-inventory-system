"""Tests for the staged client-data commit guard."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD_SCRIPT = REPO_ROOT / "scripts" / "check_no_client_data_commit.py"


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def _init_repo(tmp_path: Path) -> None:
    assert _run(["git", "init"], tmp_path).returncode == 0
    assert _run(["git", "config", "user.email", "test@example.invalid"], tmp_path).returncode == 0
    assert _run(["git", "config", "user.name", "Test Guard"], tmp_path).returncode == 0


def test_no_client_data_guard_allows_clean_synthetic_fixture(tmp_path):
    _init_repo(tmp_path)
    fixture_dir = tmp_path / "tests" / "fixtures" / "synthetic"
    fixture_dir.mkdir(parents=True)
    (fixture_dir / "purchase_lots.csv").write_text(
        "lot_id,sku,received_date,original_unit_qty,remaining_unit_qty,unit_cost,freight_cost\n"
        "LOT-001,SYNTH-SKU,2026-06-01,2,2,10.00,1.00\n"
    )
    assert _run(["git", "add", "tests/fixtures/synthetic/purchase_lots.csv"], tmp_path).returncode == 0

    result = _run([sys.executable, str(GUARD_SCRIPT), "--repo-root", str(tmp_path)], tmp_path)

    assert result.returncode == 0, result.stderr
    assert "No staged client/live data detected" in result.stdout


def test_no_client_data_guard_blocks_storage_standard_export(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "analysis.csv").write_text(
        "customer,client_id,invoice_id,bank\n"
        "Storage Standard,cli_mnviboxjaaraaeqatmvq,inv_nasyfzlt4r2aaaiaf6iq,BANK ACCOUNT 9016\n"
    )
    assert _run(["git", "add", "analysis.csv"], tmp_path).returncode == 0

    result = _run([sys.executable, str(GUARD_SCRIPT), "--repo-root", str(tmp_path)], tmp_path)

    assert result.returncode == 1
    assert "Blocked staged client/live data" in result.stderr
    assert "analysis.csv" in result.stderr
    assert "Storage Standard" in result.stderr


def test_no_client_data_guard_blocks_staged_env_file_by_name_without_printing_secret(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / ".env").write_text("SUPABASE_KEY=super-secret-test-value\n")
    assert _run(["git", "add", ".env"], tmp_path).returncode == 0

    result = _run([sys.executable, str(GUARD_SCRIPT), "--repo-root", str(tmp_path)], tmp_path)

    assert result.returncode == 1
    assert "blocked filename .env" in result.stderr
    assert "super-secret-test-value" not in result.stderr


def test_no_client_data_guard_blocks_client_markers_even_under_fixture_paths(tmp_path):
    _init_repo(tmp_path)
    fixture_dir = tmp_path / "tests" / "fixtures" / "unsafe"
    fixture_dir.mkdir(parents=True)
    (fixture_dir / "movement.csv").write_text(
        "sale_id,sku,sale_date,quantity\n"
        "inv_nasyfzlt4r2aaaiaf6iq,SKU-1,2026-06-01,1\n"
    )
    assert _run(["git", "add", "tests/fixtures/unsafe/movement.csv"], tmp_path).returncode == 0

    result = _run([sys.executable, str(GUARD_SCRIPT), "--repo-root", str(tmp_path)], tmp_path)

    assert result.returncode == 1
    assert "synthetic/demo paths must not contain client/live markers" in result.stderr
    assert "inv_" in result.stderr


def test_no_client_data_guard_blocks_client_data_paths_without_reading_markers(tmp_path):
    _init_repo(tmp_path)
    client_dir = tmp_path / "clients"
    client_dir.mkdir()
    (client_dir / "month_close.csv").write_text(
        "sku,quantity\n"
        "SYNTH-SKU,1\n"
    )
    assert _run(["git", "add", "clients/month_close.csv"], tmp_path).returncode == 0

    result = _run([sys.executable, str(GUARD_SCRIPT), "--repo-root", str(tmp_path)], tmp_path)

    assert result.returncode == 1
    assert "data file under client/live-data directory" in result.stderr
