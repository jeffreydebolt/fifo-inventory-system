"""FirstLot merge-safety gate for bounded autonomous builder branches.

This script answers one question: is this branch safe enough to push/open/merge a
bounded local/demo FirstLot PR? It deliberately checks only local, deterministic
signals and fails closed on live connector/secret-looking diffs.
"""
from __future__ import annotations

import argparse
import dataclasses
import re
import subprocess
import sys
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class MergeSafetyConfig:
    repo_root: Path = dataclasses.field(default_factory=Path.cwd)
    fast: bool = False
    dry_run: bool = False
    base_ref: str = "origin/main"


@dataclasses.dataclass(frozen=True)
class GateCommand:
    label: str
    argv: tuple[str, ...]
    cwd: str = "."


FORBIDDEN_ADDED_LINE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bload_dotenv\s*\("), "dotenv/.env loading is forbidden in FirstLot autonomous work"),
    (re.compile(r"\bdotenv\b", re.IGNORECASE), "dotenv/.env usage is forbidden in FirstLot autonomous work"),
    (re.compile(r"\bos\.environ\s*\["), "direct environment secret access needs explicit review"),
    (re.compile(r"SUPABASE_(SERVICE_ROLE|KEY|URL)"), "Supabase credential/live-data marker found"),
    (re.compile(r"requests\.(get|post|put|patch|delete)\([^\n]*(sellingpartnerapi|sellercentral|amazonaws|amazon)", re.IGNORECASE), "possible live Amazon/SP-API HTTP call added"),
    (re.compile(r"httpx\.(get|post|put|patch|delete)\([^\n]*(sellingpartnerapi|sellercentral|amazonaws|amazon)", re.IGNORECASE), "possible live Amazon/SP-API HTTP call added"),
    (re.compile(r"\b(import|from)\s+(boto3|botocore|sp_api|selling_partner)\b", re.IGNORECASE), "possible live Amazon connector library added"),
    (re.compile(r"subprocess\.(run|Popen|call).*shell\s*=\s*True"), "shell=True subprocess added"),
)


def _run(args: list[str], repo_root: Path, cwd: str = ".") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=repo_root / cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def _git_diff(repo_root: Path, base_ref: str) -> str:
    result = _run(["git", "diff", f"{base_ref}...HEAD"], repo_root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git diff {base_ref}...HEAD failed")
    return result.stdout


FORBIDDEN_SCAN_EXEMPT_PATHS = {
    "scripts/check_firstlot_merge_safety.py",
    "tests/unit/test_merge_safety_gate.py",
}


def _scan_added_lines_for_forbidden_patterns(diff_text: str) -> list[str]:
    violations: list[str] = []
    current_path: str | None = None
    for line_number, line in enumerate(diff_text.splitlines(), start=1):
        if line.startswith("+++ b/"):
            current_path = line.removeprefix("+++ b/")
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        if current_path in FORBIDDEN_SCAN_EXEMPT_PATHS:
            continue
        for pattern, message in FORBIDDEN_ADDED_LINE_PATTERNS:
            if pattern.search(line):
                violations.append(f"diff line {line_number}: {message}: {line[:180]}")
    return violations


def build_commands(config: MergeSafetyConfig) -> list[GateCommand]:
    commands = [
        GateCommand("client/live data staged guard", ("make", "check-no-client-data-commit")),
        GateCommand(
            "Amazon mock/onboarding targeted tests",
            (
                "python3",
                "-m",
                "pytest",
                "tests/unit/test_amazon_sp_api_mock_connector.py",
                "tests/unit/test_amazon_onboarding.py",
                "tests/unit/test_local_cli_amazon_onboarding.py",
                "-q",
            ),
        ),
        GateCommand("FirstLot demo safety check", ("make", "check-firstlot-demo")),
    ]
    if not config.fast:
        commands.extend(
            [
                GateCommand("FirstLot weekend safety suite", ("make", "check-firstlot-weekend")),
                GateCommand("dashboard test suite", ("npm", "test", "--", "--watchAll=false"), cwd="cogs-dashboard"),
                GateCommand("dashboard production build", ("npm", "run", "build"), cwd="cogs-dashboard"),
            ]
        )
    return commands


def _check_git_state(config: MergeSafetyConfig) -> list[str]:
    repo_root = config.repo_root
    failures: list[str] = []

    branch = _run(["git", "branch", "--show-current"], repo_root).stdout.strip()
    if branch in {"main", "master"}:
        failures.append("Refusing merge-safety pass while working directly on main/master.")

    diff_name_status = _run(["git", "diff", "--name-status", f"{config.base_ref}...HEAD"], repo_root)
    if diff_name_status.returncode != 0:
        failures.append(diff_name_status.stderr.strip() or f"Could not diff against {config.base_ref}.")
    else:
        changed = diff_name_status.stdout
        blocked_paths = [
            line for line in changed.splitlines()
            if re.search(r"(^|/)(\.env|local-client-fixtures|Storage Standard|clients/.+\.(csv|json|xlsx))", line)
        ]
        if blocked_paths:
            failures.append("Blocked path(s) changed since base: " + "; ".join(blocked_paths))

    diff_text = _git_diff(repo_root, config.base_ref)
    forbidden = _scan_added_lines_for_forbidden_patterns(diff_text)
    failures.extend(forbidden)
    return failures


def run_gate(config: MergeSafetyConfig) -> int:
    repo_root = config.repo_root.resolve()
    failures = _check_git_state(dataclasses.replace(config, repo_root=repo_root))
    if failures:
        print("FirstLot merge safety gate failed before tests:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    for command in build_commands(config):
        print(f"\n==> {command.label}: {' '.join(command.argv)}")
        if config.dry_run:
            continue
        result = _run(list(command.argv), repo_root, cwd=command.cwd)
        if result.stdout:
            print(result.stdout.rstrip())
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)
        if result.returncode != 0:
            print(f"FirstLot merge safety gate failed: {command.label}", file=sys.stderr)
            return result.returncode

    print("\nFirstLot merge safety gate passed.")
    print("Safe signal: branch is bounded/local-demo, guards passed, tests passed, no forbidden live connector/secret diff detected.")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the FirstLot bounded-branch merge-safety gate.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--base-ref", default="origin/main")
    parser.add_argument("--fast", action="store_true", help="Run fast local merge gate without dashboard build/full weekend suite.")
    parser.add_argument("--dry-run", action="store_true", help="Print the checks that would run without executing them.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    return run_gate(MergeSafetyConfig(repo_root=args.repo_root, fast=args.fast, dry_run=args.dry_run, base_ref=args.base_ref))


if __name__ == "__main__":
    raise SystemExit(main())
