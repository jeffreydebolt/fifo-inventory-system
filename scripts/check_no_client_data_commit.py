"""Guard staged commits against accidental client/live data additions.

This check is intentionally scoped to the Git index. The repository contains
legacy/live-derived files that must be handled separately; the weekend lane needs
a fast guardrail that blocks *new staged changes* from adding Storage Standard or
other client-looking exports while still allowing synthetic fixtures and code
changes.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DATA_SUFFIXES = {
    ".csv",
    ".json",
    ".jsonl",
    ".log",
    ".txt",
    ".tsv",
}

BLOCKED_BASENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".env.test",
    "analysis.csv",
    "fifo_processing_log.txt",
    "fifo_processing_log_supabase.txt",
}

CLIENT_MARKERS = {
    "Storage Standard",
    "cli_",
    "inv_",
    "paydis_",
    "BANK ACCOUNT",
    "SUPABASE_SERVICE_ROLE",
    "SUPABASE_KEY",
    "SUPABASE_URL",
}

SAFE_SYNTHETIC_PREFIXES = (
    "tests/fixtures/",
    "examples/",
    "cogs-dashboard/src/demo-output/",
)


def _run_git(args: list[str], repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )


def staged_paths(repo_root: Path) -> list[str]:
    result = _run_git(
        ["diff", "--cached", "--name-only", "--diff-filter=ACMRT"],
        repo_root,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git diff --cached failed")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _is_data_file(path: str) -> bool:
    return Path(path).suffix.lower() in DATA_SUFFIXES


def _read_staged_text(repo_root: Path, path: str) -> str:
    result = _run_git(["show", f":{path}"], repo_root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"could not read staged content for {path}")
    return result.stdout


def _looks_like_client_data(path: str, text: str) -> list[str]:
    reasons: list[str] = []
    basename = Path(path).name
    if basename in BLOCKED_BASENAMES:
        reasons.append(f"blocked filename {basename}")

    matched_markers = sorted(marker for marker in CLIENT_MARKERS if marker in text)
    if matched_markers:
        reasons.append("client/live-data marker(s): " + ", ".join(matched_markers))

    return reasons


def check_staged(repo_root: Path) -> tuple[bool, list[str]]:
    violations: list[str] = []
    for path in staged_paths(repo_root):
        if Path(path).name in BLOCKED_BASENAMES:
            violations.append(f"{path}: blocked filename {Path(path).name}")
            continue

        if not _is_data_file(path):
            continue

        text = _read_staged_text(repo_root, path)
        reasons = _looks_like_client_data(path, text)
        if not reasons:
            continue

        safe_prefix = path.startswith(SAFE_SYNTHETIC_PREFIXES)
        if safe_prefix and "blocked filename" not in "; ".join(reasons):
            violations.append(
                f"{path}: synthetic/demo paths must not contain client/live markers ({'; '.join(reasons)})"
            )
        else:
            violations.append(f"{path}: {'; '.join(reasons)}")

    return (not violations, violations)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fail if staged data-like files appear to contain client/live data."
    )
    parser.add_argument(
        "--repo-root",
        default=Path.cwd(),
        type=Path,
        help="Git repository root to inspect; defaults to the current directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = args.repo_root.resolve()
    ok, violations = check_staged(repo_root)
    if ok:
        print("No staged client/live data detected.")
        return 0

    print("Blocked staged client/live data:", file=sys.stderr)
    for violation in violations:
        print(f"- {violation}", file=sys.stderr)
    print(
        "Only commit tiny synthetic fixtures/examples/demo artifacts; do not commit Storage Standard/client exports, .env data, or live-service logs.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
