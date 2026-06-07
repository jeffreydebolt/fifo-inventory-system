"""Local-only CSV validation for FirstLot client-test readiness.

This module validates fixture/local purchase lot and movement CSVs before the FIFO
engine runs. It is intentionally dependency-free and does not import dotenv,
Supabase, API clients, or application runtime code.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

PURCHASE_LOT_REQUIRED_COLUMNS = (
    "lot_id",
    "sku",
    "received_date",
    "original_quantity",
    "remaining_quantity",
    "unit_price",
    "freight_cost_per_unit",
)

MOVEMENT_REQUIRED_COLUMNS = (
    "sale_id",
    "sku",
    "sale_date",
    "quantity_sold",
)


@dataclass(frozen=True)
class CSVValidationIssue:
    """One deterministic validation issue for operator-facing JSON output."""

    file_role: str
    row_number: int | None
    field: str | None
    code: str
    message: str
    severity: str = "error"
    title: str = "CSV validation issue"
    details: str = ""
    suggested_action: str = "Review and correct the source CSV, then rerun validation."
    blocking: bool = True

    def to_dict(self) -> dict:
        return {
            "file_role": self.file_role,
            "row_number": self.row_number,
            "field": self.field,
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "title": self.title,
            "details": self.details or self.message,
            "suggested_action": self.suggested_action,
            "blocking": self.blocking,
        }


@dataclass
class CSVValidationResult:
    """Combined validation result for local FirstLot CSV inputs."""

    valid: bool
    errors: list[CSVValidationIssue] = field(default_factory=list)
    warnings: list[CSVValidationIssue] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "summary": self.summary,
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
        }


def validate_firstlot_csvs(
    lots_path: str | Path,
    movement_path: str | Path,
    *,
    include_cross_file_checks: bool = True,
) -> CSVValidationResult:
    """Validate purchase lot and movement CSVs without running FIFO."""

    errors: list[CSVValidationIssue] = []
    warnings: list[CSVValidationIssue] = []
    errors.extend(_validate_purchase_lots(Path(lots_path), warnings))
    errors.extend(_validate_movement(Path(movement_path), warnings))
    if include_cross_file_checks and not errors:
        errors.extend(_validate_cross_file_consistency(Path(lots_path), Path(movement_path)))

    valid = not errors
    if valid:
        summary = "CSV validation passed; inputs are ready for a local/demo FIFO run."
    else:
        summary = f"CSV validation failed with {len(errors)} error(s); FIFO run should not proceed."
    return CSVValidationResult(valid=valid, errors=errors, warnings=warnings, summary=summary)


def human_validation_report(result: CSVValidationResult, *, max_issues: int = 8) -> str:
    """Return concise operator-facing validation guidance for terminal output."""

    lines = [result.summary]
    if result.valid:
        lines.append("Next action: run the local/demo FIFO command or client-smoke workflow.")
    else:
        lines.append("Next action: fix blocking CSV issues before running FIFO COGS.")
    for label, issues in (("Errors", result.errors), ("Warnings", result.warnings)):
        if not issues:
            continue
        lines.append(f"\n{label}:")
        for issue in issues[:max_issues]:
            location = issue.file_role
            if issue.row_number is not None:
                location += f" row {issue.row_number}"
            if issue.field:
                location += f" field {issue.field}"
            lines.extend(
                [
                    f"- {issue.title} ({issue.code}) — {location}",
                    f"  Details: {issue.details or issue.message}",
                    f"  Suggested action: {issue.suggested_action}",
                ]
            )
        remaining = len(issues) - max_issues
        if remaining > 0:
            lines.append(f"- ... {remaining} more {label.lower()} in JSON output")
    return "\n".join(lines)


def _validate_purchase_lots(path: Path, warnings: list[CSVValidationIssue]) -> list[CSVValidationIssue]:
    errors: list[CSVValidationIssue] = []
    rows, header_errors = _read_rows(path, "purchase_lots", PURCHASE_LOT_REQUIRED_COLUMNS)
    errors.extend(header_errors)
    if header_errors:
        return errors

    seen_lot_ids: dict[str, int] = {}
    for row_number, row in rows:
        lot_id = _clean(row.get("lot_id"))
        sku = _clean(row.get("sku"))
        original_quantity = _parse_int(row, "original_quantity", row_number, "purchase_lots", errors)
        remaining_quantity = _parse_int(row, "remaining_quantity", row_number, "purchase_lots", errors)
        unit_price = _parse_decimal(row, "unit_price", row_number, "purchase_lots", errors)
        freight_cost = _parse_decimal(row, "freight_cost_per_unit", row_number, "purchase_lots", errors)
        _parse_datetime(row, "received_date", row_number, "purchase_lots", errors)

        if not lot_id:
            errors.append(_issue("purchase_lots", row_number, "lot_id", "missing_required", "lot_id is required."))
        elif lot_id in seen_lot_ids:
            errors.append(_issue("purchase_lots", row_number, "lot_id", "duplicate_lot_id", f"lot_id {lot_id!r} duplicates row {seen_lot_ids[lot_id]}."))
        else:
            seen_lot_ids[lot_id] = row_number

        if not sku:
            errors.append(_issue("purchase_lots", row_number, "sku", "missing_required", "sku is required."))
        if original_quantity is not None and original_quantity <= 0:
            errors.append(_issue("purchase_lots", row_number, "original_quantity", "non_positive_quantity", "original_quantity must be greater than zero."))
        if remaining_quantity is not None and remaining_quantity < 0:
            errors.append(_issue("purchase_lots", row_number, "remaining_quantity", "negative_quantity", "remaining_quantity must be nonnegative."))
        if original_quantity is not None and remaining_quantity is not None and remaining_quantity > original_quantity:
            errors.append(_issue("purchase_lots", row_number, "remaining_quantity", "remaining_exceeds_original", "remaining_quantity cannot exceed original_quantity."))
        if unit_price is not None and unit_price < Decimal("0"):
            errors.append(_issue("purchase_lots", row_number, "unit_price", "negative_cost", "unit_price must be nonnegative."))
        if freight_cost is not None and freight_cost < Decimal("0"):
            errors.append(_issue("purchase_lots", row_number, "freight_cost_per_unit", "negative_freight", "freight_cost_per_unit must be nonnegative."))
        if unit_price == Decimal("0") and freight_cost == Decimal("0"):
            warnings.append(_issue("purchase_lots", row_number, "unit_price", "zero_total_unit_cost", "unit_price and freight_cost_per_unit are both zero; verify this free lot is intentional."))
    return errors


def _validate_movement(path: Path, warnings: list[CSVValidationIssue]) -> list[CSVValidationIssue]:
    errors: list[CSVValidationIssue] = []
    rows, header_errors = _read_rows(path, "movement", MOVEMENT_REQUIRED_COLUMNS)
    errors.extend(header_errors)
    if header_errors:
        return errors

    seen_sale_ids: dict[str, int] = {}
    for row_number, row in rows:
        sale_id = _clean(row.get("sale_id"))
        sku = _clean(row.get("sku"))
        quantity_sold = _parse_int(row, "quantity_sold", row_number, "movement", errors)
        _parse_datetime(row, "sale_date", row_number, "movement", errors)

        if not sale_id:
            errors.append(_issue("movement", row_number, "sale_id", "missing_required", "sale_id is required."))
        elif sale_id in seen_sale_ids:
            errors.append(_issue("movement", row_number, "sale_id", "duplicate_sale_id", f"sale_id {sale_id!r} duplicates row {seen_sale_ids[sale_id]}."))
        else:
            seen_sale_ids[sale_id] = row_number
        if not sku:
            errors.append(_issue("movement", row_number, "sku", "missing_required", "sku is required."))
        if quantity_sold is not None and quantity_sold <= 0:
            errors.append(_issue("movement", row_number, "quantity_sold", "non_positive_quantity", "quantity_sold must be greater than zero for client-test close runs."))
    return errors


def _validate_cross_file_consistency(lots_path: Path, movement_path: Path) -> list[CSVValidationIssue]:
    errors: list[CSVValidationIssue] = []
    lot_rows, lot_header_errors = _read_rows(lots_path, "purchase_lots", PURCHASE_LOT_REQUIRED_COLUMNS)
    movement_rows, movement_header_errors = _read_rows(movement_path, "movement", MOVEMENT_REQUIRED_COLUMNS)
    if lot_header_errors or movement_header_errors:
        return []

    first_received_by_sku: dict[str, datetime] = {}
    for _row_number, row in lot_rows:
        sku = _clean(row.get("sku"))
        received = _safe_datetime(_clean(row.get("received_date")))
        if sku and received and (sku not in first_received_by_sku or received < first_received_by_sku[sku]):
            first_received_by_sku[sku] = received

    if not first_received_by_sku:
        return []

    for row_number, row in movement_rows:
        sku = _clean(row.get("sku"))
        sale_date = _safe_datetime(_clean(row.get("sale_date")))
        if not sku or not sale_date:
            continue
        first_received = first_received_by_sku.get(sku)
        if first_received is None:
            errors.append(_issue("movement", row_number, "sku", "movement_sku_missing_from_purchase_lots", f"movement SKU {sku!r} has no source-backed purchase lot row."))
        elif sale_date < first_received:
            errors.append(_issue("movement", row_number, "sale_date", "sale_before_first_received_lot", f"sale_date {sale_date.isoformat()} is before first received lot {first_received.isoformat()} for SKU {sku!r}."))
    return errors


def _read_rows(path: Path, file_role: str, required_columns: Iterable[str]) -> tuple[list[tuple[int, dict]], list[CSVValidationIssue]]:
    errors: list[CSVValidationIssue] = []
    if not path.exists():
        return [], [_issue(file_role, None, None, "file_not_found", f"CSV file does not exist: {path}")]

    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing_columns = [column for column in required_columns if column not in fieldnames]
        for column in missing_columns:
            errors.append(_issue(file_role, 1, column, "missing_required_column", f"Missing required column {column!r}."))
        if errors:
            return [], errors
        return list(enumerate(reader, start=2)), []


def _parse_datetime(row: dict, field: str, row_number: int, file_role: str, errors: list[CSVValidationIssue]) -> datetime | None:
    value = _clean(row.get(field))
    if not value:
        errors.append(_issue(file_role, row_number, field, "missing_required", f"{field} is required."))
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        errors.append(_issue(file_role, row_number, field, "invalid_date", f"{field} must be an ISO date/datetime."))
        return None


def _safe_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _parse_int(row: dict, field: str, row_number: int, file_role: str, errors: list[CSVValidationIssue]) -> int | None:
    value = _clean(row.get(field))
    if not value:
        errors.append(_issue(file_role, row_number, field, "missing_required", f"{field} is required."))
        return None
    try:
        return int(value)
    except ValueError:
        errors.append(_issue(file_role, row_number, field, "invalid_integer", f"{field} must be an integer."))
        return None


def _parse_decimal(row: dict, field: str, row_number: int, file_role: str, errors: list[CSVValidationIssue]) -> Decimal | None:
    value = _clean(row.get(field))
    if not value:
        errors.append(_issue(file_role, row_number, field, "missing_required", f"{field} is required."))
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        errors.append(_issue(file_role, row_number, field, "invalid_decimal", f"{field} must be a decimal."))
        return None


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _issue(file_role: str, row_number: int | None, field: str | None, code: str, message: str) -> CSVValidationIssue:
    guidance = _GUIDANCE.get(code, {})
    severity = guidance.get("severity", "error")
    return CSVValidationIssue(
        file_role=file_role,
        row_number=row_number,
        field=field,
        code=code,
        message=message,
        severity=severity,
        title=guidance.get("title", code.replace("_", " ").capitalize()),
        details=guidance.get("details", message),
        suggested_action=guidance.get("suggested_action", "Review and correct the source CSV, then rerun validation."),
        blocking=guidance.get("blocking", severity == "error"),
    )


_GUIDANCE = {
    "file_not_found": {"title": "CSV file not found", "details": "The requested local CSV path was not found, so FirstLot cannot validate or run FIFO.", "suggested_action": "Check the path and rerun with a checked-in fixture or local synthetic CSV."},
    "missing_required_column": {"title": "Required column is missing", "details": "The CSV shape does not match FirstLot's local FIFO contract.", "suggested_action": "Add the missing column or run the local normalizer before validation."},
    "missing_required": {"title": "Required value is blank", "suggested_action": "Fill the blank value from source records, then rerun validation."},
    "duplicate_lot_id": {"title": "Duplicate purchase lot ID", "suggested_action": "Make lot_id values unique or merge duplicate source rows intentionally."},
    "duplicate_sale_id": {"title": "Duplicate sale ID", "suggested_action": "Deduplicate movement rows so each sale_id is processed once."},
    "invalid_date": {"title": "Date is not ISO formatted", "suggested_action": "Use YYYY-MM-DD or an ISO datetime from the source export."},
    "invalid_integer": {"title": "Quantity is not an integer", "suggested_action": "Use whole-unit counts for quantities before running FIFO."},
    "invalid_decimal": {"title": "Cost is not a decimal", "suggested_action": "Use decimal currency values such as 12.34, without currency symbols."},
    "non_positive_quantity": {"title": "Quantity must be positive", "suggested_action": "Replace zero/negative movement or original lot quantities with corrected source-backed quantities."},
    "negative_quantity": {"title": "Remaining quantity is negative", "suggested_action": "Correct remaining quantity to zero or a positive source-backed count."},
    "remaining_exceeds_original": {"title": "Remaining quantity exceeds original quantity", "suggested_action": "Correct original and remaining quantities so remaining is not greater than received units."},
    "negative_cost": {"title": "Unit price is negative", "suggested_action": "Correct unit_price from invoice/source data before running FIFO."},
    "negative_freight": {"title": "Freight cost is negative", "suggested_action": "Correct freight_cost_per_unit from source-backed freight data."},
    "zero_total_unit_cost": {"severity": "warning", "title": "Zero total unit cost", "details": "Both merchandise and freight cost are zero for this lot.", "suggested_action": "Confirm this is an intentional free/sample lot; otherwise add source-backed cost and freight.", "blocking": False},
    "movement_sku_missing_from_purchase_lots": {"title": "Movement SKU has no purchase lot", "details": "Sales cannot be FIFO-costed when the SKU never appears in purchase lots.", "suggested_action": "Add source-backed purchase lots/freight for this SKU or remove incorrect movement rows, then rerun validation."},
    "sale_before_first_received_lot": {"title": "Sale date predates first lot receipt", "details": "FIFO cannot confidently cost a sale before any received lot exists for that SKU.", "suggested_action": "Add earlier source-backed lots/freight, correct the sale date, or queue this SKU for operator review."},
}
