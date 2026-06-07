"""Generate a FirstLot pre-merge readiness packet.

This is the human-readable companion to `check_firstlot_merge_safety.py`: a
Printing Press-style evidence packet that explains what must be true before a
bounded autonomous FirstLot branch can be pushed, PR'd, or merged.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.check_firstlot_merge_safety import MergeSafetyConfig, _check_git_state, build_commands


def _run_git(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=repo_root, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _changed_files(repo_root: Path, base_ref: str) -> list[str]:
    output = _run_git(repo_root, ["diff", "--name-only", f"{base_ref}...HEAD"])
    return [line for line in output.splitlines() if line]


def _diff_stat(repo_root: Path, base_ref: str) -> str:
    return _run_git(repo_root, ["diff", "--stat", f"{base_ref}...HEAD"])


def build_packet(repo_root: Path, base_ref: str = "origin/main", allow_main: bool = False) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    config = MergeSafetyConfig(repo_root=repo_root, base_ref=base_ref, fast=False, dry_run=True, allow_main=allow_main)
    blockers = _check_git_state(config)
    commands = build_commands(config)

    return {
        "process": "firstlot-premerge-readiness",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "branch": _run_git(repo_root, ["branch", "--show-current"]),
        "head_sha": _run_git(repo_root, ["rev-parse", "--short", "HEAD"]),
        "base_ref": base_ref,
        "decision": "blocked" if blockers else "ready_for_pr_or_merge",
        "blockers": blockers,
        "changed_files": _changed_files(repo_root, base_ref),
        "diff_stat": _diff_stat(repo_root, base_ref),
        "safety_boundary": {
            "fixture_local_demo_only": True,
            "env_reads": False,
            "live_amazon_calls": False,
            "live_database_writes": False,
            "storage_standard_or_client_data_mutation": False,
            "real_client_csv_commits": False,
        },
        "required_checks": [
            {"name": "FirstLot merge safety gate", "command": "make check-firstlot-merge-safety", "purpose": "Runs the full bounded-branch local gate before push/merge."},
            *[
                {"name": command.label, "command": " ".join(command.argv), "cwd": command.cwd, "purpose": "Sub-check inside the FirstLot merge safety gate."}
                for command in commands
            ],
            {"name": "GitHub PR checks", "command": "gh pr view <number> --json statusCheckRollup,mergeable", "purpose": "Confirms CI, demo safety, dashboard, and deploy-preview statuses before merge."},
            {"name": "Post-merge main verification", "command": "make check-firstlot-weekend && gh run list --branch main --limit 5", "purpose": "Verifies merged main, not just the PR branch."},
        ],
        "human_review_gates": [
            "Any live Amazon connector, Seller Central OAuth, SP-API HTTP client, token handling, or credential flow requires Jeff approval and a separate reviewed branch.",
            "Any live DB/Supabase/API write, rollback, migration, upload, or client-data mutation requires explicit approval.",
            "Any real client CSV/export or Storage Standard-derived artifact must stay outside git.",
            "Any accounting/FIFO day-zero acceptance rule is review-required; mock readiness scores are product UX signals, not accounting judgments.",
            "If Netlify/Vercel/GitHub deploy-preview is red or ambiguous, leave the PR open.",
        ],
        "merge_rule": "May squash-merge only when the local merge-safety gate passes, GitHub checks pass, work is bounded/local-demo/no-live-work, and no human review gate is triggered.",
    }


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# FirstLot pre-merge readiness packet",
        "",
        f"Decision: `{packet['decision']}`",
        f"Branch: `{packet['branch']}`",
        f"Head: `{packet['head_sha']}`",
        f"Base: `{packet['base_ref']}`",
        "",
        "## Safety boundary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in packet["safety_boundary"].items())
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}" for blocker in (packet["blockers"] or ["None"]))
    lines.extend(["", "## Required checks", ""])
    lines.extend(f"- **{check['name']}**: `{check['command']}`" for check in packet["required_checks"])
    lines.extend(["", "## Human review gates", ""])
    lines.extend(f"- {gate}" for gate in packet["human_review_gates"])
    lines.extend(["", "## Changed files", ""])
    lines.extend(f"- `{path}`" for path in (packet["changed_files"] or ["None"]))
    if packet.get("diff_stat"):
        lines.extend(["", "## Diff stat", "", "```text", packet["diff_stat"], "```"])
    lines.extend(["", "## Merge rule", "", packet["merge_rule"], ""])
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a FirstLot pre-merge readiness packet.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--base-ref", default="origin/main")
    parser.add_argument("--allow-main", action="store_true")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    packet = build_packet(args.repo_root, base_ref=args.base_ref, allow_main=args.allow_main)
    markdown = render_markdown(packet)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(packet, indent=2) + "\n")
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(markdown)
    if not args.json_out and not args.md_out:
        print(markdown)
    return 1 if packet["decision"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
