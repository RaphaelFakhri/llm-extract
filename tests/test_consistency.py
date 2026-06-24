from __future__ import annotations

from llm_extract.consistency import check_consistency
from llm_extract.schemas import ExtractionResult, ProductRecord


def _rec(**kw):
    base = {
        "sku": "X1",
        "title": "Widget",
        "source": "a",
        "record_id": "r",
        "specs": [{"name": "k", "value": "v"}],
    }
    base.update(kw)
    return ProductRecord(**base)


def test_no_flag_for_single_source():
    res = ExtractionResult(records=[_rec(price=10, currency="USD")])
    out = check_consistency(res)
    assert out.issues == []


def test_matched_within_tolerance_not_flagged():
    res = ExtractionResult(
        records=[
            _rec(source="a", record_id="r1", price=100, currency="USD"),
            _rec(source="b", record_id="r2", price=103, currency="USD"),
        ]
    )
    out = check_consistency(res, price_tolerance_pct=5)
    assert out.issues == []


def test_price_divergence_flagged():
    res = ExtractionResult(
        records=[
            _rec(source="a", record_id="r1", price=100, currency="USD"),
            _rec(source="b", record_id="r2", price=130, currency="USD"),
        ]
    )
    out = check_consistency(res, price_tolerance_pct=5)
    assert len(out.issues) == 2
    assert all(i.kind == "consistency" for i in out.issues)


def test_currency_mismatch_flagged():
    res = ExtractionResult(
        records=[
            _rec(source="a", record_id="r1", price=100, currency="USD"),
            _rec(source="b", record_id="r2", price=100, currency="EUR"),
        ]
    )
    out = check_consistency(res)
    assert {i.record_id for i in out.issues} == {"r1", "r2"}
    assert all("currency mismatch" in i.message for i in out.issues)


def test_dedup_exact_duplicates():
    dup = _rec(source="a", record_id="r1", price=10, currency="USD")
    res = ExtractionResult(records=[dup, dup])
    out = check_consistency(res)
    assert len(out.deduplicated) == 1
