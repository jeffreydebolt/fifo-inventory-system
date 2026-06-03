"""Pure CSV ingestion for local/demo FIFO runs.

This module is intentionally strict and dependency-free. It does not import
Supabase, dotenv, pandas, or any application runtime code.
"""
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List

from .models import InventorySnapshot, PurchaseLot, Sale


class CSVIngestError(ValueError):
    """Raised when a local FIFO CSV cannot be parsed safely."""


def _required(row: dict, field: str, row_number: int) -> str:
    value = (row.get(field) or "").strip()
    if value == "":
        raise CSVIngestError(f"Row {row_number}: missing required field '{field}'")
    return value


def _parse_datetime(value: str, field: str, row_number: int) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise CSVIngestError(
            f"Row {row_number}: field '{field}' must be ISO date/datetime, got {value!r}"
        ) from exc


def _parse_int(value: str, field: str, row_number: int) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise CSVIngestError(
            f"Row {row_number}: field '{field}' must be an integer, got {value!r}"
        ) from exc


def _parse_decimal(value: str, field: str, row_number: int) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise CSVIngestError(
            f"Row {row_number}: field '{field}' must be a decimal, got {value!r}"
        ) from exc


def load_purchase_lots_csv(path: str | Path, snapshot_timestamp: datetime | None = None) -> InventorySnapshot:
    """Load purchase lots from a local CSV into an inventory snapshot."""
    lots: List[PurchaseLot] = []
    with Path(path).open(newline="") as handle:
        for row_number, row in enumerate(csv.DictReader(handle), start=2):
            original_quantity = _parse_int(
                _required(row, "original_quantity", row_number), "original_quantity", row_number
            )
            remaining_raw = (row.get("remaining_quantity") or "").strip()
            remaining_quantity = (
                _parse_int(remaining_raw, "remaining_quantity", row_number)
                if remaining_raw
                else original_quantity
            )
            lots.append(
                PurchaseLot(
                    lot_id=_required(row, "lot_id", row_number),
                    sku=_required(row, "sku", row_number),
                    received_date=_parse_datetime(
                        _required(row, "received_date", row_number), "received_date", row_number
                    ),
                    original_quantity=original_quantity,
                    remaining_quantity=remaining_quantity,
                    unit_price=_parse_decimal(
                        _required(row, "unit_price", row_number), "unit_price", row_number
                    ),
                    freight_cost_per_unit=_parse_decimal(
                        _required(row, "freight_cost_per_unit", row_number),
                        "freight_cost_per_unit",
                        row_number,
                    ),
                )
            )
    return InventorySnapshot(timestamp=snapshot_timestamp or datetime.now(), lots=lots)


def load_movement_csv(path: str | Path) -> List[Sale]:
    """Load sale/movement rows from a local CSV."""
    sales: List[Sale] = []
    with Path(path).open(newline="") as handle:
        for row_number, row in enumerate(csv.DictReader(handle), start=2):
            sales.append(
                Sale(
                    sale_id=_required(row, "sale_id", row_number),
                    sku=_required(row, "sku", row_number),
                    sale_date=_parse_datetime(
                        _required(row, "sale_date", row_number), "sale_date", row_number
                    ),
                    quantity_sold=_parse_int(
                        _required(row, "quantity_sold", row_number), "quantity_sold", row_number
                    ),
                )
            )
    return sales
