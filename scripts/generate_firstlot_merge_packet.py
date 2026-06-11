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
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.check_firstlot_merge_safety import MergeSafetyConfig, _check_git_state, build_commands
from scripts.check_no_client_data_commit import check_staged, path_safety_reasons


def _run_git(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=repo_root, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _git_ok(repo_root: Path, args: list[str]) -> bool:
    result = subprocess.run(["git", *args], cwd=repo_root, check=False, capture_output=True, text=True)
    return result.returncode == 0


def _changed_files(repo_root: Path, base_ref: str) -> list[str]:
    output = _run_git(repo_root, ["diff", "--name-only", f"{base_ref}...HEAD"])
    return [line for line in output.splitlines() if line]


def _diff_stat(repo_root: Path, base_ref: str) -> str:
    return _run_git(repo_root, ["diff", "--stat", f"{base_ref}...HEAD"])


def _commit_range(repo_root: Path, base_ref: str) -> str:
    if _git_ok(repo_root, ["merge-base", "--is-ancestor", base_ref, "HEAD"]):
        base_sha = _run_git(repo_root, ["rev-parse", "--short", base_ref])
        head_sha = _run_git(repo_root, ["rev-parse", "--short", "HEAD"])
        if base_sha and head_sha:
            return f"{base_sha}..{head_sha}"
    merge_base = _run_git(repo_root, ["merge-base", "--short", base_ref, "HEAD"])
    head_sha = _run_git(repo_root, ["rev-parse", "--short", "HEAD"])
    if merge_base and head_sha:
        return f"{merge_base}..{head_sha}"
    return f"{base_ref}...HEAD"


def _staged_safety_scan(repo_root: Path) -> dict[str, Any]:
    try:
        ok, violations = check_staged(repo_root)
    except RuntimeError as exc:
        return {"status": "blocked", "violations": [str(exc)]}
    return {
        "status": "passed" if ok else "blocked",
        "violations": violations,
    }


def _changed_path_safety_scan(changed_files: list[str]) -> dict[str, Any]:
    violations = [
        f"{path}: {'; '.join(reasons)}"
        for path in changed_files
        if (reasons := path_safety_reasons(path))
    ]
    return {
        "status": "passed" if not violations else "blocked",
        "violations": violations,
    }


def _verification_entries(raw_results: list[str] | None) -> list[dict[str, str]]:
    if not raw_results:
        return [
            {
                "command": "python3 -m pytest tests/unit/test_merge_readiness_packet.py tests/unit/test_no_client_data_commit_guard.py -q",
                "status": "not_provided",
                "notes": "Run locally before handoff; packet generation does not execute tests.",
            },
            {
                "command": "git diff --check",
                "status": "not_provided",
                "notes": "Run locally before handoff; packet generation does not execute tests.",
            },
            {
                "command": "git status --short",
                "status": "not_provided",
                "notes": "Run locally before handoff; packet generation does not execute tests.",
            },
        ]

    entries: list[dict[str, str]] = []
    for raw in raw_results:
        if "=" in raw:
            command, status = raw.split("=", 1)
            entries.append({"command": command.strip(), "status": status.strip() or "provided", "notes": ""})
        else:
            entries.append({"command": raw.strip(), "status": "provided", "notes": ""})
    return entries


def build_packet(
    repo_root: Path,
    base_ref: str = "origin/main",
    allow_main: bool = False,
    verification_results: list[str] | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    config = MergeSafetyConfig(repo_root=repo_root, base_ref=base_ref, fast=False, dry_run=True, allow_main=allow_main)
    blockers = _check_git_state(config)
    commands = build_commands(config)
    changed_files = _changed_files(repo_root, base_ref)
    staged_scan = _staged_safety_scan(repo_root)
    changed_path_scan = _changed_path_safety_scan(changed_files)
    safety_status = "passed" if staged_scan["status"] == "passed" and changed_path_scan["status"] == "passed" and not blockers else "blocked"
    pr_ready = safety_status == "passed"

    return {
        "process": "firstlot-autonomous-merge-readiness",
        "branch": _run_git(repo_root, ["branch", "--show-current"]),
        "head_sha": _run_git(repo_root, ["rev-parse", "--short", "HEAD"]),
        "base_ref": base_ref,
        "commit_range": _commit_range(repo_root, base_ref),
        "decision": "blocked" if not pr_ready else "ready_for_pr_or_merge",
        "blockers": blockers,
        "changed_files": changed_files,
        "diff_stat": _diff_stat(repo_root, base_ref),
        "safety_scan": {
            "status": safety_status,
            "staged_client_live_data": staged_scan,
            "changed_path_leaks": changed_path_scan,
            "notes": [
                "Offline/local scan only.",
                "Does not read .env files or call production APIs.",
                "Blocks obvious .env, Storage Standard, and client-data path leaks.",
            ],
        },
        "local_verification": _verification_entries(verification_results),
        "skipped_live_actions": {
            "live_database_writes": "skipped",
            "supabase_uploads_migrations_rollbacks": "skipped",
            "storage_standard_or_client_data_mutation": "skipped",
            "network_calls": "skipped",
        },
        "git_handoff": {
            "push": "not_performed",
            "pr_creation": "not_performed",
            "main_branch_push": "not_performed",
        },
        "pr_readiness": {
            "status": "ready" if pr_ready else "blocked",
            "reason": "Local packet safety scans passed." if pr_ready else "Resolve blockers or unsafe path findings before push/PR.",
        },
        "recommended_next_safe_bead": "Run the targeted verification commands, review this packet, then push/open PR only with Jeff approval.",
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
        f"Commit range: `{packet['commit_range']}`",
        f"PR readiness: `{packet['pr_readiness']['status']}`",
        "",
        "## Safety boundary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in packet["safety_boundary"].items())
    lines.extend(["", "## Safety scan", ""])
    lines.append(f"- status: `{packet['safety_scan']['status']}`")
    lines.append(f"- staged client/live data: `{packet['safety_scan']['staged_client_live_data']['status']}`")
    lines.append(f"- changed path leaks: `{packet['safety_scan']['changed_path_leaks']['status']}`")
    scan_violations = (
        packet["safety_scan"]["staged_client_live_data"]["violations"]
        + packet["safety_scan"]["changed_path_leaks"]["violations"]
    )
    lines.extend(f"- violation: {violation}" for violation in (scan_violations or ["None"]))
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}" for blocker in (packet["blockers"] or ["None"]))
    lines.extend(["", "## Local verification", ""])
    lines.extend(
        f"- `{entry['command']}`: `{entry['status']}`{(' - ' + entry['notes']) if entry.get('notes') else ''}"
        for entry in packet["local_verification"]
    )
    lines.extend(["", "## Skipped live actions", ""])
    lines.extend(f"- {key}: `{value}`" for key, value in packet["skipped_live_actions"].items())
    lines.extend(["", "## Git handoff", ""])
    lines.extend(f"- {key}: `{value}`" for key, value in packet["git_handoff"].items())
    lines.extend(["", "## Required checks", ""])
    lines.extend(f"- **{check['name']}**: `{check['command']}`" for check in packet["required_checks"])
    lines.extend(["", "## Human review gates", ""])
    lines.extend(f"- {gate}" for gate in packet["human_review_gates"])
    lines.extend(["", "## Changed files", ""])
    lines.extend(f"- `{path}`" for path in (packet["changed_files"] or ["None"]))
    if packet.get("diff_stat"):
        lines.extend(["", "## Diff stat", "", "```text", packet["diff_stat"], "```"])
    lines.extend(["", "## Recommended next safe bead", "", packet["recommended_next_safe_bead"]])
    lines.extend(["", "## Merge rule", "", packet["merge_rule"], ""])
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a FirstLot pre-merge readiness packet.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--base-ref", default="origin/main")
    parser.add_argument("--allow-main", action="store_true")
    parser.add_argument(
        "--verification-result",
        action="append",
        default=None,
        help="Record a local verification result as 'command=status'. May be passed multiple times.",
    )
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    packet = build_packet(
        args.repo_root,
        base_ref=args.base_ref,
        allow_main=args.allow_main,
        verification_results=args.verification_result,
    )
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
