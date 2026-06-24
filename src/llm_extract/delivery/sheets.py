"""Google Sheets delivery via gspread + google-auth.

The gspread client is *injectable*, so tests pass a fake worksheet and no real
auth or network occurs. In production, credentials are loaded from a service
account (file path or inline JSON) and records are written to a fixed column
spec. When credentials are absent, callers fall back to the JSON sink.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from llm_extract.schemas import ExtractionResult, ProductRecord

# Fixed column spec — the contract for the destination sheet.
COLUMNS: list[str] = [
    "source",
    "record_id",
    "sku",
    "title",
    "price",
    "currency",
    "availability",
    "specs",
]

# OAuth scopes required to edit a spreadsheet.
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _format_specs(record: ProductRecord) -> str:
    return "; ".join(f"{s.name}={s.value}" for s in record.specs)


def records_to_rows(result: ExtractionResult) -> list[list[Any]]:
    """Convert records into a header + data row matrix matching :data:`COLUMNS`."""
    rows: list[list[Any]] = [list(COLUMNS)]
    ordered = sorted(result.records, key=lambda r: (r.source, r.record_id))
    for rec in ordered:
        rows.append(
            [
                rec.source,
                rec.record_id,
                rec.sku,
                rec.title,
                "" if rec.price is None else rec.price,
                rec.currency or "",
                rec.availability or "",
                _format_specs(rec),
            ]
        )
    return rows


class Worksheet(Protocol):
    """The minimal slice of a gspread worksheet that we use."""

    def clear(self) -> Any: ...

    def update(self, values: list[list[Any]], range_name: str | None = ...) -> Any: ...


class SheetsClient(Protocol):
    """Minimal gspread client surface for opening a worksheet."""

    def open_by_key(self, key: str) -> Any: ...


def build_gspread_client(service_account_json: str) -> Any:
    """Build a real gspread client from a service-account file path or inline JSON.

    Imported lazily so gspread/google-auth are only needed when actually
    delivering to Sheets.
    """
    import gspread
    from google.oauth2.service_account import Credentials

    candidate = Path(service_account_json)
    if candidate.exists():
        info = json.loads(candidate.read_text(encoding="utf-8"))
    else:
        info = json.loads(service_account_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


class SheetsDelivery:
    """Writes validated records to a Google Sheet using an injectable client."""

    def __init__(self, client: SheetsClient, *, sheet_id: str, worksheet_index: int = 0) -> None:
        self._client = client
        self._sheet_id = sheet_id
        self._worksheet_index = worksheet_index

    def _worksheet(self) -> Worksheet:
        spreadsheet = self._client.open_by_key(self._sheet_id)
        return spreadsheet.get_worksheet(self._worksheet_index)

    def deliver(self, result: ExtractionResult) -> int:
        """Write all records to the sheet, returning the number of data rows."""
        rows = records_to_rows(result)
        ws = self._worksheet()
        ws.clear()
        ws.update(rows, range_name="A1")
        return len(rows) - 1  # exclude header
