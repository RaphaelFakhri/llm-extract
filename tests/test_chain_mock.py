from __future__ import annotations

from llm_extract.chain import ExtractionChain, parse_and_repair_json
from llm_extract.ingest.fixtures import load_fixtures


def _records_to_dicts(records):
    return {(r.source, r.record_id): r.model_dump() for r in records}


def test_chain_reproduces_expected(fixtures_root, mock_llm, expected_records):
    chain = ExtractionChain(llm=mock_llm)
    snippets = list(load_fixtures(root=fixtures_root))
    result, errors = chain.run_with_errors(snippets)

    assert errors == []
    got = _records_to_dicts(result.records)

    for src, recs in expected_records.items():
        for exp in recs:
            key = (src, exp["record_id"])
            assert key in got, f"missing {key}"
            assert got[key] == exp


def test_chain_skips_unparseable(monkeypatch, fixtures_root):
    class BadLLM:
        def complete(self, messages, *, temperature=0.0):
            return "not json at all"

    chain = ExtractionChain(llm=BadLLM())
    snippets = list(load_fixtures("source_a", root=fixtures_root))
    result, errors = chain.run_with_errors(snippets)
    assert result.records == []
    assert len(errors) == len(snippets)


def test_parse_and_repair_handles_fences_and_prose():
    assert parse_and_repair_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_and_repair_json('Here you go: {"a": 1} thanks') == {"a": 1}
    assert parse_and_repair_json('{"a": 1,}') == {"a": 1}
