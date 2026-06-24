"""Runnable example: full pipeline end-to-end with the mock LLM, no keys needed.

    python examples/run_pipeline.py

Prints a verification report and writes deterministic JSON to ``out/``.
"""

from __future__ import annotations

from pathlib import Path

from llm_extract.chain import ExtractionChain
from llm_extract.consistency import check_consistency
from llm_extract.delivery.json_sink import write_json
from llm_extract.ingest.fixtures import load_fixtures
from llm_extract.llm.mock import MockLLMClient
from llm_extract.report import print_console, render_markdown
from llm_extract.verify import verify


def main() -> None:
    chain = ExtractionChain(llm=MockLLMClient())
    snippets = list(load_fixtures())
    result, errors = chain.run_with_errors(snippets)

    cons = check_consistency(result)
    report = verify(result, extraction_errors=errors, consistency=cons)

    print_console(report)

    out_dir = Path("out")
    write_json(result, out_dir / "delivery.json")
    (out_dir / "report.md").write_text(render_markdown(report), encoding="utf-8")
    print(f"\nWrote {out_dir/'delivery.json'} and {out_dir/'report.md'}")


if __name__ == "__main__":
    main()
