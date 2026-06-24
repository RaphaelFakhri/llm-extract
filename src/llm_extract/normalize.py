"""Deterministic post-LLM normalization.

Runs *before* pydantic validation. Converts currency symbols to ISO codes,
parses messy numeric prices (``$1,299.00`` / ``1.799,00``), harmonizes simple
units, and tidies whitespace/casing so the schema validators see clean input.
This layer makes the pipeline robust even if the LLM emits raw, un-normalized
values.
"""

from __future__ import annotations

import re
from typing import Any

CURRENCY_SYMBOLS: dict[str, str] = {
    "$": "USD",
    "US$": "USD",
    "USD": "USD",
    "€": "EUR",  # EUR sign
    "EUR": "EUR",
    "£": "GBP",  # GBP sign
    "GBP": "GBP",
    "¥": "JPY",  # JPY sign
    "JPY": "JPY",
    "C$": "CAD",
    "CAD": "CAD",
    "A$": "AUD",
    "AUD": "AUD",
}

_CURRENCY_TOKEN_RE = re.compile(
    r"(US\$|C\$|A\$|\$|€|£|¥|USD|EUR|GBP|JPY|CAD|AUD)",
    re.IGNORECASE,
)

# Unit harmonization for spec values (lightweight, conservative).
_UNIT_SUBS = [
    (re.compile(r"(?i)\b(\d+)\s*kg\b"), r"\1 kg"),
    (re.compile(r"(?i)\b(\d+)\s*w\b"), r"\1 W"),
    (re.compile(r"(?i)\b(\d+)\s*cm\b"), r"\1 cm"),
    (re.compile(r"(?i)\byes\b"), "Yes"),
    (re.compile(r"(?i)\bno\b"), "No"),
    (re.compile(r"(?i)\b(\d+)\s*yrs?\b"), r"\1 years"),
]


def normalize_currency(raw: str | None) -> str | None:
    """Map a currency symbol/code to its ISO-4217 code, or None."""
    if not raw:
        return None
    token = raw.strip()
    if token.upper() in CURRENCY_SYMBOLS:
        return CURRENCY_SYMBOLS[token.upper()]
    if token in CURRENCY_SYMBOLS:
        return CURRENCY_SYMBOLS[token]
    match = _CURRENCY_TOKEN_RE.search(token)
    if match:
        key = match.group(1)
        return CURRENCY_SYMBOLS.get(key.upper(), CURRENCY_SYMBOLS.get(key))
    return None


def parse_price(raw: Any) -> float | None:
    """Parse a possibly-messy price into a float.

    Handles thousands separators in both ``1,299.00`` (US) and ``1.799,00``
    (EU) conventions, and strips any currency token.
    """
    if raw is None:
        return None
    if isinstance(raw, int | float):
        return float(raw)
    text = str(raw).strip()
    if not text:
        return None
    # Drop currency tokens and any non-numeric noise except separators.
    text = _CURRENCY_TOKEN_RE.sub("", text).strip()
    text = re.sub(r"[^\d.,-]", "", text)
    if not text:
        return None

    has_comma = "," in text
    has_dot = "." in text
    if has_comma and has_dot:
        # The right-most separator is the decimal point.
        if text.rfind(",") > text.rfind("."):
            # EU style: '.' thousands, ',' decimal
            text = text.replace(".", "").replace(",", ".")
        else:
            # US style: ',' thousands, '.' decimal
            text = text.replace(",", "")
    elif has_comma:
        # Ambiguous: treat ',' as decimal if it looks like cents, else thousands.
        if re.match(r"^\d{1,3}(,\d{3})+$", text):
            text = text.replace(",", "")
        else:
            text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def normalize_value(value: str) -> str:
    """Harmonize units and whitespace within a spec value."""
    out = " ".join(str(value).split())
    for pattern, repl in _UNIT_SUBS:
        out = pattern.sub(repl, out)
    return out


def normalize_record_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw extracted dict in place-safe fashion, returning a new dict."""
    out: dict[str, Any] = dict(data)

    out["currency"] = normalize_currency(data.get("currency"))
    out["price"] = parse_price(data.get("price"))

    # If currency wasn't given but the price string carried a symbol, recover it.
    if out["currency"] is None and isinstance(data.get("price"), str):
        out["currency"] = normalize_currency(data["price"])

    if isinstance(out.get("title"), str):
        out["title"] = " ".join(out["title"].split())

    if isinstance(out.get("availability"), str):
        out["availability"] = " ".join(out["availability"].split()) or None

    specs = data.get("specs") or []
    norm_specs = []
    for spec in specs:
        if not isinstance(spec, dict):
            continue
        name = " ".join(str(spec.get("name", "")).split())
        value = normalize_value(spec.get("value", ""))
        if name:
            norm_specs.append({"name": name, "value": value})
    out["specs"] = norm_specs

    return out
