"""Local FirstLot close packet writer.

The close packet summarizes a fixture/local FIFO run for client-test readiness.
It is deterministic, dependency-free, and performs no live service access.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from .month_history import MonthHistoryRecord
from .outputs import FIFOReport, decimal_to_string

SAFETY_MODE = "local_fixture_only_no_live_writes"


def write_close_packet(
    report: FIFOReport,
    out_dir: str | Path,
    *,
    lots_path: str | Path,
    movement_path: str | Path,
    artifact_paths: list[Path],
    period: str | None = None,
    history_record: MonthHistoryRecord | None = None,
) -> list[Path]:
    """Write close_packet.json and close_packet.md for a local FIFO run."""

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    packet = build_close_packet(
        report,
        out_path,
        lots_path=lots_path,
        movement_path=movement_path,
        artifact_paths=artifact_paths,
        period=period,
        history_record=history_record,
    )

    json_path = out_path / "close_packet.json"
    md_path = out_path / "close_packet.md"
    with json_path.open("w") as handle:
        json.dump(packet, handle, indent=2, sort_keys=True)
        handle.write("\n")
    md_path.write_text(_packet_markdown(packet), encoding="utf-8")
    return [json_path, md_path]


def build_close_packet(
    report: FIFOReport,
    out_dir: Path,
    *,
    lots_path: str | Path,
    movement_path: str | Path,
    artifact_paths: list[Path],
    period: str | None = None,
    history_record: MonthHistoryRecord | None = None,
) -> dict:
    """Build the close-packet dictionary without writing files."""

    periods = sorted({row.period for row in report.cogs_summary} | {row.period for row in report.failed_sku_queue})
    packet_period = period or (periods[0] if len(periods) == 1 else "MULTI_PERIOD")
    total_cogs = sum((row.total_cogs for row in report.cogs_summary), Decimal("0"))
    total_units = sum(row.total_quantity_sold for row in report.cogs_summary)
    shortfall_quantity = sum(row.shortfall_quantity for row in report.failed_sku_queue)
    failed_skus = sorted({row.sku for row in report.failed_sku_queue})
    processed_skus = sorted({row.sku for row in report.cogs_summary})
    review_out_dir = _display_path(out_dir)

    return {
        "packet_type": "firstlot_local_month_close",
        "safety_mode": SAFETY_MODE,
        "live_mutations_performed": [],
        "period": packet_period,
        "periods_in_outputs": periods,
        "generated_at": report.generated_at.isoformat(),
        "input_files": {
            "purchase_lots": _file_fingerprint(lots_path),
            "movement": _file_fingerprint(movement_path),
        },
        "summary": {
            "sku_count": len(processed_skus),
            "skus_processed": processed_skus,
            "total_units_sold": total_units,
            "total_cogs": decimal_to_string(total_cogs),
            "failed_sku_count": len(failed_skus),
            "failed_skus": failed_skus,
            "shortfall_quantity": shortfall_quantity,
        },
        "history": asdict(history_record) if history_record else None,
        "accountant_review_columns": {
            "cogs_detail": [
                "sku",
                "period",
                "total_quantity_sold",
                "merchandise_cost",
                "shipping_cost",
                "total_cost",
                "average_cost",
            ],
            "failed_sku_queue": [
                "sku",
                "period",
                "requested_quantity",
                "allocated_quantity",
                "shortfall_quantity",
                "reasons",
                "status",
            ],
        },
        "local_review_commands": {
            "failed_sku_queue": f"python -m app.local_cli failed-skus --out {review_out_dir} --period {packet_period}",
            "assert_failed_skus_clear": f"python -m app.local_cli failed-skus --out {review_out_dir} --period {packet_period} --assert-clear",
            "rollback_plan_read_only": f"python -m app.local_cli rollback-plan --out {review_out_dir} --period {packet_period}",
        },
        "artifact_files": [_relative_artifact(out_dir, path) for path in artifact_paths],
        "operator_next_step": (
            "Fix local input CSVs and rerun with --reopen, then assert failed-skus --assert-clear."
            if failed_skus
            else "Review close packet and retain artifacts for local audit handoff."
        ),
    }


def _display_path(path: str | Path) -> str:
    file_path = Path(path)
    try:
        return file_path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return file_path.as_posix()


def _file_fingerprint(path: str | Path) -> dict:
    file_path = Path(path)
    display_path = _display_path(file_path)
    return {
        "path": display_path,
        "name": file_path.name,
        "sha256": hashlib.sha256(file_path.read_bytes()).hexdigest(),
    }


def _relative_artifact(out_dir: Path, path: Path) -> str:
    try:
        return path.relative_to(out_dir).as_posix()
    except ValueError:
        return str(path)


def _packet_markdown(packet: dict) -> str:
    summary = packet["summary"]
    lines = [
        "# FirstLot local close packet",
        "",
        f"- Safety mode: `{packet['safety_mode']}`",
        f"- Period: `{packet['period']}`",
        f"- Generated at: `{packet['generated_at']}`",
        f"- SKUs processed: {summary['sku_count']} ({', '.join(summary['skus_processed']) or 'none'})",
        f"- Total units sold: {summary['total_units_sold']}",
        f"- Total COGS: {summary['total_cogs']}",
        f"- Failed SKU count: {summary['failed_sku_count']}",
        f"- Shortfall quantity: {summary['shortfall_quantity']}",
        f"- Operator next step: {packet['operator_next_step']}",
        "",
        "## Input files",
        "",
        f"- Purchase lots: `{packet['input_files']['purchase_lots']['path']}` "
        f"sha256 `{packet['input_files']['purchase_lots']['sha256']}`",
        f"- Movement: `{packet['input_files']['movement']['path']}` "
        f"sha256 `{packet['input_files']['movement']['sha256']}`",
        "",
        "## Artifacts",
        "",
    ]
    lines.extend(f"- `{artifact}`" for artifact in packet["artifact_files"])
    lines.extend(
        [
            "",
            "## Local review commands",
            "",
        ]
    )
    lines.extend(
        f"- {name}: `{command}`" for name, command in packet["local_review_commands"].items()
    )
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "No live database writes, no Supabase/API imports, no `.env` reads, and no Storage Standard/client-data mutation are part of this packet.",
            "",
        ]
    )
    return "\n".join(lines)
