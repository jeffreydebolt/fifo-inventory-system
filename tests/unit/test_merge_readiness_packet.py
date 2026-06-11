from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.generate_firstlot_merge_packet import build_packet
from scripts.check_no_client_data_commit import path_safety_reasons


def test_build_packet_contains_printing_press_style_sections():
    repo_root = Path(__file__).resolve().parents[2]
    packet = build_packet(repo_root=repo_root, base_ref="HEAD", allow_main=True)

    assert packet["process"] == "firstlot-autonomous-merge-readiness"
    assert packet["decision"] in {"ready_for_pr_or_merge", "blocked"}
    assert packet["base_ref"] == "HEAD"
    assert packet["commit_range"]
    assert isinstance(packet["changed_files"], list)
    assert "diff_stat" in packet
    assert packet["safety_boundary"]["live_amazon_calls"] is False
    assert packet["safety_boundary"]["live_database_writes"] is False
    assert packet["safety_boundary"]["env_reads"] is False
    assert packet["safety_scan"]["staged_client_live_data"]["status"] in {"passed", "blocked"}
    assert packet["safety_scan"]["changed_path_leaks"]["status"] in {"passed", "blocked"}
    assert packet["local_verification"][0]["status"] == "not_provided"
    assert packet["skipped_live_actions"]["live_database_writes"] == "skipped"
    assert packet["git_handoff"]["push"] == "not_performed"
    assert packet["git_handoff"]["pr_creation"] == "not_performed"
    assert packet["pr_readiness"]["status"] in {"ready", "blocked"}
    assert packet["recommended_next_safe_bead"]
    assert packet["required_checks"]
    assert any(check["name"] == "FirstLot merge safety gate" for check in packet["required_checks"])
    assert packet["human_review_gates"]
    assert "live Amazon connector" in " ".join(packet["human_review_gates"])


def test_packet_records_provided_verification_results():
    repo_root = Path(__file__).resolve().parents[2]
    packet = build_packet(
        repo_root=repo_root,
        base_ref="HEAD",
        allow_main=True,
        verification_results=["git diff --check=passed"],
    )

    assert packet["local_verification"] == [
        {"command": "git diff --check", "status": "passed", "notes": ""}
    ]


def test_path_safety_rejects_env_storage_standard_and_client_data_paths():
    unsafe_paths = [
        ".env",
        "reports/Storage Standard/export.csv",
        "clients/storage-standard-lots.csv",
        "client-data/month-close.json",
    ]

    for path in unsafe_paths:
        assert path_safety_reasons(path), path


def test_packet_cli_writes_json_and_markdown(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    json_path = tmp_path / "packet.json"
    md_path = tmp_path / "packet.md"

    result = subprocess.run(
        [
            "python3",
            "scripts/generate_firstlot_merge_packet.py",
            "--base-ref",
            "HEAD",
            "--allow-main",
            "--json-out",
            str(json_path),
            "--md-out",
            str(md_path),
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(json_path.read_text())
    markdown = md_path.read_text()
    assert payload["process"] == "firstlot-autonomous-merge-readiness"
    assert "# FirstLot pre-merge readiness packet" in markdown
    assert "PR readiness" in markdown
    assert "Skipped live actions" in markdown
    assert "Required checks" in markdown
    assert "Safety boundary" in markdown
