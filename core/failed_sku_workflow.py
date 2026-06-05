"""Local failed-SKU queue helpers for FirstLot fix/rerun workflow.

This module is deliberately local-artifact only. It reads generated
``failed_sku_queue`` files and returns operator guidance; it never imports live
services and never mutates inventory, databases, or generated COGS artifacts.
"""
from __future__ import annotations

import csv
import json
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class FailedSKUQueueRecord:
    """One row from a generated failed_sku_queue artifact."""

    sku: str
    period: str
    failure_count: int
    first_sale_date: str
    last_sale_date: str
    requested_quantity: int
    allocated_quantity: int
    shortfall_quantity: int
    reasons: str
    status: str


QUEUE_FIELDNAMES = [
    "sku",
    "period",
    "failure_count",
    "first_sale_date",
    "last_sale_date",
    "requested_quantity",
    "allocated_quantity",
    "shortfall_quantity",
    "reasons",
    "status",
]


def queue_paths(out_dir: str | Path) -> tuple[Path, Path]:
    out_path = Path(out_dir)
    return out_path / "failed_sku_queue.json", out_path / "failed_sku_queue.csv"


def _record_from_mapping(row: dict) -> FailedSKUQueueRecord:
    return FailedSKUQueueRecord(
        sku=row["sku"],
        period=row["period"],
        failure_count=int(row["failure_count"]),
        first_sale_date=row["first_sale_date"],
        last_sale_date=row["last_sale_date"],
        requested_quantity=int(row["requested_quantity"]),
        allocated_quantity=int(row["allocated_quantity"]),
        shortfall_quantity=int(row["shortfall_quantity"]),
        reasons=row["reasons"],
        status=row.get("status", "NEEDS_FIX_RERUN"),
    )


def load_failed_sku_queue(out_dir: str | Path) -> list[FailedSKUQueueRecord]:
    """Load a generated failed SKU queue, preferring JSON and falling back to CSV."""

    json_path, csv_path = queue_paths(out_dir)
    if json_path.exists():
        with json_path.open() as handle:
            rows = json.load(handle)
        return [_record_from_mapping(row) for row in rows]
    if csv_path.exists():
        with csv_path.open(newline="") as handle:
            return [_record_from_mapping(row) for row in csv.DictReader(handle)]
    raise FileNotFoundError(f"No failed_sku_queue.json/csv found under {Path(out_dir)}")


def filter_queue(
    records: Iterable[FailedSKUQueueRecord],
    *,
    period: str | None = None,
    sku: str | None = None,
) -> list[FailedSKUQueueRecord]:
    """Return queue records narrowed by period and/or SKU."""

    filtered = list(records)
    if period:
        filtered = [record for record in filtered if record.period == period]
    if sku:
        filtered = [record for record in filtered if record.sku == sku]
    return sorted(filtered, key=lambda row: (row.period, row.sku))


def _shell_command(args: list[str]) -> str:
    """Return a copy/paste-safe shell command string for display in JSON output."""

    return " ".join(shlex.quote(str(arg)) for arg in args)


def _pluralize(count: int, singular: str, plural: str | None = None) -> str:
    if count == 1:
        return f"1 {singular}"
    return f"{count} {plural or singular + 's'}"


def _build_summary(
    records: list[FailedSKUQueueRecord],
    *,
    total_shortfall_quantity: int,
    affected_periods: list[str],
    affected_skus: list[str],
) -> str:
    if not records:
        return "No failed SKU queue rows match the requested filters; no CSV fix is currently required."
    return (
        f"{_pluralize(len(records), 'failed SKU queue row')} across "
        f"{_pluralize(len(affected_skus), 'SKU')} and "
        f"{_pluralize(len(affected_periods), 'period')} requires "
        f"{_pluralize(total_shortfall_quantity, 'additional available unit')} before rerun."
    )


def _build_recommended_next_action(records: list[FailedSKUQueueRecord], affected_periods: list[str]) -> str:
    if not records:
        return "Run the completion check command; if it remains clear, continue month-close review."
    if len(records) == 1:
        record = records[0]
        period_text = record.period
        return (
            f"Add at least {record.shortfall_quantity} unit(s) of {record.sku} available before "
            f"{record.first_sale_date}, then rerun {period_text} with --reopen."
        )
    period_text = affected_periods[0] if len(affected_periods) == 1 else "the affected periods"
    return (
        "Fix the local purchase lots or sales CSV so each recommended_csv_fixes row has enough "
        f"available FIFO quantity, then rerun {period_text} with --reopen or the correct prior-month correction mode."
    )


def _build_completion_check_args(
    out_dir: str | Path,
    *,
    period: str | None,
    sku: str | None,
    affected_periods: list[str],
    affected_skus: list[str],
) -> list[str]:
    args = ["python", "-m", "app.local_cli", "failed-skus", "--out", str(Path(out_dir))]
    check_period = period or (affected_periods[0] if len(affected_periods) == 1 else None)
    check_sku = sku or (affected_skus[0] if len(affected_skus) == 1 and period else None)
    if check_period:
        args.extend(["--period", check_period])
    if check_sku:
        args.extend(["--sku", check_sku])
    args.append("--assert-clear")
    return args


def build_fix_plan(
    out_dir: str | Path,
    *,
    period: str | None = None,
    sku: str | None = None,
    lots_path: str | None = None,
    movement_path: str | None = None,
    note: str = "",
) -> dict:
    """Build a read-only local plan for fixing queue rows and rerunning FIFO.

    The returned plan is intentionally prescriptive but non-mutating: operators
    can review the missing quantities, fix purchase lots/sales CSV inputs, then
    rerun ``app.local_cli run`` with ``--reopen`` or ``--append-prior-month``.
    """

    records = filter_queue(load_failed_sku_queue(out_dir), period=period, sku=sku)
    total_shortfall_quantity = sum(record.shortfall_quantity for record in records)
    affected_periods = sorted({record.period for record in records})
    affected_skus = sorted({record.sku for record in records})

    rerun_args = ["python", "-m", "app.local_cli", "run"]
    if lots_path:
        rerun_args.extend(["--lots", lots_path])
    if movement_path:
        rerun_args.extend(["--movement", movement_path])
    rerun_args.extend(["--out", str(Path(out_dir))])
    if len(affected_periods) == 1:
        rerun_args.extend(["--period", affected_periods[0], "--reopen"])

    completion_check_args = _build_completion_check_args(
        out_dir,
        period=period,
        sku=sku,
        affected_periods=affected_periods,
        affected_skus=affected_skus,
    )

    return {
        "read_only": True,
        "mutations_performed": [],
        "summary": _build_summary(
            records,
            total_shortfall_quantity=total_shortfall_quantity,
            affected_periods=affected_periods,
            affected_skus=affected_skus,
        ),
        "recommended_next_action": _build_recommended_next_action(records, affected_periods),
        "suggested_rerun_command": _shell_command(rerun_args),
        "completion_check_command": _shell_command(completion_check_args),
        "note": note,
        "queue_record_count": len(records),
        "affected_periods": affected_periods,
        "affected_skus": affected_skus,
        "total_shortfall_quantity": total_shortfall_quantity,
        "queue_records": [asdict(record) for record in records],
        "recommended_csv_fixes": [
            {
                "sku": record.sku,
                "period": record.period,
                "minimum_additional_available_units_needed": record.shortfall_quantity,
                "reason": record.reasons,
                "status": record.status,
            }
            for record in records
        ],
        "rerun_command_args": rerun_args,
        "operator_steps": [
            "Open failed_sku_queue.csv/json and confirm each SKU-period shortfall is expected.",
            "Fix the local purchase lots CSV, sales CSV, or month selection so available FIFO units cover the queue rows.",
            "Rerun the local FIFO CLI into the same output folder with --reopen for the affected closed period, or --append-prior-month for a prior-month correction.",
            "Run failed-skus --assert-clear for the period before considering the fix complete.",
        ],
    }


def assert_queue_clear(out_dir: str | Path, *, period: str | None = None, sku: str | None = None) -> dict:
    """Return queue-clear status; callers can turn non-clear status into exit 1."""

    records = filter_queue(load_failed_sku_queue(out_dir), period=period, sku=sku)
    return {
        "clear": len(records) == 0,
        "queue_record_count": len(records),
        "total_shortfall_quantity": sum(record.shortfall_quantity for record in records),
        "queue_records": [asdict(record) for record in records],
    }
