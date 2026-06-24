from __future__ import annotations

from llm_extract.delivery.sheets import COLUMNS, SheetsDelivery, records_to_rows
from llm_extract.schemas import ExtractionResult, ProductRecord


def _result():
    return ExtractionResult(
        records=[
            ProductRecord(
                sku="A1",
                title="Lamp",
                price=49.99,
                currency="USD",
                availability="In stock",
                source="source_a",
                record_id="r1",
                specs=[{"name": "Color", "value": "Black"}, {"name": "Power", "value": "9 W"}],
            )
        ]
    )


def test_records_to_rows_header_and_specs():
    rows = records_to_rows(_result())
    assert rows[0] == COLUMNS
    data_row = rows[1]
    assert data_row[COLUMNS.index("sku")] == "A1"
    assert data_row[COLUMNS.index("price")] == 49.99
    assert data_row[COLUMNS.index("specs")] == "Color=Black; Power=9 W"


def test_sheets_delivery_uses_injected_client(fake_gspread_client):
    delivery = SheetsDelivery(fake_gspread_client, sheet_id="SHEET123")
    written = delivery.deliver(_result())
    assert written == 1
    assert fake_gspread_client.opened_key == "SHEET123"
    ws = fake_gspread_client.worksheet
    assert ws.cleared is True
    assert ws.values[0] == COLUMNS
    assert ws.values[1][COLUMNS.index("title")] == "Lamp"
