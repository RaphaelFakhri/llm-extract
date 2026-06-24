# Architecture

```
            ┌────────────┐
fixtures ──▶│  ingest    │── RawSnippet ─┐
(HTML)      │ fixtures   │               │
            └────────────┘               ▼
live ──────▶ live_source ─────────▶ ┌─────────────────────────────┐
(opt-in)                            │        ExtractionChain       │
                                    │  reduce_html (preprocess)    │
                                    │   └▶ render prompt (prompts) │
                                    │       └▶ LLM.complete        │
                                    │           (OpenRouter|mock)  │
                                    │           └▶ parse+repair    │
                                    │               └▶ normalize   │
                                    │                   └▶ pydantic │
                                    └──────────────┬──────────────┘
                                                   │ ProductRecord[]
                                                   ▼
                                        ┌────────────────────┐
                                        │  consistency        │ cross-source
                                        │  (align + diverge)  │ flags + dedupe
                                        └─────────┬──────────┘
                                                  ▼
                                        ┌────────────────────┐
                                        │   verify (gate)     │ pass/fail
                                        │   + report (md/rich)│
                                        └─────────┬──────────┘
                                       pass │           │ fail → block
                                            ▼           ▼
                                ┌────────────────┐  (exit 1)
                                │   delivery     │
                                │ sheets | json  │
                                └────────────────┘
```

## Design principles

- **One seam for the LLM** (`llm/base.py::LLMClient`). The real OpenRouter
  client and the deterministic mock are interchangeable. The mock is the default
  whenever no API key is configured, which is what makes the whole suite run
  offline.
- **Deterministic normalization before validation.** The LLM is allowed to be
  sloppy; `normalize.py` fixes currency/number/unit/casing issues, and the
  pydantic schema in `schemas.py` is the hard gate.
- **Verification blocks delivery.** `verify.py` produces a `ValidationReport`
  with an explicit pass/fail; the CLI exits non-zero and refuses to deliver on
  failure.
- **Delivery is injectable.** `delivery/sheets.py` takes a client object, so
  tests pass a fake and never touch Google. Without credentials, delivery falls
  back to deterministic JSON.

See `data_contract.md` for the schema and `formatting_spec.md` for the rules.
