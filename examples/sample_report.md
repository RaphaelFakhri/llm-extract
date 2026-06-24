# Extraction Verification Report

- **Status:** PASS
- **Total records:** 6
- **Valid:** 4
- **Flagged:** 2

## Flagged records

| Source | Record | Kind | Message |
| --- | --- | --- | --- |
| source_a | product_003_nested_specs | consistency | currency mismatch for 'cobalt office chair': sources disagree ['EUR', 'USD'] |
| source_b | listing_beta_dirty_currency | consistency | currency mismatch for 'cobalt office chair': sources disagree ['EUR', 'USD'] |

> The Cobalt Office Chair is listed in USD by source A and EUR by source B with a
> large nominal gap. The gate surfaces this as a consistency flag for human
> review while still passing the run overall (flagged fraction 2/6 below the 0.5
> threshold).
