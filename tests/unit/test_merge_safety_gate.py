from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.check_firstlot_merge_safety import (
    MergeSafetyConfig,
    _scan_added_lines_for_forbidden_patterns,
    build_commands,
)


def test_build_commands_include_full_safe_firstlot_and_dashboard_checks():
    commands = build_commands(MergeSafetyConfig())
    command_text = "\n".join(command.label + " " + " ".join(command.argv) for command in commands)

    assert "check-no-client-data-commit" in command_text
    assert "check-firstlot-demo" in command_text
    assert "check-firstlot-weekend" in command_text
    assert "tests/unit/test_amazon_onboarding.py" in command_text
    assert "tests/unit/test_local_cli_amazon_onboarding.py" in command_text
    assert "npm test" in command_text
    assert "npm run build" in command_text


def test_build_commands_allow_fast_mode_without_dropping_client_data_guard():
    commands = build_commands(MergeSafetyConfig(fast=True))
    command_text = "\n".join(command.label + " " + " ".join(command.argv) for command in commands)

    assert "check-no-client-data-commit" in command_text
    assert "check-firstlot-demo" in command_text
    assert "check-firstlot-weekend" not in command_text
    assert "npm run build" not in command_text


def test_forbidden_scan_flags_live_connectors_and_secret_access():
    diff = """
+import os
+from dotenv import load_dotenv
+load_dotenv()
+import requests
+requests.get('https://sellingpartnerapi-na.amazon.com/orders')
+SUPABASE_SERVICE_ROLE='abc123'
"""

    violations = _scan_added_lines_for_forbidden_patterns(diff)

    assert any("dotenv" in violation for violation in violations)
    assert any("live Amazon" in violation for violation in violations)
    assert any("SUPABASE_SERVICE_ROLE" in violation for violation in violations)


def test_script_fast_mode_passes_on_current_repo():
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["python3", "scripts/check_firstlot_merge_safety.py", "--fast", "--dry-run", "--allow-main", "--base-ref", "HEAD"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "FirstLot merge safety gate passed" in result.stdout
