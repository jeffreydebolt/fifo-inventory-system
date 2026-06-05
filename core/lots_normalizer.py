"""Local-only purchase-lot CSV inspection and normalization.

This module helps operators use client-shaped purchase lot exports without
weakening the strict FIFO engine contract. It performs no network access, does
not import dotenv/Supabase/API adapters, and only writes when the caller passes
an explicit output CSV path.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

from .csv_validation import MOVEMENT_REQUIRED_COLUMNS, PURCHASE_LOT_REQUIRED_COLUMNS, validate_firstlot_csvs

LOT_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "lot_id": ("lot_id", "po_number", "po", "purchase_order", "purchase_order_number", "lot", "lot_number"),
    "sku": ("sku", "item", "item_sku", "product_sku", "variant_sku"),
    "received_date": ("received_date", "receipt_date", "received", "date_received", "po_date"),
    "original_quantity": (
        "original_quantity",
        "original_unit_qty",
        "original_qty",
        "quantity",
        "qty",
        "units",
    ),
    "remaining_quantity": (
        "remaining_quantity",
        "remaining_unit_qty",
        "remaining_qty",
        "on_hand",
        "available_quantity",
    ),
    "unit_price": ("unit_price", "unit_cost", "cost", "item_cost", "price"),
    "freight_cost_per_unit": (
        "freight_cost_per_unit",
        "freight_unit_cost",
        "shipping_cost_per_unit",
        "freight",
        "landed_freight_per_unit",
    ),
}

MOVEMENT_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "sale_id": ("sale_id", "order_id", "order_line_id", "transaction_id", "line_id"),
    "sku": ("sku", "item", "item_sku", "product_sku", "variant_sku"),
    "sale_date": ("sale_date", "sale_month_str", "date", "order_date", "sold_date", "transaction_date"),
    "quantity_sold": ("quantity_sold", "qty_sold", "quantity", "qty", "units_sold"),
}


@dataclass(frozen=True)
class NormalizeIssue:
    row_number: int | None
    field: str | None
    code: str
    message: str

    def to_dict(self) -> dict:
        return {
            "row_number": self.row_number,
            "field": self.field,
            "code": self.code,
            "message": self.message,
        }


@dataclass
class LotInspection:
    path: str
    row_count: int
    headers: list[str]
    ignored_blank_headers: int
    mapping: dict[str, str | None]
    missing_required: list[str] = field(default_factory=list)
    warnings: list[NormalizeIssue] = field(default_factory=list)
    sample_rows: list[dict[str, str]] = field(default_factory=list)

    @property
    def ready_to_normalize(self) -> bool:
        return not self.missing_required

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "row_count": self.row_count,
            "headers": self.headers,
            "ignored_blank_headers": self.ignored_blank_headers,
            "mapping": self.mapping,
            "missing_required": self.missing_required,
            "ready_to_normalize": self.ready_to_normalize,
            "warnings": [warning.to_dict() for warning in self.warnings],
            "sample_rows": self.sample_rows,
            "safety": "local purchase-lot CSV inspection only; no .env, no Supabase/API imports, no live DB writes",
        }


@dataclass
class LotNormalizationResult:
    input_path: str
    output_path: str
    rows_written: int
    inspection: LotInspection
    errors: list[NormalizeIssue] = field(default_factory=list)
    validation: dict | None = None

    @property
    def ok(self) -> bool:
        return not self.errors and (self.validation or {}).get("valid") is True

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "input_path": self.input_path,
            "output_path": self.output_path,
            "rows_written": self.rows_written,
            "inspection": self.inspection.to_dict(),
            "errors": [error.to_dict() for error in self.errors],
            "validation": self.validation,
            "safety": "local purchase-lot CSV normalization only; no .env, no Supabase/API imports, no live DB writes",
        }


def inspect_lot_csv(path: str | Path, sample_limit: int = 3) -> LotInspection:
    """Inspect a purchase-lot export and infer its FirstLot column mapping."""

    source = Path(path)
    with source.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        raw_headers = reader.fieldnames or []
        headers = [header for header in raw_headers if _clean_header(header)]
        ignored_blank_headers = len(raw_headers) - len(headers)
        mapping = _infer_mapping(headers, LOT_COLUMN_ALIASES)
        missing_required = [field for field in PURCHASE_LOT_REQUIRED_COLUMNS if not mapping.get(field)]
        sample_rows: list[dict[str, str]] = []
        row_count = 0
        for row in reader:
            row_count += 1
            if len(sample_rows) < sample_limit:
                sample_rows.append(_project_sample_row(row, mapping))

    warnings: list[NormalizeIssue] = []
    if ignored_blank_headers:
        warnings.append(
            NormalizeIssue(
                row_number=1,
                field=None,
                code="ignored_blank_headers",
                message=f"Ignored {ignored_blank_headers} trailing blank header column(s).",
            )
        )
    if mapping.get("lot_id") == "po_number":
        warnings.append(
            NormalizeIssue(
                row_number=1,
                field="lot_id",
                code="mapped_po_number_to_lot_id",
                message="Mapped po_number to lot_id for local FIFO testing.",
            )
        )

    return LotInspection(
        path=str(source),
        row_count=row_count,
        headers=headers,
        ignored_blank_headers=ignored_blank_headers,
        mapping=mapping,
        missing_required=missing_required,
        warnings=warnings,
        sample_rows=sample_rows,
    )


def normalize_lot_csv(input_path: str | Path, output_path: str | Path) -> LotNormalizationResult:
    """Normalize a client-shaped lot CSV to FirstLot's strict purchase_lots.csv shape."""

    source = Path(input_path)
    target = Path(output_path)
    inspection = inspect_lot_csv(source, sample_limit=3)
    errors: list[NormalizeIssue] = []
    if inspection.missing_required:
        for field in inspection.missing_required:
            errors.append(
                NormalizeIssue(
                    row_number=1,
                    field=field,
                    code="missing_mappable_column",
                    message=f"No source column could be mapped to required FirstLot field {field!r}.",
                )
            )
        return LotNormalizationResult(str(source), str(target), 0, inspection, errors, validation=None)

    target.parent.mkdir(parents=True, exist_ok=True)
    rows_written = 0
    normalized_rows: list[dict[str, str]] = []
    with source.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=2):
            if _mapped_row_is_blank(row, inspection.mapping, PURCHASE_LOT_REQUIRED_COLUMNS):
                continue
            normalized, row_errors = _normalize_row(row, inspection.mapping, row_number)
            errors.extend(row_errors)
            if not row_errors:
                normalized_rows.append(normalized)

    if errors:
        return LotNormalizationResult(str(source), str(target), 0, inspection, errors, validation=None)

    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(PURCHASE_LOT_REQUIRED_COLUMNS))
        writer.writeheader()
        for row in normalized_rows:
            writer.writerow(row)
        rows_written = len(normalized_rows)

    validation = _validate_normalized_lots_only(target)
    return LotNormalizationResult(str(source), str(target), rows_written, inspection, errors, validation=validation)


@dataclass
class MovementInspection:
    path: str
    row_count: int
    headers: list[str]
    ignored_blank_headers: int
    mapping: dict[str, str | None]
    missing_required: list[str] = field(default_factory=list)
    generated_sale_ids: bool = False
    warnings: list[NormalizeIssue] = field(default_factory=list)
    sample_rows: list[dict[str, str]] = field(default_factory=list)

    @property
    def ready_to_normalize(self) -> bool:
        missing = [field for field in self.missing_required if field != "sale_id"]
        return not missing

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "row_count": self.row_count,
            "headers": self.headers,
            "ignored_blank_headers": self.ignored_blank_headers,
            "mapping": self.mapping,
            "missing_required": self.missing_required,
            "generated_sale_ids": self.generated_sale_ids,
            "ready_to_normalize": self.ready_to_normalize,
            "warnings": [warning.to_dict() for warning in self.warnings],
            "sample_rows": self.sample_rows,
            "safety": "local movement CSV inspection only; no .env, no Supabase/API imports, no live DB writes",
        }


@dataclass
class MovementNormalizationResult:
    input_path: str
    output_path: str
    rows_written: int
    inspection: MovementInspection
    errors: list[NormalizeIssue] = field(default_factory=list)
    validation: dict | None = None

    @property
    def ok(self) -> bool:
        return not self.errors and (self.validation or {}).get("valid") is True

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "input_path": self.input_path,
            "output_path": self.output_path,
            "rows_written": self.rows_written,
            "inspection": self.inspection.to_dict(),
            "errors": [error.to_dict() for error in self.errors],
            "validation": self.validation,
            "safety": "local movement CSV normalization only; no .env, no Supabase/API imports, no live DB writes",
        }


def inspect_movement_csv(path: str | Path, sample_limit: int = 3) -> MovementInspection:
    source = Path(path)
    with source.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        raw_headers = reader.fieldnames or []
        headers = [header for header in raw_headers if _clean_header(header)]
        ignored_blank_headers = len(raw_headers) - len(headers)
        mapping = _infer_mapping(headers, MOVEMENT_COLUMN_ALIASES)
        missing_required = [field for field in MOVEMENT_REQUIRED_COLUMNS if not mapping.get(field)]
        sample_rows: list[dict[str, str]] = []
        row_count = 0
        for row in reader:
            row_count += 1
            if len(sample_rows) < sample_limit:
                sample_rows.append(_project_movement_sample_row(row, mapping, row_count))

    warnings: list[NormalizeIssue] = []
    if ignored_blank_headers:
        warnings.append(
            NormalizeIssue(1, None, "ignored_blank_headers", f"Ignored {ignored_blank_headers} trailing blank header column(s).")
        )
    generated_sale_ids = "sale_id" in missing_required
    if generated_sale_ids:
        warnings.append(
            NormalizeIssue(
                1,
                "sale_id",
                "generated_sale_ids",
                "No sale_id column was found; normalize-movement will generate deterministic local sale IDs.",
            )
        )
    blocking_missing = [field for field in missing_required if field != "sale_id"]
    return MovementInspection(
        path=str(source),
        row_count=row_count,
        headers=headers,
        ignored_blank_headers=ignored_blank_headers,
        mapping=mapping,
        missing_required=blocking_missing,
        generated_sale_ids=generated_sale_ids,
        warnings=warnings,
        sample_rows=sample_rows,
    )


def normalize_movement_csv(input_path: str | Path, output_path: str | Path) -> MovementNormalizationResult:
    source = Path(input_path)
    target = Path(output_path)
    inspection = inspect_movement_csv(source, sample_limit=3)
    errors: list[NormalizeIssue] = []
    if inspection.missing_required:
        for field in inspection.missing_required:
            errors.append(NormalizeIssue(1, field, "missing_mappable_column", f"No source column could be mapped to required FirstLot field {field!r}."))
        return MovementNormalizationResult(str(source), str(target), 0, inspection, errors, validation=None)

    target.parent.mkdir(parents=True, exist_ok=True)
    normalized_rows: list[dict[str, str]] = []
    with source.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader, start=1):
            row_number = index + 1
            if _mapped_row_is_blank(row, inspection.mapping, MOVEMENT_REQUIRED_COLUMNS):
                continue
            normalized, row_errors = _normalize_movement_row(row, inspection.mapping, row_number, index)
            errors.extend(row_errors)
            if not row_errors:
                normalized_rows.append(normalized)
    if errors:
        return MovementNormalizationResult(str(source), str(target), 0, inspection, errors, validation=None)

    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(MOVEMENT_REQUIRED_COLUMNS))
        writer.writeheader()
        for row in normalized_rows:
            writer.writerow(row)
    validation = _validate_normalized_movement_only(target)
    return MovementNormalizationResult(str(source), str(target), len(normalized_rows), inspection, errors, validation=validation)

def _infer_mapping(headers: Iterable[str], aliases_by_field: dict[str, tuple[str, ...]]) -> dict[str, str | None]:
    normalized_lookup = {_normalize_header(header): header for header in headers}
    mapping: dict[str, str | None] = {}
    for target_field, aliases in aliases_by_field.items():
        mapping[target_field] = None
        for alias in aliases:
            if alias in normalized_lookup:
                mapping[target_field] = normalized_lookup[alias]
                break
    return mapping


def _project_sample_row(row: dict, mapping: dict[str, str | None]) -> dict[str, str]:
    projected = {}
    for target_field in PURCHASE_LOT_REQUIRED_COLUMNS:
        source_field = mapping.get(target_field)
        projected[target_field] = (row.get(source_field) or "").strip() if source_field else ""
    return projected


def _project_movement_sample_row(row: dict, mapping: dict[str, str | None], index: int) -> dict[str, str]:
    projected = {}
    for target_field in MOVEMENT_REQUIRED_COLUMNS:
        source_field = mapping.get(target_field)
        projected[target_field] = (row.get(source_field) or "").strip() if source_field else f"SALE-{index:04d}"
    return projected


def _mapped_row_is_blank(row: dict, mapping: dict[str, str | None], target_fields: Iterable[str]) -> bool:
    for target_field in target_fields:
        source_field = mapping.get(target_field)
        if source_field and (row.get(source_field) or "").strip():
            return False
    return True


def _normalize_row(row: dict, mapping: dict[str, str | None], row_number: int) -> tuple[dict[str, str], list[NormalizeIssue]]:
    errors: list[NormalizeIssue] = []

    def mapped_value(target_field: str) -> str:
        source_field = mapping[target_field]
        return (row.get(source_field) or "").strip() if source_field else ""

    normalized = {
        "lot_id": mapped_value("lot_id"),
        "sku": mapped_value("sku"),
        "received_date": _normalize_date(mapped_value("received_date"), row_number, "received_date", errors),
        "original_quantity": _normalize_int(mapped_value("original_quantity"), row_number, "original_quantity", errors),
        "remaining_quantity": _normalize_int(mapped_value("remaining_quantity"), row_number, "remaining_quantity", errors),
        "unit_price": _normalize_decimal(mapped_value("unit_price"), row_number, "unit_price", errors),
        "freight_cost_per_unit": _normalize_decimal(
            mapped_value("freight_cost_per_unit"), row_number, "freight_cost_per_unit", errors
        ),
    }
    for field in ("lot_id", "sku"):
        if not normalized[field]:
            errors.append(NormalizeIssue(row_number, field, "missing_required", f"{field} is required."))
    return normalized, errors


def _normalize_movement_row(
    row: dict, mapping: dict[str, str | None], row_number: int, index: int
) -> tuple[dict[str, str], list[NormalizeIssue]]:
    errors: list[NormalizeIssue] = []

    def mapped_value(target_field: str) -> str:
        source_field = mapping.get(target_field)
        return (row.get(source_field) or "").strip() if source_field else ""

    sale_id = mapped_value("sale_id") or f"SALE-{index:04d}"
    normalized = {
        "sale_id": sale_id,
        "sku": mapped_value("sku"),
        "sale_date": _normalize_date(mapped_value("sale_date"), row_number, "sale_date", errors),
        "quantity_sold": _normalize_int(mapped_value("quantity_sold"), row_number, "quantity_sold", errors),
    }
    for field in ("sale_id", "sku"):
        if not normalized[field]:
            errors.append(NormalizeIssue(row_number, field, "missing_required", f"{field} is required."))
    return normalized, errors


def _normalize_date(value: str, row_number: int, field: str, errors: list[NormalizeIssue]) -> str:
    value = value.strip()
    if not value:
        errors.append(NormalizeIssue(row_number, field, "missing_required", f"{field} is required."))
        return ""
    formats = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d")
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    errors.append(
        NormalizeIssue(row_number, field, "invalid_date", f"{field} must be ISO date or M/D/YY style date; got {value!r}.")
    )
    return ""


def _normalize_int(value: str, row_number: int, field: str, errors: list[NormalizeIssue]) -> str:
    value = value.strip().replace(",", "")
    if not value:
        errors.append(NormalizeIssue(row_number, field, "missing_required", f"{field} is required."))
        return ""
    if not re.fullmatch(r"[-+]?\d+", value):
        errors.append(NormalizeIssue(row_number, field, "invalid_integer", f"{field} must be an integer; got {value!r}."))
        return ""
    return str(int(value))


def _normalize_decimal(value: str, row_number: int, field: str, errors: list[NormalizeIssue]) -> str:
    cleaned = value.strip().replace("$", "").replace(",", "")
    if not cleaned:
        errors.append(NormalizeIssue(row_number, field, "missing_required", f"{field} is required."))
        return ""
    try:
        decimal = Decimal(cleaned)
    except InvalidOperation:
        errors.append(NormalizeIssue(row_number, field, "invalid_decimal", f"{field} must be currency/decimal; got {value!r}."))
        return ""
    return format(decimal, "f")


def _validate_normalized_lots_only(path: Path) -> dict:
    """Reuse strict lot validation without requiring a real movement CSV."""

    movement = path.with_name("__normalizer_empty_movement.csv")
    movement.write_text("sale_id,sku,sale_date,quantity_sold\n", encoding="utf-8")
    try:
        result = validate_firstlot_csvs(path, movement)
    finally:
        movement.unlink(missing_ok=True)
    errors = [issue for issue in result.errors if issue.file_role == "purchase_lots"]
    warnings = [issue for issue in result.warnings if issue.file_role == "purchase_lots"]
    return {
        "valid": not errors,
        "summary": "Normalized purchase lots passed strict FirstLot validation." if not errors else "Normalized purchase lots failed strict FirstLot validation.",
        "errors": [issue.to_dict() for issue in errors],
        "warnings": [issue.to_dict() for issue in warnings],
    }


def _validate_normalized_movement_only(path: Path) -> dict:
    """Reuse strict movement validation without requiring real purchase lots."""

    lots = path.with_name("__normalizer_empty_lots.csv")
    lots.write_text("lot_id,sku,received_date,original_quantity,remaining_quantity,unit_price,freight_cost_per_unit\n", encoding="utf-8")
    try:
        result = validate_firstlot_csvs(lots, path)
    finally:
        lots.unlink(missing_ok=True)
    errors = [issue for issue in result.errors if issue.file_role == "movement"]
    warnings = [issue for issue in result.warnings if issue.file_role == "movement"]
    return {
        "valid": not errors,
        "summary": "Normalized movement passed strict FirstLot validation." if not errors else "Normalized movement failed strict FirstLot validation.",
        "errors": [issue.to_dict() for issue in errors],
        "warnings": [issue.to_dict() for issue in warnings],
    }


def _clean_header(header: str | None) -> str:
    return (header or "").strip()


def _normalize_header(header: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", header.strip().lower()).strip("_")
