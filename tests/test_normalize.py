from __future__ import annotations

import pytest

from llm_extract.normalize import (
    normalize_currency,
    normalize_record_dict,
    normalize_value,
    parse_price,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("$", "USD"),
        ("usd", "USD"),
        ("EUR", "EUR"),
        ("£", "GBP"),
        ("EUR 1.799,00", "EUR"),
        ("nonsense", None),
        (None, None),
    ],
)
def test_normalize_currency(raw, expected):
    assert normalize_currency(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("$1,299.00", 1299.0),
        ("1.799,00", 1799.0),
        ("49.99", 49.99),
        ("EUR 1.799,00", 1799.0),
        ("£39.00", 39.0),
        ("1,234", 1234.0),
        (None, None),
        ("", None),
        (10, 10.0),
    ],
)
def test_parse_price(raw, expected):
    assert parse_price(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("9W", "9 W"),
        ("30cm", "30 cm"),
        ("120kg", "120 kg"),
        ("5 yrs", "5 years"),
        ("  matte   black ", "matte black"),
    ],
)
def test_normalize_value(raw, expected):
    assert normalize_value(raw) == expected


def test_normalize_record_dict_recovers_currency_from_price_string():
    out = normalize_record_dict(
        {"price": "$1,299.00", "currency": None, "title": " A  B ", "specs": []}
    )
    assert out["price"] == 1299.0
    assert out["currency"] == "USD"
    assert out["title"] == "A B"


def test_normalize_record_dict_filters_bad_specs():
    out = normalize_record_dict(
        {"specs": [{"name": "", "value": "x"}, {"name": "K", "value": "9W"}, "bad"]}
    )
    assert out["specs"] == [{"name": "K", "value": "9 W"}]
