"""End-to-end local client CSV smoke runner for FirstLot.

This module is intentionally local-file only. It normalizes client-shaped CSVs,
runs the deterministic FIFO engine, writes local review artifacts, and produces
operator/fix-plan guidance. It never imports dotenv, Supabase, API clients, or
live adapters.
"""
from __future__ import annotations

import csv
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from .close_packet import write_close_packet
from .csv_ingest import load_movement_csv, load_purchase_lots_csv
from .csv_validation import validate_firstlot_csvs
from .failed_sku_workflow import build_fix_plan, load_failed_sku_queue
from .lots_normalizer import normalize_lot_csv, normalize_movement_csv
from .month_history import append_month_close_record
from .output_files import write_fifo_report
from .outputs import run_fifo_report


@dataclass
class ClientSmokeResult:
    ok: bool
    out: str
    period: str
    normalized_lots: str
    normalized_movement: str
    total_cogs: str
    failed_sku_count: int
    total_shortfall_quantity: int
    artifact_count: int
    mutations_performed: list[str] = field(default_factory=list)
    validation: dict | None = None
    lots_normalization: dict | None = None
    movement_normalization: dict | None = None
    fix_plan: dict | None = None
    missing_lot_request_path: str | None = None
    synthetic_repair_lots_path: str | None = None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "out": self.out,
            "period": self.period,
            "normalized_lots": self.normalized_lots,
            "normalized_movement": self.normalized_movement,
            "total_cogs": self.total_cogs,
            "failed_sku_count": self.failed_sku_count,
            "total_shortfall_quantity": self.total_shortfall_quantity,
            "artifact_count": self.artifact_count,
            "mutations_performed": self.mutations_performed,
            "validation": self.validation,
            "lots_normalization": self.lots_normalization,
            "movement_normalization": self.movement_normalization,
            "fix_plan": self.fix_plan,
            "missing_lot_request_path": self.missing_lot_request_path,
            "synthetic_repair_lots_path": self.synthetic_repair_lots_path,
            "safety": "local client CSV smoke only; no .env, no Supabase/API imports, no live DB writes",
        }


def run_client_smoke(
    *,
    lots_path: str | Path,
    movement_path: str | Path,
    out_dir: str | Path,
    period: str,
    generated_at: str = "2026-06-03T23:00:00",
    expect_clear: bool = False,
    clean_output: bool = False,
) -> ClientSmokeResult:
    """Run the full safe local weekend-test workflow from raw client-shaped CSVs."""

    out = Path(out_dir)
    if clean_output:
        _clean_temp_output(out)
    out.mkdir(parents=True, exist_ok=True)
    normalized_dir = out / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    normalized_lots = normalized_dir / "purchase_lots.csv"
    normalized_movement = normalized_dir / "movement.csv"

    lots_result = normalize_lot_csv(lots_path, normalized_lots)
    movement_result = normalize_movement_csv(movement_path, normalized_movement)
    if not lots_result.ok or not movement_result.ok:
        result = ClientSmokeResult(
            ok=False,
            out=str(out),
            period=period,
            normalized_lots=str(normalized_lots),
            normalized_movement=str(normalized_movement),
            total_cogs="0.00",
            failed_sku_count=0,
            total_shortfall_quantity=0,
            artifact_count=len(list(out.rglob("*"))),
            lots_normalization=lots_result.to_dict(),
            movement_normalization=movement_result.to_dict(),
        )
        _write_json(out / "client_smoke_summary.json", result.to_dict())
        _write_operator_summary_md(out / "client_smoke_summary.md", result.to_dict())
        return result

    validation = validate_firstlot_csvs(
        normalized_lots,
        normalized_movement,
        include_cross_file_checks=False,
    ).to_dict()
    if not validation["valid"]:
        result = ClientSmokeResult(
            ok=False,
            out=str(out),
            period=period,
            normalized_lots=str(normalized_lots),
            normalized_movement=str(normalized_movement),
            total_cogs="0.00",
            failed_sku_count=0,
            total_shortfall_quantity=0,
            artifact_count=len(list(out.rglob("*"))),
            validation=validation,
            lots_normalization=lots_result.to_dict(),
            movement_normalization=movement_result.to_dict(),
        )
        _write_json(out / "client_smoke_summary.json", result.to_dict())
        _write_operator_summary_md(out / "client_smoke_summary.md", result.to_dict())
        return result

    generated_dt = datetime.fromisoformat(generated_at)
    inventory = load_purchase_lots_csv(normalized_lots, snapshot_timestamp=generated_dt)
    sales = load_movement_csv(normalized_movement)
    report = run_fifo_report(inventory, sales, generated_at=generated_dt)
    written = write_fifo_report(report, out, include_json=True)
    history_record, history_files = append_month_close_record(
        report,
        out,
        period,
        recorded_at=generated_dt,
        note="client-smoke local raw CSV test",
    )
    written.extend(history_files)
    written.extend(
        write_close_packet(
            report,
            out,
            lots_path=normalized_lots,
            movement_path=normalized_movement,
            artifact_paths=written,
            period=period,
            history_record=history_record,
        )
    )

    queue_records = load_failed_sku_queue(out)
    total_shortfall = sum(record.shortfall_quantity for record in queue_records)
    fix_plan = build_fix_plan(
        out,
        period=period,
        lots_path=str(normalized_lots),
        movement_path=str(normalized_movement),
        note="client-smoke generated fix plan",
    )
    _write_json(out / "fix_plan.json", fix_plan)
    missing_lot_request_path = None
    synthetic_repair_path = None
    if queue_records:
        missing_lot_request_path = out / "missing_lot_request.csv"
        _write_missing_lot_request(missing_lot_request_path, queue_records)
        synthetic_repair_path = out / "synthetic_repair_lots_SANDBOX_ONLY.csv"
        _write_synthetic_repair_lots(synthetic_repair_path, queue_records, period)

    result = ClientSmokeResult(
        ok=(not queue_records) if expect_clear else True,
        out=str(out),
        period=period,
        normalized_lots=str(normalized_lots),
        normalized_movement=str(normalized_movement),
        total_cogs=str(sum(row.total_cogs for row in report.cogs_summary)),
        failed_sku_count=len(queue_records),
        total_shortfall_quantity=total_shortfall,
        artifact_count=len([path for path in out.rglob("*") if path.is_file()]),
        validation=validation,
        lots_normalization=lots_result.to_dict(),
        movement_normalization=movement_result.to_dict(),
        fix_plan=fix_plan,
        missing_lot_request_path=str(missing_lot_request_path) if missing_lot_request_path else None,
        synthetic_repair_lots_path=str(synthetic_repair_path) if synthetic_repair_path else None,
    )
    _write_json(out / "client_smoke_summary.json", result.to_dict())
    _write_operator_summary_md(out / "client_smoke_summary.md", result.to_dict())
    return result


def _clean_temp_output(out: Path) -> None:
    resolved = out.resolve()
    temp_roots = [Path("/tmp").resolve(), Path("/private/tmp").resolve()]
    if not any(resolved == root or root in resolved.parents for root in temp_roots):
        raise ValueError("--clean-output is only allowed for /tmp or /private/tmp output folders")
    if resolved.exists():
        shutil.rmtree(resolved)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_operator_summary_md(path: Path, payload: dict) -> None:
    """Write a concise human review note next to the machine-readable smoke JSON."""

    validation = payload.get("validation") or {}
    fix_plan = payload.get("fix_plan") or {}
    recommended_fixes = fix_plan.get("recommended_csv_fixes") or []
    status = "PASS — failed SKU queue clear" if payload.get("failed_sku_count") == 0 else "NEEDS FIX — failed SKU queue remains"
    next_command = fix_plan.get("completion_check_command") or (
        "python3 -m app.local_cli failed-skus "
        f"--out {payload.get('out')} --period {payload.get('period')} --assert-clear"
    )
    lines = [
        "# FirstLot client CSV smoke summary",
        "",
        f"- Status: {status}",
        f"- Period: {payload.get('period')}",
        f"- Output folder: `{payload.get('out')}`",
        f"- Validation valid: {validation.get('valid')}",
        f"- Total COGS: {payload.get('total_cogs')}",
        f"- Failed SKU count: {payload.get('failed_sku_count')}",
        f"- Total shortfall quantity: {payload.get('total_shortfall_quantity')}",
        f"- Normalized lots: `{payload.get('normalized_lots')}`",
        f"- Normalized movement: `{payload.get('normalized_movement')}`",
        "- Safety: local client CSV smoke only; no .env, no Supabase/API imports, no live DB writes",
        "- Mutations performed: none",
        "",
        "## Next operator command",
        "",
        "```bash",
        str(next_command),
        "```",
    ]
    if payload.get("missing_lot_request_path"):
        lines.extend(
            [
                "",
                "## Failed SKU repair files",
                "",
                f"- Source-backed missing-lot request: `{payload.get('missing_lot_request_path')}`",
                f"- Sandbox shape/template only: `{payload.get('synthetic_repair_lots_path')}`",
                "- Do not rely on synthetic repair rows for real COGS; replace with source-backed lot data first.",
            ]
        )
    validation_errors = validation.get("errors") or []
    validation_warnings = validation.get("warnings") or []
    if validation_errors or validation_warnings:
        lines.extend(["", "## Top validation issues / next action", ""])
        for issue in (validation_errors + validation_warnings)[:5]:
            location = issue.get("file_role", "csv")
            if issue.get("row_number") is not None:
                location += f" row {issue.get('row_number')}"
            if issue.get("field"):
                location += f" field {issue.get('field')}"
            lines.append(
                "- "
                f"{issue.get('title', issue.get('code'))} at {location}: "
                f"{issue.get('suggested_action', 'Correct the source CSV and rerun validation.')}"
            )
    if recommended_fixes:
        lines.extend(["", "## Recommended CSV fixes", ""])
        for fix in recommended_fixes:
            lines.append(
                "- "
                f"{fix.get('sku')} {fix.get('period')}: add at least "
                f"{fix.get('minimum_additional_available_units_needed')} source-backed unit(s) "
                f"({fix.get('reason')})."
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_missing_lot_request(path: Path, queue_records: list) -> None:
    """Write source-backed missing-lot requirements for operator repair."""

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "sku",
                "period",
                "minimum_units_needed",
                "first_sale_date",
                "last_sale_date",
                "reason",
                "source_document_needed",
                "operator_note",
            ],
        )
        writer.writeheader()
        for record in queue_records:
            writer.writerow(
                {
                    "sku": record.sku,
                    "period": record.period,
                    "minimum_units_needed": str(record.shortfall_quantity),
                    "first_sale_date": record.first_sale_date,
                    "last_sale_date": record.last_sale_date,
                    "reason": record.reasons,
                    "source_document_needed": "Source-backed purchase lot with received date on/before first sale date, available units, unit cost, and freight cost",
                    "operator_note": "Do not invent COGS: add only purchase-lot data supported by source exports/invoices, then rerun client-smoke or local FIFO.",
                }
            )


def _write_synthetic_repair_lots(path: Path, queue_records: list, period: str) -> None:
    """Write clearly labeled sandbox rows operators may copy/edit locally.

    These rows deliberately use zero costs and synthetic lot IDs so they cannot be
    mistaken for source-backed COGS. They are only a shape/template for local
    repair testing.
    """

    period_start = f"{period}-01"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "lot_id",
                "sku",
                "received_date",
                "original_quantity",
                "remaining_quantity",
                "unit_price",
                "freight_cost_per_unit",
                "note",
            ],
        )
        writer.writeheader()
        for record in queue_records:
            qty = max(1, int(record.shortfall_quantity))
            writer.writerow(
                {
                    "lot_id": f"SYNTH-REPAIR-{record.sku}",
                    "sku": record.sku,
                    "received_date": period_start,
                    "original_quantity": str(qty),
                    "remaining_quantity": str(qty),
                    "unit_price": str(Decimal("0.00")),
                    "freight_cost_per_unit": str(Decimal("0.00")),
                    "note": "SANDBOX ONLY - replace with real source-backed lot/cost before relying on COGS",
                }
            )
