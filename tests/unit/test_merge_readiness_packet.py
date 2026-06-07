from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.generate_firstlot_merge_packet import build_packet


def test_build_packet_contains_printing_press_style_sections():
    repo_root = Path(__file__).resolve().parents[2]
    packet = build_packet(repo_root=repo_root, base_ref="HEAD", allow_main=True)

    assert packet["process"] == "firstlot-premerge-readiness"
    assert packet["decision"] in {"ready_for_pr_or_merge", "blocked"}
    assert packet["safety_boundary"]["live_amazon_calls"] is False
    assert packet["safety_boundary"]["live_database_writes"] is False
    assert packet["safety_boundary"]["env_reads"] is False
    assert packet["required_checks"]
    assert any(check["name"] == "FirstLot merge safety gate" for check in packet["required_checks"])
    assert packet["human_review_gates"]
    assert "live Amazon connector" in " ".join(packet["human_review_gates"])


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
    assert payload["process"] == "firstlot-premerge-readiness"
    assert "# FirstLot pre-merge readiness packet" in markdown
    assert "Required checks" in markdown
    assert "Safety boundary" in markdown
