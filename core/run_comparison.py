"""Read-only comparison helpers for local FirstLot rerun/version artifacts.

This module compares two generated local artifact directories so an operator can
review a fix/rerun delta before finalizing a month. It reads JSON artifacts only
and performs no file, database, API, or live-client mutations.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

MONEY_ZERO = Decimal("0.00")


def compare_run_artifacts(before_dir: str | Path, after_dir: str | Path, *, period: str | None = None) -> dict:
    """Return SKU-level and run-level deltas between two local FIFO artifact folders."""

    before_path = Path(before_dir)
    after_path = Path(after_dir)
    before_rows = _cogs_rows_by_sku(before_path, period=period)
    after_rows = _cogs_rows_by_sku(after_path, period=period)
    before_queue = _failed_queue(before_path, period=period)
    after_queue = _failed_queue(after_path, period=period)
    skus = sorted(set(before_rows) | set(after_rows))
    sku_deltas = [_sku_delta(sku, before_rows.get(sku), after_rows.get(sku)) for sku in skus]
    before_total_cogs = sum((_money(row.get("total_cost", "0.00")) for row in before_rows.values()), MONEY_ZERO)
    after_total_cogs = sum((_money(row.get("total_cost", "0.00")) for row in after_rows.values()), MONEY_ZERO)

    return {
        "read_only": True,
        "mutations_performed": [],
        "period": period or "ALL_PERIODS",
        "before_dir": str(before_path),
        "after_dir": str(after_path),
        "summary": {
            "before_total_cogs": _fmt(before_total_cogs),
            "after_total_cogs": _fmt(after_total_cogs),
            "delta_total_cogs": _fmt(after_total_cogs - before_total_cogs),
            "before_failed_sku_count": len({row["sku"] for row in before_queue}),
            "after_failed_sku_count": len({row["sku"] for row in after_queue}),
            "failed_sku_delta": len({row["sku"] for row in after_queue}) - len({row["sku"] for row in before_queue}),
            "sku_delta_count": len([row for row in sku_deltas if row["changed"]]),
        },
        "sku_deltas": sku_deltas,
        "operator_next_step": (
            "Review SKU deltas, confirm failed SKU queue is clear for fixed run, then retain both local artifact folders as run-version audit support."
        ),
    }


def _load_json(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Missing local artifact: {path}")
    with path.open() as handle:
        rows = json.load(handle)
    if not isinstance(rows, list):
        raise ValueError(f"Expected a JSON list in {path}")
    return rows


def _cogs_rows_by_sku(out_dir: Path, *, period: str | None) -> dict[str, dict]:
    rows = _load_json(out_dir / "cogs_detail.json")
    if period:
        rows = [row for row in rows if row.get("period") == period]
    return {row["sku"]: row for row in rows}


def _failed_queue(out_dir: Path, *, period: str | None) -> list[dict]:
    rows = _load_json(out_dir / "failed_sku_queue.json")
    if period:
        rows = [row for row in rows if row.get("period") == period]
    return rows


def _money(value: str | int | float | None) -> Decimal:
    if value is None:
        return MONEY_ZERO
    return Decimal(str(value))


def _int(value: str | int | None) -> int:
    if value is None:
        return 0
    return int(value)


def _fmt(value: Decimal) -> str:
    return format(value.quantize(MONEY_ZERO), "f")


def _sku_delta(sku: str, before: dict | None, after: dict | None) -> dict:
    before_units = _int(before.get("total_quantity_sold") if before else None)
    after_units = _int(after.get("total_quantity_sold") if after else None)
    before_total = _money(before.get("total_cost") if before else None)
    after_total = _money(after.get("total_cost") if after else None)
    before_average = _money(before.get("average_cost") if before else None)
    after_average = _money(after.get("average_cost") if after else None)
    return {
        "sku": sku,
        "before_units_sold": before_units,
        "after_units_sold": after_units,
        "delta_units_sold": after_units - before_units,
        "before_total_cost": _fmt(before_total),
        "after_total_cost": _fmt(after_total),
        "delta_total_cost": _fmt(after_total - before_total),
        "before_average_cost": _fmt(before_average),
        "after_average_cost": _fmt(after_average),
        "changed": before_units != after_units or before_total != after_total or before_average != after_average,
    }
