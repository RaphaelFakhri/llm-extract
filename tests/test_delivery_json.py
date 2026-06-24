from __future__ import annotations

import json

from llm_extract.delivery.json_sink import serialize, write_json
from llm_extract.schemas import ExtractionResult, ProductRecord


def _result():
    return ExtractionResult(
        records=[
            ProductRecord(
                sku="B1",
                title="B",
                source="z",
                record_id="r2",
                specs=[{"name": "k", "value": "v"}],
            ),
            ProductRecord(
                sku="A1",
                title="A",
                source="a",
                record_id="r1",
                specs=[{"name": "k", "value": "v"}],
            ),
        ]
    )


def test_serialize_is_deterministic_and_sorted():
    out1 = serialize(_result())
    out2 = serialize(_result())
    assert out1 == out2
    data = json.loads(out1)
    sources = [r["source"] for r in data["records"]]
    assert sources == ["a", "z"]  # sorted by (source, record_id)


def test_write_json_roundtrip(tmp_path):
    path = write_json(_result(), tmp_path / "nested" / "out.json")
    assert path.exists()
    data = json.loads(path.read_text())
    assert len(data["records"]) == 2
