"""Structured delivery sinks: JSON (always) and Google Sheets (optional)."""

from __future__ import annotations

from llm_extract.delivery.json_sink import write_json
from llm_extract.delivery.sheets import COLUMNS, SheetsDelivery, records_to_rows

__all__ = ["write_json", "SheetsDelivery", "records_to_rows", "COLUMNS"]
