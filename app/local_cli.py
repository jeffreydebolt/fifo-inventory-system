"""Safe local/demo CLI for FIFO CSV runs.

This entrypoint is intentionally local-file only. It does not import API,
Supabase, dotenv, or any live client adapters.
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

from core.close_packet import write_close_packet
from core.csv_ingest import load_movement_csv, load_purchase_lots_csv
from core.csv_validation import validate_firstlot_csvs
from core.failed_sku_workflow import assert_queue_clear, build_fix_plan, load_failed_sku_queue
from core.lots_normalizer import (
    inspect_lot_csv,
    inspect_movement_csv,
    normalize_lot_csv,
    normalize_movement_csv,
)
from core.month_history import append_month_close_record, build_rollback_plan, load_month_history
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
    run_parser.add_argument(
        "--period",
        help="Optional close period (YYYY-MM) to append to local month_history CSV/JSON",
    )
    run_parser.add_argument(
        "--reopen",
        action="store_true",
        help="Allow rerun of an existing period and mark the history row REOPENED",
    )
    run_parser.add_argument(
        "--append-prior-month",
        action="store_true",
        help="Allow appending/reclosing a prior period and mark history APPENDED_PRIOR_MONTH",
    )
    run_parser.add_argument(
        "--note",
        default="",
        help="Optional local audit note for month history records",
    )
    run_parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Explicitly bypass pre-run CSV validation for local/debug use",
    )
    run_parser.add_argument(
        "--no-close-packet",
        action="store_true",
        help="Do not write close_packet.json/md for this local run",
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate local FirstLot CSV inputs without running FIFO or writing artifacts",
    )
    validate_parser.add_argument("--lots", required=True, help="Purchase lots CSV path")
    validate_parser.add_argument("--movement", required=True, help="Movement/sales CSV path")

    inspect_lots_parser = subparsers.add_parser(
        "inspect-lots",
        help="Inspect a client-shaped purchase-lot CSV and infer FirstLot column mapping",
    )
    inspect_lots_parser.add_argument("--lots", required=True, help="Purchase lots CSV path")
    inspect_lots_parser.add_argument(
        "--sample-limit",
        type=int,
        default=3,
        help="Number of projected sample rows to include in JSON output",
    )

    normalize_lots_parser = subparsers.add_parser(
        "normalize-lots",
        help="Normalize a client-shaped purchase-lot CSV to strict FirstLot purchase_lots.csv",
    )
    normalize_lots_parser.add_argument("--lots", required=True, help="Input purchase lots CSV path")
    normalize_lots_parser.add_argument("--out", required=True, help="Output normalized purchase_lots.csv path")

    inspect_movement_parser = subparsers.add_parser(
        "inspect-movement",
        help="Inspect a client-shaped sales/movement CSV and infer FirstLot column mapping",
    )
    inspect_movement_parser.add_argument("--movement", required=True, help="Movement/sales CSV path")
    inspect_movement_parser.add_argument(
        "--sample-limit",
        type=int,
        default=3,
        help="Number of projected sample rows to include in JSON output",
    )

    normalize_movement_parser = subparsers.add_parser(
        "normalize-movement",
        help="Normalize a client-shaped sales/movement CSV to strict FirstLot movement.csv",
    )
    normalize_movement_parser.add_argument("--movement", required=True, help="Input movement/sales CSV path")
    normalize_movement_parser.add_argument("--out", required=True, help="Output normalized movement.csv path")

    history_parser = subparsers.add_parser("history", help="Print local month close history")
    history_parser.add_argument("--out", required=True, help="Output directory containing month_history.json")

    rollback_parser = subparsers.add_parser(
        "rollback-plan",
        help="Print a read-only rollback plan for a local period; performs no mutations",
    )
    rollback_parser.add_argument("--out", required=True, help="Output directory containing month_history.json")
    rollback_parser.add_argument("--period", required=True, help="Close period (YYYY-MM)")
    rollback_parser.add_argument("--generated-at", default="2026-06-03T23:00:00")
    rollback_parser.add_argument("--note", default="")

    failed_parser = subparsers.add_parser(
        "failed-skus",
        help="Review failed SKU queue rows or assert a local fix/rerun cleared them",
    )
    failed_parser.add_argument("--out", required=True, help="Output directory containing failed_sku_queue.json/csv")
    failed_parser.add_argument("--period", help="Optional period filter (YYYY-MM)")
    failed_parser.add_argument("--sku", help="Optional SKU filter")
    failed_parser.add_argument(
        "--assert-clear",
        action="store_true",
        help="Exit non-zero if matching failed SKU queue rows remain",
    )

    fix_parser = subparsers.add_parser(
        "fix-plan",
        help="Print a read-only failed-SKU fix/rerun plan; performs no mutations",
    )
    fix_parser.add_argument("--out", required=True, help="Output directory containing failed_sku_queue.json/csv")
    fix_parser.add_argument("--period", help="Optional period filter (YYYY-MM)")
    fix_parser.add_argument("--sku", help="Optional SKU filter")
    fix_parser.add_argument("--lots", help="Optional purchase lots CSV path to include in rerun args")
    fix_parser.add_argument("--movement", help="Optional movement/sales CSV path to include in rerun args")
    fix_parser.add_argument("--note", default="")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.command == "inspect-lots":
        inspection = inspect_lot_csv(args.lots, sample_limit=args.sample_limit)
        print(json.dumps(inspection.to_dict(), indent=2, sort_keys=True))
        return 0 if inspection.ready_to_normalize else 1

    if args.command == "normalize-lots":
        result = normalize_lot_csv(args.lots, args.out)
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0 if result.ok else 1

    if args.command == "inspect-movement":
        inspection = inspect_movement_csv(args.movement, sample_limit=args.sample_limit)
        print(json.dumps(inspection.to_dict(), indent=2, sort_keys=True))
        return 0 if inspection.ready_to_normalize else 1

    if args.command == "normalize-movement":
        result = normalize_movement_csv(args.movement, args.out)
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0 if result.ok else 1

    if args.command == "history":
        rows = [record.__dict__ for record in load_month_history(args.out)]
        print(json.dumps(rows, indent=2, sort_keys=True))
        return 0

    if args.command == "rollback-plan":
        generated_at = datetime.fromisoformat(args.generated_at)
        plan = build_rollback_plan(
            args.out,
            args.period,
            recorded_at=generated_at,
            note=args.note,
        )
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0

    if args.command == "failed-skus":
        if args.assert_clear:
            result = assert_queue_clear(args.out, period=args.period, sku=args.sku)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["clear"] else 1
        rows = load_failed_sku_queue(args.out)
        if args.period:
            rows = [record for record in rows if record.period == args.period]
        if args.sku:
            rows = [record for record in rows if record.sku == args.sku]
        print(json.dumps([record.__dict__ for record in rows], indent=2, sort_keys=True))
        return 0

    if args.command == "fix-plan":
        plan = build_fix_plan(
            args.out,
            period=args.period,
            sku=args.sku,
            lots_path=args.lots,
            movement_path=args.movement,
            note=args.note,
        )
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0

    if args.command == "validate":
        result = validate_firstlot_csvs(args.lots, args.movement)
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0 if result.valid else 1

    if args.command != "run":
        raise AssertionError(f"Unsupported command: {args.command}")

    validation = validate_firstlot_csvs(args.lots, args.movement)
    if not validation.valid and not args.skip_validation:
        print(json.dumps(validation.to_dict(), indent=2, sort_keys=True))
        return 1

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
    history_record = None
    if args.period:
        history_record, history_files = append_month_close_record(
            report,
            Path(args.out),
            args.period,
            recorded_at=generated_at,
            reopen=args.reopen,
            append_prior_month=args.append_prior_month,
            note=args.note,
        )
        written.extend(history_files)
    if not args.no_close_packet and not args.csv_only:
        close_packet_files = write_close_packet(
            report,
            Path(args.out),
            lots_path=args.lots,
            movement_path=args.movement,
            artifact_paths=written,
            period=args.period,
            history_record=history_record,
        )
        written.extend(close_packet_files)

    print("Local/demo FIFO run complete — no live DB writes.")
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
