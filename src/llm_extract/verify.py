"""The systematic verification gate.

Aggregates three signals into a single pass/fail decision that blocks delivery:

1. schema validity   — records that failed pydantic during the chain
2. normalization      — records whose required fields are still missing/odd
3. consistency        — cross-source divergences flagged by :mod:`consistency`

The thresholds are explicit and unit-tested so the gate is neither too lenient
(shipping bad data) nor too strict (blocking everything).
"""

from __future__ import annotations

from dataclasses import dataclass

from llm_extract.consistency import ConsistencyResult, check_consistency
from llm_extract.schemas import (
    ExtractionResult,
    ProductRecord,
    RecordIssue,
    ValidationReport,
)


@dataclass
class GateConfig:
    """Thresholds controlling the pass/fail decision."""

    # Maximum fraction of records allowed to be flagged before the gate fails.
    max_flagged_fraction: float = 0.5
    # If True, any chain-level extraction failure fails the gate.
    fail_on_extraction_error: bool = False
    price_tolerance_pct: float = 5.0


def _normalization_issues(records: list[ProductRecord]) -> list[RecordIssue]:
    """Catch records that are schema-valid but semantically incomplete."""
    issues: list[RecordIssue] = []
    for rec in records:
        if rec.price is not None and rec.currency is None:
            issues.append(
                RecordIssue(
                    record_id=rec.record_id,
                    source=rec.source,
                    kind="normalization",
                    message="price present without a currency",
                )
            )
        if not rec.specs:
            issues.append(
                RecordIssue(
                    record_id=rec.record_id,
                    source=rec.source,
                    kind="normalization",
                    message="record has no specifications",
                )
            )
    return issues


def verify(
    result: ExtractionResult,
    *,
    extraction_errors: list[tuple] | None = None,
    config: GateConfig | None = None,
    consistency: ConsistencyResult | None = None,
) -> ValidationReport:
    """Run the full verification gate and return a :class:`ValidationReport`."""
    config = config or GateConfig()
    extraction_errors = extraction_errors or []

    issues: list[RecordIssue] = []

    # 1. Extraction/schema failures surfaced by the chain.
    for snippet, message in extraction_errors:
        issues.append(
            RecordIssue(
                record_id=getattr(snippet, "record_id", "?"),
                source=getattr(snippet, "source", "?"),
                kind="schema",
                message=message,
            )
        )

    # 2. Normalization completeness.
    issues.extend(_normalization_issues(result.records))

    # 3. Cross-source consistency.
    cons = consistency or check_consistency(result, price_tolerance_pct=config.price_tolerance_pct)
    issues.extend(cons.issues)

    total = len(result.records) + len(extraction_errors)
    flagged_records = {(i.source, i.record_id) for i in issues}
    valid = len(result.records) - len(
        {(i.source, i.record_id) for i in issues if i.kind != "normalization"}
        & {(r.source, r.record_id) for r in result.records}
    )
    valid = max(valid, 0)

    passed = True
    if total == 0:
        passed = False
    else:
        flagged_fraction = len(flagged_records) / total
        if flagged_fraction > config.max_flagged_fraction:
            passed = False
    if config.fail_on_extraction_error and extraction_errors:
        passed = False

    return ValidationReport.from_counts(
        total=total,
        valid=valid,
        issues=issues,
        passed=passed,
    )
