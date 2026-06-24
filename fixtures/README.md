# Fixtures

These HTML files are **hand-authored, synthetic, and fictional**. The products
(Aurora Desk Lamp, Nimbus Wall Clock, Cobalt Office Chair) and their SKUs/prices
do not correspond to any real catalog. They were written for this repository to
exercise the pipeline and therefore carry **no third-party copyright or
Terms-of-Service concerns**.

## Why commit messy fixtures?

Real product/listing HTML is inconsistent and hierarchical. To prove the
extraction + normalization + verification pipeline works, the fixtures are
*deliberately* messy in different ways:

| File | What it stresses |
| --- | --- |
| `source_a/product_001.html` | currency symbol (`$`), `<table>` specs, stray `<script>`/`<style>` |
| `source_a/product_002_missing_price.html` | **missing price**, `<dl>` definition-list specs |
| `source_a/product_003_nested_specs.html` | thousands separator (`$1,299.00`), nested `<div class="spec">` specs |
| `source_b/listing_alpha.html` | same product as source A, different SKU/casing/units (`9W`) |
| `source_b/listing_beta_dirty_currency.html` | **EU currency formatting** (`EUR 1.799,00`) and a price that **diverges** from source A for the same product (consistency flag) |
| `source_b/listing_gamma_table_specs.html` | GBP symbol entity (`&pound;`), compact units (`30cm`) |

## Cross-source design

`source_a` and `source_b` describe the **same three products** under different
per-source SKUs. This lets the consistency controls align records by normalized
title and detect the intentional price divergence on the office chair.

## Expected output

`expected/source_a.json` and `expected/source_b.json` are the canonical,
post-normalization, post-validation records. `tests/test_chain_mock.py` asserts
the mock-LLM chain reproduces them exactly.
