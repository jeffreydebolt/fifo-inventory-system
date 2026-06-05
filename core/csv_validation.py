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

    def to_dict(self) -> dict:
        return {
            "file_role": self.file_role,
            "row_number": self.row_number,
            "field": self.field,
            "code": self.code,
            "message": self.message,
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


def validate_firstlot_csvs(lots_path: str | Path, movement_path: str | Path) -> CSVValidationResult:
    """Validate purchase lot and movement CSVs without running FIFO."""

    errors: list[CSVValidationIssue] = []
    warnings: list[CSVValidationIssue] = []
    errors.extend(_validate_purchase_lots(Path(lots_path), warnings))
    errors.extend(_validate_movement(Path(movement_path), warnings))

    valid = not errors
    if valid:
        summary = "CSV validation passed; inputs are ready for a local/demo FIFO run."
    else:
        summary = f"CSV validation failed with {len(errors)} error(s); FIFO run should not proceed."
    return CSVValidationResult(valid=valid, errors=errors, warnings=warnings, summary=summary)


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
            errors.append(
                _issue(
                    "purchase_lots",
                    row_number,
                    "lot_id",
                    "duplicate_lot_id",
                    f"lot_id {lot_id!r} duplicates row {seen_lot_ids[lot_id]}.",
                )
            )
        else:
            seen_lot_ids[lot_id] = row_number

        if not sku:
            errors.append(_issue("purchase_lots", row_number, "sku", "missing_required", "sku is required."))
        if original_quantity is not None and original_quantity <= 0:
            errors.append(
                _issue(
                    "purchase_lots",
                    row_number,
                    "original_quantity",
                    "non_positive_quantity",
                    "original_quantity must be greater than zero.",
                )
            )
        if remaining_quantity is not None and remaining_quantity < 0:
            errors.append(
                _issue(
                    "purchase_lots",
                    row_number,
                    "remaining_quantity",
                    "negative_quantity",
                    "remaining_quantity must be nonnegative.",
                )
            )
        if (
            original_quantity is not None
            and remaining_quantity is not None
            and remaining_quantity > original_quantity
        ):
            errors.append(
                _issue(
                    "purchase_lots",
                    row_number,
                    "remaining_quantity",
                    "remaining_exceeds_original",
                    "remaining_quantity cannot exceed original_quantity.",
                )
            )
        if unit_price is not None and unit_price < Decimal("0"):
            errors.append(_issue("purchase_lots", row_number, "unit_price", "negative_cost", "unit_price must be nonnegative."))
        if freight_cost is not None and freight_cost < Decimal("0"):
            errors.append(
                _issue(
                    "purchase_lots",
                    row_number,
                    "freight_cost_per_unit",
                    "negative_freight",
                    "freight_cost_per_unit must be nonnegative.",
                )
            )
        if unit_price == Decimal("0") and freight_cost == Decimal("0"):
            warnings.append(
                _issue(
                    "purchase_lots",
                    row_number,
                    "unit_price",
                    "zero_total_unit_cost",
                    "unit_price and freight_cost_per_unit are both zero; verify this free lot is intentional.",
                )
            )
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
            errors.append(
                _issue(
                    "movement",
                    row_number,
                    "sale_id",
                    "duplicate_sale_id",
                    f"sale_id {sale_id!r} duplicates row {seen_sale_ids[sale_id]}.",
                )
            )
        else:
            seen_sale_ids[sale_id] = row_number
        if not sku:
            errors.append(_issue("movement", row_number, "sku", "missing_required", "sku is required."))
        if quantity_sold is not None and quantity_sold <= 0:
            errors.append(
                _issue(
                    "movement",
                    row_number,
                    "quantity_sold",
                    "non_positive_quantity",
                    "quantity_sold must be greater than zero for client-test close runs.",
                )
            )
    return errors


def _read_rows(
    path: Path, file_role: str, required_columns: Iterable[str]
) -> tuple[list[tuple[int, dict]], list[CSVValidationIssue]]:
    errors: list[CSVValidationIssue] = []
    if not path.exists():
        return [], [_issue(file_role, None, None, "file_not_found", f"CSV file does not exist: {path}")]

    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing_columns = [column for column in required_columns if column not in fieldnames]
        for column in missing_columns:
            errors.append(
                _issue(
                    file_role,
                    1,
                    column,
                    "missing_required_column",
                    f"Missing required column {column!r}.",
                )
            )
        if errors:
            return [], errors
        return list(enumerate(reader, start=2)), []


def _parse_datetime(
    row: dict, field: str, row_number: int, file_role: str, errors: list[CSVValidationIssue]
) -> datetime | None:
    value = _clean(row.get(field))
    if not value:
        errors.append(_issue(file_role, row_number, field, "missing_required", f"{field} is required."))
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        errors.append(_issue(file_role, row_number, field, "invalid_date", f"{field} must be an ISO date/datetime."))
        return None


def _parse_int(
    row: dict, field: str, row_number: int, file_role: str, errors: list[CSVValidationIssue]
) -> int | None:
    value = _clean(row.get(field))
    if not value:
        errors.append(_issue(file_role, row_number, field, "missing_required", f"{field} is required."))
        return None
    try:
        return int(value)
    except ValueError:
        errors.append(_issue(file_role, row_number, field, "invalid_integer", f"{field} must be an integer."))
        return None


def _parse_decimal(
    row: dict, field: str, row_number: int, file_role: str, errors: list[CSVValidationIssue]
) -> Decimal | None:
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
    return CSVValidationIssue(
        file_role=file_role,
        row_number=row_number,
        field=field,
        code=code,
        message=message,
    )
