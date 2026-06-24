# llm-extract

**LLM-assisted extraction from messy, inconsistent HTML into validated, cross-checked, delivered data.**

[![CI](https://github.com/RaphaelFakhri/llm-extract/actions/workflows/ci.yml/badge.svg)](https://github.com/RaphaelFakhri/llm-extract/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Ruff](https://img.shields.io/badge/lint-ruff-orange)
![License](https://img.shields.io/badge/license-MIT-green)

Hand-written HTML parsers break the moment a source changes its markup. This
project uses an LLM (via OpenRouter) inside a small, deterministic, **verifiable**
pipeline: messy HTML is reduced, sent to the model under a strict schema,
deterministically normalized, validated by pydantic, cross-checked across
sources, gated by a systematic verification step, and only then delivered to
Google Sheets or JSON. It runs **fully offline** in tests via a deterministic
mock LLM — no API key required.

## Skills demonstrated

| Capability (job bullet) | Where it is proven (file / function) |
| --- | --- |
| LLM frameworks applied to automation (OpenRouter) | `src/llm_extract/llm/openrouter.py::OpenRouterClient.complete` |
| LangChain-style composable chain | `src/llm_extract/chain.py::ExtractionChain` |
| Extraction from inconsistent / hierarchical HTML | `src/llm_extract/ingest/preprocess.py::reduce_html` |
| Data cleaning & normalization | `src/llm_extract/normalize.py::normalize_record_dict`, `parse_price` |
| Validation (pydantic) | `src/llm_extract/schemas.py::ProductRecord` (field/model validators) |
| Cross-source consistency controls | `src/llm_extract/consistency.py::check_consistency` |
| Formatting-spec adherence | `docs/formatting_spec.md` enforced in prompts + normalize + schema |
| Systematic verification before delivery | `src/llm_extract/verify.py::verify` (the gate) |
| QA report | `src/llm_extract/report.py::render_markdown` / `print_console` |
| Structured delivery to Google Sheets | `src/llm_extract/delivery/sheets.py::SheetsDelivery.deliver` |
| Structured delivery to JSON | `src/llm_extract/delivery/json_sink.py::write_json` |
| Offline, mocked tests | `src/llm_extract/llm/mock.py::MockLLMClient`, `tests/` |
| Safe live fetching (robots/rate-limit, opt-in) | `src/llm_extract/ingest/live_source.py::fetch_live_source` |
| CLI orchestration | `src/llm_extract/cli.py` (`extract`/`verify`/`deliver`/`run`) |

## Architecture

```
ingest ─▶ preprocess ─▶ chain (OpenRouter | mock) ─▶ normalize ─▶ validate
       ─▶ consistency ─▶ verify gate ─▶ report ─▶ delivery (Sheets | JSON)
```

The LLM lives behind a single protocol (`llm/base.py::LLMClient`), so the real
OpenRouter client and the deterministic mock are interchangeable. Normalization
is deterministic and runs *before* the pydantic gate, so a sloppy model can't
produce invalid data. The verification gate returns an explicit pass/fail and
**blocks delivery** on failure. Full diagram in [`docs/architecture.md`](docs/architecture.md).

## Quickstart (offline, no keys)

```bash
git clone <this-repo> && cd llm-extract
python -m pip install -e ".[dev]"

pytest                      # full suite, fully offline
llm-extract run --dry-run   # end-to-end with the mock LLM + JSON output
```

`run --dry-run` ingests the synthetic fixtures, extracts + normalizes + validates
them, prints a verification report (flagging the deliberate cross-source price
divergence), and writes deterministic JSON to `out/delivery.json`.

You can also run the scripted example:

```bash
python examples/run_pipeline.py
```

## Running with real services

Copy `.env.example` to `.env` and fill in what you need; everything is optional.

- **Real LLM:** set `OPENROUTER_API_KEY` (and optionally `OPENROUTER_MODEL`). The
  real client is selected automatically when the key is present.
- **Google Sheets:** set `GOOGLE_SERVICE_ACCOUNT_JSON` (file path *or* inline
  JSON) and `GSHEET_ID`. Share the sheet with the service-account email. When
  both are present, `deliver`/`run` write to the sheet; otherwise they fall back
  to JSON.

```bash
llm-extract run                       # real LLM if key set; real Sheets if creds set
llm-extract run --dry-run             # never calls external services
llm-extract verify --report-out qa.md # QA report + non-zero exit on failure
```

## The data contract

`src/llm_extract/schemas.py` defines the pydantic v2 models. The authoritative
formatting rules (ISO currency codes, numeric prices, unit harmonization, SKU
casing) live in [`docs/formatting_spec.md`](docs/formatting_spec.md) and the
field-level contract in [`docs/data_contract.md`](docs/data_contract.md).

## Verification & QA

`verify.py` aggregates schema validity, normalization completeness, and
cross-source consistency into one `ValidationReport` with explicit, unit-tested
thresholds. The report always lists every flagged record. A sample is in
[`examples/sample_report.md`](examples/sample_report.md).

## Google Sheets delivery

Fixed column spec: `source, record_id, sku, title, price, currency,
availability, specs`. The gspread client is injectable, so tests use a fake and
never touch Google. Without credentials, delivery falls back to deterministic,
diff-friendly JSON.

## Data sources policy

- **Fixtures** under `fixtures/` are hand-authored, synthetic, fictional
  products — **no third-party copyright/ToS issues** (see `fixtures/README.md`).
- The **live source** path is **off by default**, gated behind
  `LIVE_SOURCE_ENABLED`, checks `robots.txt`, sets a descriptive User-Agent, and
  rate-limits. CI never hits the network; a static snapshot is committed for
  tests.

## Project layout

```
src/llm_extract/
  cli.py            Typer CLI: extract | verify | deliver | run
  config.py         env-driven Settings (mock-vs-real, json-vs-sheets)
  schemas.py        pydantic data contract
  prompts.py        versioned prompts + output schema
  chain.py          LangChain-style pipeline
  normalize.py      deterministic cleaning
  consistency.py    cross-source controls
  verify.py         verification gate
  report.py         markdown + rich reports
  llm/              base protocol, openrouter, mock
  ingest/           fixtures, live_source, preprocess
  delivery/         json_sink, sheets
fixtures/           synthetic messy HTML + expected JSON
docs/               architecture, data_contract, formatting_spec
tests/              offline suite (mocked LLM/httpx/gspread)
```

## Development

```bash
make install     # editable install + pre-commit hooks
make lint        # ruff check
make format      # ruff format
make typecheck   # mypy
make test        # pytest
make cov         # pytest with coverage
```

`.pre-commit-config.yaml` wires ruff + format + hygiene hooks.

## Docker

```bash
docker build -t llm-extract .
docker run --rm llm-extract            # runs `run --dry-run` with bundled fixtures
```

## Configuration reference

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | — | Enables the real OpenRouter client. |
| `OPENROUTER_MODEL` | `openai/gpt-4o-mini` | Model id. |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | API base. |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | — | Path or inline JSON for Sheets auth. |
| `GSHEET_ID` | — | Target spreadsheet id. |
| `LIVE_SOURCE_ENABLED` | `false` | Opt-in for live fetching. |
| `LIVE_SOURCE_URL` | — | Sanctioned source URL. |
| `PRICE_TOLERANCE_PCT` | `5.0` | Cross-source price tolerance. |

## Limitations, risks & responsible use

- LLM output is non-deterministic; we mitigate with a strict output schema,
  temperature 0, JSON repair, pydantic as a hard gate, and tenacity retries.
- The verification gate's thresholds are explicit and unit-tested to avoid both
  over-lenient (ships bad data) and over-strict (blocks everything) failures.
- Only scrape sources you are permitted to: the live path is opt-in, robots-aware
  and rate-limited. Never commit secrets — all credentials come from env vars.
- Scraped HTML is reduced to bounded text before reaching the model to limit
  prompt-injection, and **all** model output is validated against the schema.

## License

MIT — see [LICENSE](LICENSE).
