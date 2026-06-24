"""Canonical, validated data contract (pydantic v2).

These models are the single source of truth for what valid extracted data looks
like. Field validators enforce the formatting spec (ISO currency codes, numeric
prices, normalized SKUs) so that anything reaching delivery is already clean.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# ISO-4217 currency codes we recognize for the synthetic catalog.
KNOWN_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "CAD", "AUD"}

_SKU_RE = re.compile(r"[^A-Z0-9-]")


class RawSnippet(BaseModel):
    """A unit of source HTML with provenance, fed into the chain."""

    source: str = Field(description="Logical source id, e.g. 'source_a'.")
    record_id: str = Field(description="Stable id within the source (often the filename stem).")
    path: str = Field(description="Origin path or URL for traceability.")
    html: str = Field(description="Raw, possibly messy HTML.")


class ProductSpec(BaseModel):
    """A single normalized key/value specification."""

    name: str
    value: str

    @field_validator("name", "value")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class ProductRecord(BaseModel):
    """A validated product record — the core deliverable unit."""

    sku: str = Field(description="Uppercase alphanumeric SKU.")
    title: str
    price: float | None = Field(default=None, ge=0, description="Numeric price, currency-stripped.")
    currency: str | None = Field(default=None, description="ISO-4217 code, e.g. 'USD'.")
    availability: str | None = Field(default=None)
    specs: list[ProductSpec] = Field(default_factory=list)
    source: str
    record_id: str

    @field_validator("sku")
    @classmethod
    def _normalize_sku(cls, v: str) -> str:
        cleaned = _SKU_RE.sub("", v.strip().upper())
        if not cleaned:
            raise ValueError("SKU must contain at least one alphanumeric character")
        return cleaned

    @field_validator("title")
    @classmethod
    def _title_not_empty(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("title must not be empty")
        return v

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().upper()
        if v not in KNOWN_CURRENCIES:
            raise ValueError(f"unknown currency code: {v!r}")
        return v

    @model_validator(mode="after")
    def _price_requires_currency(self) -> ProductRecord:
        if self.price is not None and self.currency is None:
            raise ValueError("a price must be accompanied by a currency code")
        return self

    def match_key(self) -> str:
        """Key used to align the same product across sources."""
        return self.sku


class ExtractionResult(BaseModel):
    """The aggregated, deduplicated output of an extraction run."""

    records: list[ProductRecord] = Field(default_factory=list)

    def by_key(self) -> dict[str, list[ProductRecord]]:
        grouped: dict[str, list[ProductRecord]] = {}
        for rec in self.records:
            grouped.setdefault(rec.match_key(), []).append(rec)
        return grouped


class RecordIssue(BaseModel):
    """A single problem attributed to a record (or a group of records)."""

    record_id: str
    source: str
    kind: str = Field(description="e.g. 'schema', 'normalization', 'consistency'.")
    message: str


class ValidationReport(BaseModel):
    """Outcome of the verification gate."""

    total: int = 0
    valid: int = 0
    flagged: int = 0
    issues: list[RecordIssue] = Field(default_factory=list)
    passed: bool = False

    def add_issue(self, issue: RecordIssue) -> None:
        self.issues.append(issue)

    @classmethod
    def from_counts(
        cls,
        *,
        total: int,
        valid: int,
        issues: list[RecordIssue],
        passed: bool,
    ) -> ValidationReport:
        return cls(
            total=total,
            valid=valid,
            flagged=len(issues),
            issues=issues,
            passed=passed,
        )


def coerce_record(data: dict[str, Any], *, source: str, record_id: str) -> ProductRecord:
    """Build a :class:`ProductRecord`, injecting provenance if absent."""
    payload = dict(data)
    payload.setdefault("source", source)
    payload.setdefault("record_id", record_id)
    return ProductRecord.model_validate(payload)
