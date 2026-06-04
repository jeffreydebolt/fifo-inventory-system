"""Local month-close history helpers for FirstLot FIFO runs.

This module is intentionally file-local and deterministic. It does not import
Supabase, dotenv, API adapters, or any live client integrations. The history file
is an append-only audit record in the caller's chosen output directory.
"""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Literal

from .outputs import FIFOReport, dataclass_row_dict, decimal_to_string

MonthCloseStatus = Literal["CLOSED", "REOPENED", "APPENDED_PRIOR_MONTH", "ROLLBACK_PLANNED"]


@dataclass(frozen=True)
class MonthHistoryRecord:
    """One append-only local month close history row."""

    period: str
    status: MonthCloseStatus
    run_sequence: int
    generated_at: str
    recorded_at: str
    cogs_sku_count: int
    total_quantity_sold: int
    total_cogs: str
    shortfall_sku_count: int
    shortfall_quantity: int
    note: str


FIELDNAMES = [
    "period",
    "status",
    "run_sequence",
    "generated_at",
    "recorded_at",
    "cogs_sku_count",
    "total_quantity_sold",
    "total_cogs",
    "shortfall_sku_count",
    "shortfall_quantity",
    "note",
]


def history_paths(out_dir: str | Path) -> tuple[Path, Path]:
    out_path = Path(out_dir)
    return out_path / "month_history.json", out_path / "month_history.csv"


def load_month_history(out_dir: str | Path) -> list[MonthHistoryRecord]:
    """Load local append-only month history if present."""
    json_path, _ = history_paths(out_dir)
    if not json_path.exists():
        return []
    with json_path.open() as handle:
        rows = json.load(handle)
    return [MonthHistoryRecord(**row) for row in rows]


def _write_history(out_dir: str | Path, records: Iterable[MonthHistoryRecord]) -> list[Path]:
    json_path, csv_path = history_paths(out_dir)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(record) for record in records]
    with json_path.open("w") as handle:
        json.dump(rows, handle, indent=2, sort_keys=True)
        handle.write("\n")
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return [csv_path, json_path]


def append_month_close_record(
    report: FIFOReport,
    out_dir: str | Path,
    period: str,
    *,
    recorded_at: datetime,
    reopen: bool = False,
    append_prior_month: bool = False,
    note: str = "",
) -> tuple[MonthHistoryRecord, list[Path]]:
    """Append a local month-close history record and persist CSV/JSON copies.

    Re-running an already closed period requires either ``reopen=True`` or
    ``append_prior_month=True`` so accidental overwrite/reclose is blocked.
    """
    records = load_month_history(out_dir)
    period_records = [record for record in records if record.period == period]
    if period_records and not (reopen or append_prior_month):
        raise ValueError(
            f"Period {period} already has history; rerun with --reopen or --append-prior-month"
        )

    if reopen:
        status: MonthCloseStatus = "REOPENED"
    elif append_prior_month:
        status = "APPENDED_PRIOR_MONTH"
    else:
        status = "CLOSED"

    cogs_rows = [dataclass_row_dict(row) for row in report.cogs_summary if row.period == period]
    shortfall_rows = [
        dataclass_row_dict(row)
        for row in report.shortfalls
        if row.sale_date.strftime("%Y-%m") == period
    ]
    total_cogs = sum(
        (row.total_cogs for row in report.cogs_summary if row.period == period),
        Decimal("0"),
    )
    record = MonthHistoryRecord(
        period=period,
        status=status,
        run_sequence=len(period_records) + 1,
        generated_at=report.generated_at.isoformat(),
        recorded_at=recorded_at.isoformat(),
        cogs_sku_count=len({row["sku"] for row in cogs_rows}),
        total_quantity_sold=sum(int(row["total_quantity_sold"]) for row in cogs_rows),
        total_cogs=decimal_to_string(total_cogs),
        shortfall_sku_count=len({row["sku"] for row in shortfall_rows}),
        shortfall_quantity=sum(int(row["shortfall_quantity"]) for row in shortfall_rows),
        note=note,
    )
    written = _write_history(out_dir, [*records, record])
    return record, written


def build_rollback_plan(out_dir: str | Path, period: str, *, recorded_at: datetime, note: str = "") -> dict:
    """Return a read-only rollback plan for a local month history period.

    This intentionally does not delete or mutate any artifact. It tells an
    operator which local files would be reviewed/restored in a future approved
    rollback workflow.
    """
    records = load_month_history(out_dir)
    period_records = [record for record in records if record.period == period]
    if not period_records:
        raise ValueError(f"No local month history found for period {period}")
    latest = period_records[-1]
    return {
        "period": period,
        "planned_at": recorded_at.isoformat(),
        "note": note,
        "latest_history_status": latest.status,
        "latest_run_sequence": latest.run_sequence,
        "read_only": True,
        "mutations_performed": [],
        "operator_steps": [
            "Review month_history.csv/json for the period and confirm intended prior run_sequence.",
            "Compare cogs_summary, remaining_layers, audit_trail, shortfalls, and failed_sku_queue artifacts from the target run.",
            "If approved, restore the selected artifact set in a separate reviewed local-file change; do not touch live data.",
        ],
    }
