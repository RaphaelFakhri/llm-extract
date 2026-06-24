"""Versioned prompt templates and the JSON output schema injected into the LLM.

The prompts encode the formatting spec (ISO currency codes, numeric prices,
unit harmonization, casing) so that even the *model* is steered toward the same
contract the deterministic normalizer and the pydantic schema enforce.
"""

from __future__ import annotations

import json

PROMPT_VERSION = "2024-10-01"

# The JSON schema we ask the model to emit. Kept compact and explicit so a
# small/cheap model can follow it reliably.
OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "sku": {"type": "string", "description": "Product SKU, uppercase alphanumeric."},
        "title": {"type": "string"},
        "price": {
            "type": ["number", "null"],
            "description": "Numeric price only, no currency symbol or thousands separators.",
        },
        "currency": {
            "type": ["string", "null"],
            "description": "ISO-4217 code such as USD, EUR, GBP. Null if unknown.",
        },
        "availability": {"type": ["string", "null"]},
        "specs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["name", "value"],
            },
        },
    },
    "required": ["sku", "title", "specs"],
}

SYSTEM_PROMPT = (
    "You are a precise data-extraction engine. You receive reduced text from a "
    "product web page and return ONLY a single JSON object matching the provided "
    "schema. Follow these rules exactly:\n"
    "- Output JSON only. No prose, no markdown fences.\n"
    "- price: numeric, currency symbol and thousands separators removed "
    "(e.g. '$1,299.00' -> 1299.00). Use null if absent.\n"
    "- currency: ISO-4217 code (USD, EUR, GBP, JPY, CAD, AUD). Map symbols "
    "($->USD, EUR/E with two strokes->EUR, GBP/pound->GBP). Use null if unknown.\n"
    "- sku: uppercase, keep only letters, digits and hyphens.\n"
    "- title: collapse internal whitespace, keep original casing.\n"
    "- specs: flatten nested tables / definition lists into name/value pairs.\n"
)

USER_TEMPLATE = (
    "Extract the product into JSON matching this schema:\n"
    "{schema}\n\n"
    "Source id: {source}\n"
    "Record id: {record_id}\n\n"
    "Reduced page text:\n"
    "<<<\n{content}\n>>>\n"
)


def render_user_prompt(*, source: str, record_id: str, content: str) -> str:
    """Render the user prompt for a single record."""
    return USER_TEMPLATE.format(
        schema=json.dumps(OUTPUT_SCHEMA, indent=2),
        source=source,
        record_id=record_id,
        content=content,
    )


def render_messages(*, source: str, record_id: str, content: str) -> list[dict[str, str]]:
    """Render the full chat message list sent to the LLM client."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": render_user_prompt(source=source, record_id=record_id, content=content),
        },
    ]
