"""Regenerate checked-in FirstLot demo artifacts from local CSV fixtures.

Safety boundary: this script only reads synthetic fixture CSV files and writes local
CSV/JSON artifacts. It does not import dotenv, Supabase adapters, the API app, or
any live client integrations.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "firstlot_demo"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "cogs-dashboard" / "src" / "demo-output" / "firstlot_demo"
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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regenerate safe local FirstLot demo CSV/JSON artifacts."
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory (default: dashboard checked-in demo-output directory)",
    )
    parser.add_argument(
        "--generated-at",
        default=DEFAULT_GENERATED_AT,
        help="Deterministic ISO timestamp to embed in report generation metadata",
    )
    return parser.parse_args()


def _verify_artifacts(out_dir: Path) -> None:
    missing = [name for name in EXPECTED_ARTIFACTS if not (out_dir / name).is_file()]
    if missing:
        raise RuntimeError(f"Missing expected artifacts in {out_dir}: {', '.join(missing)}")

    for name in EXPECTED_ARTIFACTS:
        path = out_dir / name
        if path.suffix == ".json":
            with path.open() as handle:
                json.load(handle)
        elif path.stat().st_size == 0:
            raise RuntimeError(f"Artifact is empty: {path}")


def main() -> int:
    args = _parse_args()
    out_dir = Path(args.out).resolve()

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
        args.generated_at,
    ]

    print("Regenerating FirstLot demo artifacts from local fixtures only.", flush=True)
    print("Safety: no .env reads, no Supabase/API imports, no live DB writes.", flush=True)
    subprocess.run(command, cwd=REPO_ROOT, check=True)
    _verify_artifacts(out_dir)
    print(f"Verified {len(EXPECTED_ARTIFACTS)} artifacts in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
