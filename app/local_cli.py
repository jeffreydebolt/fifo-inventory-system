"""Safe local/demo CLI for FIFO CSV runs.

This entrypoint is intentionally local-file only. It does not import API,
Supabase, dotenv, or any live client adapters.
"""
import argparse
from datetime import datetime
from pathlib import Path

from core.csv_ingest import load_movement_csv, load_purchase_lots_csv
from core.output_files import write_fifo_report
from core.outputs import run_fifo_report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local FirstLot FIFO demo from CSV inputs.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Generate local FIFO output artifacts")
    run_parser.add_argument("--lots", required=True, help="Purchase lots CSV path")
    run_parser.add_argument("--movement", required=True, help="Movement/sales CSV path")
    run_parser.add_argument("--out", required=True, help="Output directory for CSV/JSON artifacts")
    run_parser.add_argument(
        "--generated-at",
        default="2026-06-03T23:00:00",
        help="Deterministic report timestamp as ISO datetime (default: fixture timestamp)",
    )
    run_parser.add_argument(
        "--strict-shortfalls",
        action="store_true",
        help="Do not partially allocate sales with insufficient inventory",
    )
    run_parser.add_argument(
        "--csv-only",
        action="store_true",
        help="Write CSV artifacts only; omit JSON copies",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.command != "run":
        raise AssertionError(f"Unsupported command: {args.command}")

    generated_at = datetime.fromisoformat(args.generated_at)
    inventory = load_purchase_lots_csv(args.lots, snapshot_timestamp=generated_at)
    sales = load_movement_csv(args.movement)
    report = run_fifo_report(
        inventory,
        sales,
        generated_at=generated_at,
        allow_partial_shortfalls=not args.strict_shortfalls,
    )
    written = write_fifo_report(report, Path(args.out), include_json=not args.csv_only)

    print("Local/demo FIFO run complete — no live DB writes.")
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
