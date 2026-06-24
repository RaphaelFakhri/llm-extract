# Formatting specification

This is the authoritative output spec. It is enforced in **three** places so a
violation cannot slip through: the LLM prompt (`prompts.py`), the deterministic
normalizer (`normalize.py`), and the pydantic schema (`schemas.py`).

## Currency

- Output ISO-4217 codes only: `USD`, `EUR`, `GBP`, `JPY`, `CAD`, `AUD`.
- Symbol mapping: `$`→`USD`, `EUR sign`→`EUR`, `GBP sign`→`GBP`, `JPY sign`→`JPY`,
  `C$`→`CAD`, `A$`→`AUD`.
- Unknown / unmappable currency ⇒ `null` (and the price must then also be `null`).

## Price

- Numeric only — no symbols, no thousands separators.
- US convention `1,299.00` and EU convention `1.799,00` both parse correctly.
- Missing price ⇒ `null` (valid; e.g. preorder pages).

## SKU

- Uppercase; keep only `A-Z`, `0-9`, and `-`. Everything else stripped.

## Units (spec values)

- Normalize spacing: `9W` → `9 W`, `30cm` → `30 cm`, `120kg` → `120 kg`.
- `yrs`/`yr` → `years`. Booleans cased as `Yes`/`No`.

## Text

- Collapse internal whitespace in `title` and `availability`.
- Preserve original casing of titles and free-text spec values (only spacing /
  unit tokens are harmonized).

## Casing note

Spec *values* keep their source casing (e.g. `matte black`, `oak`) on purpose —
they are user-facing descriptions, not controlled vocabulary. Only structural
formatting (currency, numbers, units, SKU) is forced.
