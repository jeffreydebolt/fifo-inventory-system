"""Run a safe generic FirstLot client-style fixture workflow.

Safety boundary: this wrapper accepts local CSV files only, shells out to the local
FirstLot CLI, and writes local artifacts. It does not import dotenv, Supabase,
API clients, or live adapters.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GENERATED_AT = "2026-06-05T03:30:00"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and run a local FirstLot client-style fixture directory."
    )
    parser.add_argument(
        "--fixture-dir",
        required=True,
        help="Directory containing purchase_lots.csv and movement.csv",
    )
    parser.add_argument("--out", required=True, help="Local output artifact directory")
    parser.add_argument("--period", required=True, help="Close period, e.g. 2026-06")
    parser.add_argument(
        "--generated-at",
        default=DEFAULT_GENERATED_AT,
        help="Deterministic ISO timestamp for generated artifacts",
    )
    parser.add_argument(
        "--expect-clear",
        action="store_true",
        help="Fail if the generated failed-SKU queue is not clear",
    )
    parser.add_argument(
        "--reopen",
        action="store_true",
        help="Pass --reopen to the local CLI for intentional reruns of the same output period",
    )
    parser.add_argument(
        "--clean-output",
        action="store_true",
        help="Delete the output directory first; only allowed under the system temp directory",
    )
    return parser.parse_args()


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Command failed with exit code "
            f"{result.returncode}: {' '.join(command)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def _safe_clean_output(out_dir: Path) -> None:
    resolved = out_dir.resolve()
    allowed_roots = {
        Path(tempfile.gettempdir()).resolve(),
        Path("/tmp").resolve(),
        Path("/private/tmp").resolve(),
    }
    if not any(resolved == root or root in resolved.parents for root in allowed_roots):
        raise RuntimeError(f"Refusing to clean non-temp output directory: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def _json_file(path: Path):
    with path.open() as handle:
        return json.load(handle)


def main() -> int:
    args = _parse_args()
    fixture_dir = Path(args.fixture_dir)
    lots_path = fixture_dir / "purchase_lots.csv"
    movement_path = fixture_dir / "movement.csv"
    out_dir = Path(args.out)

    if args.clean_output:
        _safe_clean_output(out_dir)

    validate_result = _run(
        [
            sys.executable,
            "-m",
            "app.local_cli",
            "validate",
            "--lots",
            str(lots_path),
            "--movement",
            str(movement_path),
        ]
    )
    validation_payload = json.loads(validate_result.stdout)

    run_command = [
        sys.executable,
        "-m",
        "app.local_cli",
        "run",
        "--lots",
        str(lots_path),
        "--movement",
        str(movement_path),
        "--out",
        str(out_dir),
        "--generated-at",
        args.generated_at,
        "--period",
        args.period,
        "--note",
        f"generic client-test fixture run from {fixture_dir}",
    ]
    if args.reopen:
        run_command.append("--reopen")
    _run(run_command)

    queue_command = [
        sys.executable,
        "-m",
        "app.local_cli",
        "failed-skus",
        "--out",
        str(out_dir),
        "--period",
        args.period,
    ]
    if args.expect_clear:
        queue_command.append("--assert-clear")
    queue_payload = _run(queue_command)
    raw_queue_result = json.loads(queue_payload.stdout)
    if args.expect_clear:
        queue_result = raw_queue_result
    else:
        total_shortfall = sum(row["shortfall_quantity"] for row in raw_queue_result)
        queue_result = {
            "clear": len(raw_queue_result) == 0,
            "queue_record_count": len(raw_queue_result),
            "total_shortfall_quantity": total_shortfall,
        }

    cogs_summary = _json_file(out_dir / "cogs_summary.json")
    remaining_layers = _json_file(out_dir / "remaining_layers.json")
    close_packet = _json_file(out_dir / "close_packet.json")
    remaining_inventory_value = sum(
        Decimal(row["remaining_value"]) for row in remaining_layers
    )
    summary = {
        "read_only_local_fixture_workflow": True,
        "mutations_performed": [],
        "fixture_dir": str(fixture_dir),
        "out": str(out_dir),
        "period": args.period,
        "validation": validation_payload,
        "failed_sku_check": queue_result,
        "artifact_count": len(close_packet["artifact_files"]),
        "total_cogs": close_packet["summary"]["total_cogs"],
        "remaining_inventory_value": f"{remaining_inventory_value:.2f}",
        "skus": [row["sku"] for row in cogs_summary],
        "safety": "local fixture CSVs only; no .env, no Supabase/API imports, no live DB writes",
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
