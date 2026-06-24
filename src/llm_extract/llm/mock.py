"""Deterministic mock LLM client used in tests and key-less runs.

The mock inspects the ``Record id:`` line in the rendered user prompt and
returns a canned JSON object for known fixtures. For unknown records it falls
back to a tiny heuristic extractor over the reduced text so the chain still
produces *something* validatable. It never touches the network.
"""

from __future__ import annotations

import json
import re

# Canned responses keyed by fixture record id. Values are raw JSON strings,
# intentionally including some "messiness" the normalizer must clean
# (currency symbols, thousands separators) to prove the pipeline works.
CANNED: dict[str, dict] = {
    "product_001": {
        "sku": "sa-1001",
        "title": "Aurora Desk Lamp",
        "price": "$49.99",
        "currency": "$",
        "availability": "In stock",
        "specs": [
            {"name": "Color", "value": "Matte Black"},
            {"name": "Power", "value": "9 W"},
            {"name": "Height", "value": "45 cm"},
        ],
    },
    "product_002_missing_price": {
        "sku": "SA-1002",
        "title": "Nimbus Wall Clock",
        "price": None,
        "currency": None,
        "availability": "Preorder",
        "specs": [
            {"name": "Diameter", "value": "30 cm"},
            {"name": "Material", "value": "Oak"},
        ],
    },
    "product_003_nested_specs": {
        "sku": "SA-1003",
        "title": "Cobalt Office Chair",
        "price": "1,299.00",
        "currency": "USD",
        "availability": "In stock",
        "specs": [
            {"name": "Max Load", "value": "120 kg"},
            {"name": "Adjustable Height", "value": "Yes"},
            {"name": "Armrests", "value": "4D"},
            {"name": "Warranty", "value": "5 years"},
        ],
    },
    "listing_alpha": {
        "sku": "sb-1001",
        "title": "Aurora Desk Lamp",
        "price": "49.99",
        "currency": "USD",
        "availability": "Available",
        "specs": [
            {"name": "Color", "value": "matte black"},
            {"name": "Power", "value": "9W"},
        ],
    },
    "listing_beta_dirty_currency": {
        # Same product as source_a product_003 but with a divergent price
        # (well beyond tolerance) to exercise the consistency gate.
        "sku": "SB-1003",
        "title": "Cobalt Office Chair",
        "price": "EUR 1.799,00",
        "currency": "EUR",
        "availability": "In stock",
        "specs": [
            {"name": "Max Load", "value": "120kg"},
            {"name": "Warranty", "value": "5 yrs"},
        ],
    },
    "listing_gamma_table_specs": {
        "sku": "SB-1002",
        "title": "Nimbus Wall Clock",
        "price": "£39.00",
        "currency": "£",
        "availability": "In stock",
        "specs": [
            {"name": "Diameter", "value": "30cm"},
            {"name": "Material", "value": "oak"},
        ],
    },
}

# SKU cross-walk so source_b records align with source_a on a shared key.
# (Same physical product, different per-source SKU.) The chain leaves SKUs as
# extracted; consistency uses a configurable alias map instead.
_RECORD_ID_RE = re.compile(r"^Record id:\s*(.+)$", re.MULTILINE)


class MockLLMClient:
    """Deterministic, offline LLM client."""

    def __init__(self, extra: dict[str, dict] | None = None) -> None:
        self._table = dict(CANNED)
        if extra:
            self._table.update(extra)

    def complete(self, messages: list[dict[str, str]], *, temperature: float = 0.0) -> str:
        user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        record_id = self._extract_record_id(user)
        if record_id in self._table:
            return json.dumps(self._table[record_id])
        return json.dumps(self._heuristic(user, record_id))

    @staticmethod
    def _extract_record_id(user_prompt: str) -> str:
        match = _RECORD_ID_RE.search(user_prompt)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _heuristic(user_prompt: str, record_id: str) -> dict:
        """Very small fallback extractor for unknown records."""
        content = user_prompt.split("<<<", 1)[-1]
        title_match = re.search(r"(?im)^\s*(?:title|name)\s*[:|]\s*(.+)$", content)
        price_match = re.search(r"([$£]|EUR)\s*([\d.,]+)", content)
        return {
            "sku": record_id.upper() or "UNKNOWN",
            "title": title_match.group(1).strip() if title_match else record_id,
            "price": price_match.group(0) if price_match else None,
            "currency": price_match.group(1) if price_match else None,
            "availability": None,
            "specs": [],
        }
