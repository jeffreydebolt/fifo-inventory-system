"""Fixture-backed Amazon SP-API mock connector.

This connector proves the future onboarding shape without credentials, OAuth,
HTTP clients, or live Amazon calls.
"""
from __future__ import annotations

import json
from pathlib import Path

from .amazon_sp_api_contract import AmazonConnectorSafety


class AmazonSPAPIMockConnector:
    """Read deterministic Amazon-shaped fixture JSON from a local directory."""

    def __init__(self, fixture_dir: str | Path):
        self.fixture_dir = Path(fixture_dir)
        self.safety = AmazonConnectorSafety()

    def safety_payload(self) -> dict:
        return self.safety.to_dict()

    def account(self) -> dict:
        return self._read_json("account.json")

    def inventory(self) -> list[dict]:
        return self._read_json("inventory.json")

    def sales_movements(self, *, period: str) -> list[dict]:
        movements = self._read_json("sales_movements.json")
        return [row for row in movements if str(row.get("sale_date", "")).startswith(period)]

    def other_warehouse_counts(self) -> list[dict]:
        return self._read_json("other_warehouse_counts.json")

    def purchase_lot_guidance(self) -> list[dict]:
        return self._read_json("purchase_lot_guidance.json")

    def _read_json(self, name: str):
        path = self.fixture_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Amazon mock fixture missing: {path}")
        return json.loads(path.read_text(encoding="utf-8"))
