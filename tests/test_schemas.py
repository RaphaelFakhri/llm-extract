from __future__ import annotations

import pytest
from pydantic import ValidationError

from llm_extract.schemas import ProductRecord, coerce_record


def _base(**kw):
    data = {
        "sku": "AB-1",
        "title": "Thing",
        "source": "s",
        "record_id": "r",
        "specs": [{"name": "k", "value": "v"}],
    }
    data.update(kw)
    return data


def test_sku_normalized_uppercase_and_filtered():
    rec = ProductRecord(**_base(sku="ab_12!3"))
    assert rec.sku == "AB123"


def test_empty_sku_rejected():
    with pytest.raises(ValidationError):
        ProductRecord(**_base(sku="!!!"))


def test_title_whitespace_collapsed():
    rec = ProductRecord(**_base(title="  Cobalt   Chair  "))
    assert rec.title == "Cobalt Chair"


def test_price_requires_currency():
    with pytest.raises(ValidationError):
        ProductRecord(**_base(price=10.0, currency=None))


def test_unknown_currency_rejected():
    with pytest.raises(ValidationError):
        ProductRecord(**_base(price=10.0, currency="XYZ"))


def test_valid_priced_record():
    rec = ProductRecord(**_base(price=10.0, currency="usd"))
    assert rec.currency == "USD"
    assert rec.price == 10.0


def test_negative_price_rejected():
    with pytest.raises(ValidationError):
        ProductRecord(**_base(price=-1, currency="USD"))


def test_coerce_record_injects_provenance():
    rec = coerce_record({"sku": "x1", "title": "T", "specs": []}, source="src", record_id="rid")
    assert rec.source == "src"
    assert rec.record_id == "rid"
    assert rec.match_key() == "X1"
