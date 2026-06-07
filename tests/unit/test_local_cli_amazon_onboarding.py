"""CLI tests for safe Amazon mock onboarding."""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "amazon_sp_api_mock"


def test_local_cli_amazon_onboarding_mock_outputs_safety_payload():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "amazon-onboarding-mock",
            "--fixture-dir",
            str(FIXTURE_DIR),
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
    assert payload["connector_mode"] == "mock"
    assert payload["credentials_loaded"] is False
    assert payload["live_api_calls_performed"] == []
    assert payload["mutations_performed"] == []
    assert payload["mock_amazon_connection"]["account_name"] == "FirstLot Mock Seller Central"
    assert payload["proposed_fifo_day_0"]["confidence"] == "review_required"
