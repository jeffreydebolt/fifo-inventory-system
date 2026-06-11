"""Local output file writer for deterministic FIFO report artifacts."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from .outputs import FIFOReport, dataclass_row_dict


CSV_SECTIONS = {
    "cogs_summary": [
        "sku",
        "period",
        "total_quantity_sold",
        "total_cogs",
        "average_unit_cost",
    ],
    "remaining_layers": [
        "lot_id",
        "sku",
        "received_date",
        "original_quantity",
        "remaining_quantity",
        "unit_cost",
        "remaining_value",
    ],
    "audit_trail": [
        "sale_id",
        "sku",
        "sale_date",
        "lot_id",
        "lot_received_date",
        "quantity",
        "unit_cost",
        "total_cost",
    ],
    "shortfalls": [
        "sale_id",
        "sku",
        "sale_date",
        "requested_quantity",
        "allocated_quantity",
        "shortfall_quantity",
        "available_quantity",
        "reason",
        "message",
    ],
    "failed_sku_queue": [
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
    ],
    "cogs_detail": [
        "sku",
        "period",
        "total_quantity_sold",
        "merchandise_cost",
        "shipping_cost",
        "total_cost",
        "average_cost",
    ],
}


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_fifo_report(report: FIFOReport, out_dir: str | Path, include_json: bool = True) -> list[Path]:
    """Write canonical local FIFO artifacts and return paths written."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    sections = {
        "cogs_summary": report.cogs_summary,
        "remaining_layers": report.remaining_layers,
        "audit_trail": report.audit_trail,
        "shortfalls": report.shortfalls,
        "failed_sku_queue": report.failed_sku_queue,
        "cogs_detail": report.cogs_detail,
    }
    written: list[Path] = []

    for section_name, rows in sections.items():
        serialized_rows = [dataclass_row_dict(row) for row in rows]
        csv_path = out_path / f"{section_name}.csv"
        _write_csv(csv_path, CSV_SECTIONS[section_name], serialized_rows)
        written.append(csv_path)

        if include_json:
            json_path = out_path / f"{section_name}.json"
            with json_path.open("w") as handle:
                json.dump(serialized_rows, handle, indent=2, sort_keys=True)
                handle.write("\n")
            written.append(json_path)

    return written
