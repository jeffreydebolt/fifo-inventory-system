"""Run the safe, reproducible FirstLot local demo check.

Safety boundary: this check only regenerates artifacts from synthetic CSV fixtures
into a temporary directory and runs the dashboard smoke test against checked-in
demo artifacts. It does not read .env files, import Supabase adapters, call the
production API, or write to a live database.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = REPO_ROOT / "cogs-dashboard"
REGENERATE_SCRIPT = REPO_ROOT / "scripts" / "regenerate_firstlot_demo_artifacts.py"
DASHBOARD_SMOKE_TEST = DASHBOARD_DIR / "src" / "App.test.js"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check the fixture-backed FirstLot demo path without live services."
    )
    parser.add_argument(
        "--out",
        help="Optional output directory for regenerated artifacts. Defaults to a temporary directory.",
    )
    parser.add_argument(
        "--keep-out",
        action="store_true",
        help="Keep the generated artifact directory after the check finishes.",
    )
    parser.add_argument(
        "--skip-dashboard",
        action="store_true",
        help="Only regenerate/verify artifacts; skip the dashboard smoke test.",
    )
    return parser.parse_args()


def _run(command: list[str], cwd: Path) -> None:
    print(f"$ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def _npm_command() -> str:
    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("npm was not found; install Node/npm to run the dashboard smoke test")
    return npm


def main() -> int:
    args = _parse_args()
    temp_dir: Path | None = None

    if args.out:
        out_dir = Path(args.out).resolve()
    else:
        temp_dir = Path(tempfile.mkdtemp(prefix="firstlot-demo-check-"))
        out_dir = temp_dir

    print("FirstLot local demo safe check")
    print("Safety: fixture CSVs only; no .env reads; no Supabase/API imports; no live DB writes.")
    print(f"Artifact check output: {out_dir}")

    try:
        _run([sys.executable, str(REGENERATE_SCRIPT), "--out", str(out_dir)], cwd=REPO_ROOT)

        if not args.skip_dashboard:
            _run(
                [
                    _npm_command(),
                    "test",
                    "--",
                    "--runTestsByPath",
                    str(DASHBOARD_SMOKE_TEST.relative_to(DASHBOARD_DIR)),
                    "--watchAll=false",
                ],
                cwd=DASHBOARD_DIR,
            )

        print("FirstLot local demo safe check passed.")
        return 0
    finally:
        if temp_dir is not None and args.keep_out:
            print(f"Kept generated artifacts at: {out_dir}")
        elif temp_dir is not None:
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    raise SystemExit(main())
