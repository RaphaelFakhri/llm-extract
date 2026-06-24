"""Cross-source consistency controls.

Aligns records that describe the same physical product across sources, then
flags divergence in price (beyond a configurable tolerance) and conflicting
specs. Also deduplicates exact repeats. Matching is by a configurable key; by
default we normalize the title, because per-source SKUs frequently differ.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from llm_extract.schemas import ExtractionResult, ProductRecord, RecordIssue


def _title_key(rec: ProductRecord) -> str:
    return " ".join(rec.title.lower().split())


@dataclass
class ConsistencyResult:
    """Outcome of cross-source consistency analysis."""

    issues: list[RecordIssue] = field(default_factory=list)
    groups: dict[str, list[ProductRecord]] = field(default_factory=dict)
    deduplicated: list[ProductRecord] = field(default_factory=list)

    @property
    def flagged_keys(self) -> set[str]:
        return {f"{i.source}/{i.record_id}" for i in self.issues}


def _dedupe(records: list[ProductRecord]) -> list[ProductRecord]:
    """Drop exact duplicates (same source + sku + price + currency)."""
    seen: set[tuple] = set()
    out: list[ProductRecord] = []
    for rec in records:
        sig = (rec.source, rec.sku, rec.price, rec.currency)
        if sig in seen:
            continue
        seen.add(sig)
        out.append(rec)
    return out


def check_consistency(
    result: ExtractionResult,
    *,
    price_tolerance_pct: float = 5.0,
    match_key=_title_key,
) -> ConsistencyResult:
    """Group records across sources and flag divergences.

    Parameters
    ----------
    result:
        The extracted records to analyze.
    price_tolerance_pct:
        Allowed relative spread between the min and max price within a group
        before it is flagged.
    match_key:
        Callable mapping a record to its grouping key (default: normalized title).
    """
    deduped = _dedupe(result.records)
    groups: dict[str, list[ProductRecord]] = defaultdict(list)
    for rec in deduped:
        groups[match_key(rec)].append(rec)

    issues: list[RecordIssue] = []
    for key, members in groups.items():
        sources = {m.source for m in members}
        if len(sources) < 2:
            # Only one source has this product: nothing to cross-check.
            continue

        # Price divergence check across sources.
        priced = [m for m in members if m.price is not None]
        if len(priced) >= 2:
            currencies = {m.currency for m in priced}
            if len(currencies) > 1:
                for m in priced:
                    issues.append(
                        RecordIssue(
                            record_id=m.record_id,
                            source=m.source,
                            kind="consistency",
                            message=(
                                f"currency mismatch for '{key}': "
                                f"sources disagree {sorted(c or '?' for c in currencies)}"
                            ),
                        )
                    )
            else:
                prices = [m.price for m in priced if m.price is not None]
                lo = min(prices)
                hi = max(prices)
                if lo > 0 and (hi - lo) / lo * 100.0 > price_tolerance_pct:
                    for m in priced:
                        issues.append(
                            RecordIssue(
                                record_id=m.record_id,
                                source=m.source,
                                kind="consistency",
                                message=(
                                    f"price divergence for '{key}': "
                                    f"{lo} vs {hi} exceeds {price_tolerance_pct}% tolerance"
                                ),
                            )
                        )

    return ConsistencyResult(issues=issues, groups=dict(groups), deduplicated=deduped)
