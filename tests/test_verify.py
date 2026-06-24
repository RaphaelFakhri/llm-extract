from __future__ import annotations

from llm_extract.schemas import ExtractionResult, ProductRecord
from llm_extract.verify import GateConfig, verify


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


def test_empty_result_fails():
    report = verify(ExtractionResult(records=[]))
    assert report.passed is False
    assert report.total == 0


def test_clean_single_source_passes():
    res = ExtractionResult(records=[_rec(price=10, currency="USD")])
    report = verify(res)
    assert report.passed is True
    assert report.flagged == 0


def test_missing_specs_flagged_as_normalization():
    res = ExtractionResult(records=[_rec(specs=[], price=10, currency="USD")])
    report = verify(res)
    kinds = {i.kind for i in report.issues}
    assert "normalization" in kinds


def test_too_many_flags_fail_gate():
    res = ExtractionResult(
        records=[
            _rec(source="a", record_id="r1", specs=[], price=10, currency="USD"),
            _rec(source="b", record_id="r2", specs=[], price=10, currency="USD"),
        ]
    )
    report = verify(res, config=GateConfig(max_flagged_fraction=0.4))
    assert report.passed is False


def test_extraction_errors_surface_as_schema_issues():
    class FakeSnippet:
        source = "a"
        record_id = "bad"

    res = ExtractionResult(records=[_rec(price=10, currency="USD")])
    report = verify(
        res,
        extraction_errors=[(FakeSnippet(), "boom")],
        config=GateConfig(fail_on_extraction_error=True),
    )
    assert report.passed is False
    assert any(i.kind == "schema" and i.record_id == "bad" for i in report.issues)
