# Data contract

The canonical contract is defined in `src/llm_extract/schemas.py` (pydantic v2).

## ProductRecord

| Field | Type | Rules |
| --- | --- | --- |
| `sku` | `str` | Uppercased; only `A-Z0-9-` kept; must be non-empty. |
| `title` | `str` | Internal whitespace collapsed; non-empty. |
| `price` | `float \| None` | `>= 0`; currency symbols & thousands separators removed before validation. |
| `currency` | `str \| None` | ISO-4217, one of USD/EUR/GBP/JPY/CAD/AUD. |
| `availability` | `str \| None` | Free text, whitespace-collapsed. |
| `specs` | `list[ProductSpec]` | Each `{name, value}`, both stripped. |
| `source` | `str` | Provenance: source id. |
| `record_id` | `str` | Provenance: stable id within source. |

### Invariants enforced by validators

- A non-null `price` **requires** a non-null `currency` (`model_validator`).
- Unknown currency codes raise during validation (hard fail).
- An empty SKU (after cleaning) raises during validation.

## Aggregates

- `ExtractionResult` — `records: list[ProductRecord]`, plus `by_key()` grouping.
- `ValidationReport` — `total`, `valid`, `flagged`, `issues`, `passed`.
- `RecordIssue` — `{source, record_id, kind, message}` where `kind` is one of
  `schema`, `normalization`, `consistency`.
