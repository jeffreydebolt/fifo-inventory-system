"""Regenerate checked-in FirstLot demo artifacts from local CSV fixtures.

Safety boundary: this script only reads synthetic fixture CSV files and writes local
CSV/JSON artifacts. It does not import dotenv, Supabase adapters, the API app, or
any live client integrations.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "firstlot_demo"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "cogs-dashboard" / "src" / "demo-output" / "firstlot_demo"
DEFAULT_FIXED_OUTPUT_DIR = REPO_ROOT / "cogs-dashboard" / "src" / "demo-output" / "firstlot_demo_fixed"
DEFAULT_GENERATED_AT = "2026-06-03T23:00:00"
EXPECTED_ARTIFACTS = (
    "cogs_summary.csv",
    "cogs_summary.json",
    "remaining_layers.csv",
    "remaining_layers.json",
    "audit_trail.csv",
    "audit_trail.json",
    "shortfalls.csv",
    "shortfalls.json",
    "failed_sku_queue.csv",
    "failed_sku_queue.json",
    "cogs_detail.csv",
    "cogs_detail.json",
)
EXPECTED_FIXED_ARTIFACTS = (*EXPECTED_ARTIFACTS, "month_history.csv", "month_history.json")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regenerate safe local FirstLot demo CSV/JSON artifacts."
    )
    parser.add_argument(
        "--out",
        help="Output directory for v1 failing artifacts (default: dashboard checked-in demo-output directory)",
    )
    parser.add_argument(
        "--fixed-out",
        help="Optional output directory for v1-failed then v2-fixed rerun artifacts",
    )
    parser.add_argument(
        "--include-fixed-rerun",
        action="store_true",
        help="Also generate fixed-rerun artifacts from purchase_lots_fixed.csv",
    )
    parser.add_argument(
        "--generated-at",
        default=DEFAULT_GENERATED_AT,
        help="Deterministic ISO timestamp to embed in report generation metadata",
    )
    return parser.parse_args()


def _verify_artifacts(out_dir: Path, expected_artifacts: tuple[str, ...] = EXPECTED_ARTIFACTS) -> None:
    missing = [name for name in expected_artifacts if not (out_dir / name).is_file()]
    if missing:
        raise RuntimeError(f"Missing expected artifacts in {out_dir}: {', '.join(missing)}")

    for name in expected_artifacts:
        path = out_dir / name
        if path.suffix == ".json":
            with path.open() as handle:
                json.load(handle)
        elif path.stat().st_size == 0:
            raise RuntimeError(f"Artifact is empty: {path}")


def _run_cli(command: list[str]) -> None:
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def _reset_output_dir(out_dir: Path) -> None:
    """Keep regenerated demo artifacts deterministic without touching non-output paths."""

    resolved = out_dir.resolve()
    allowed_roots = [
        (REPO_ROOT / "cogs-dashboard" / "src" / "demo-output").resolve(),
        Path(tempfile.gettempdir()).resolve(),
        Path("/tmp").resolve(),
        Path("/private/tmp").resolve(),
    ]
    if not any(resolved == root or root in resolved.parents for root in allowed_roots):
        raise RuntimeError(f"Refusing to reset non-demo output directory: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def _run_v1(out_dir: Path, generated_at: str) -> None:
    command = [
        sys.executable,
        "-m",
        "app.local_cli",
        "run",
        "--lots",
        str(FIXTURE_DIR / "purchase_lots.csv"),
        "--movement",
        str(FIXTURE_DIR / "movement.csv"),
        "--out",
        str(out_dir),
        "--generated-at",
        generated_at,
    ]
    _run_cli(command)


def _run_fixed_rerun(fixed_out_dir: Path, generated_at: str) -> None:
    """Write a demo folder that preserves v1 history and final v2 fixed artifacts."""

    _run_cli(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "run",
            "--lots",
            str(FIXTURE_DIR / "purchase_lots.csv"),
            "--movement",
            str(FIXTURE_DIR / "movement.csv"),
            "--out",
            str(fixed_out_dir),
            "--generated-at",
            generated_at,
            "--period",
            "2026-05",
            "--note",
            "v1 fixture run queued SKU-A shortfall for local fix/rerun",
        ]
    )
    _run_cli(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "run",
            "--lots",
            str(FIXTURE_DIR / "purchase_lots_fixed.csv"),
            "--movement",
            str(FIXTURE_DIR / "movement.csv"),
            "--out",
            str(fixed_out_dir),
            "--generated-at",
            generated_at,
            "--period",
            "2026-05",
            "--reopen",
            "--note",
            "v2 fixed rerun uses corrected purchase_lots_fixed.csv and clears queue",
        ]
    )


def main() -> int:
    args = _parse_args()
    out_dir = Path(args.out or DEFAULT_OUTPUT_DIR).resolve()
    should_generate_default_fixed = args.out is None and args.fixed_out is None
    fixed_out_dir = Path(args.fixed_out or DEFAULT_FIXED_OUTPUT_DIR).resolve()

    print("Regenerating FirstLot demo artifacts from local fixtures only.", flush=True)
    print("Safety: no .env reads, no Supabase/API imports, no live DB writes.", flush=True)
    _reset_output_dir(out_dir)
    _run_v1(out_dir, args.generated_at)
    _verify_artifacts(out_dir)
    print(f"Verified {len(EXPECTED_ARTIFACTS)} artifacts in {out_dir}")

    if args.include_fixed_rerun or args.fixed_out or should_generate_default_fixed:
        print("Regenerating FirstLot fixed-rerun artifacts from purchase_lots_fixed.csv.", flush=True)
        _reset_output_dir(fixed_out_dir)
        _run_fixed_rerun(fixed_out_dir, args.generated_at)
        _verify_artifacts(fixed_out_dir, EXPECTED_FIXED_ARTIFACTS)
        print(f"Verified {len(EXPECTED_FIXED_ARTIFACTS)} artifacts in {fixed_out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
