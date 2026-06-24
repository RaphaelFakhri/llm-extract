from __future__ import annotations

from llm_extract.ingest.fixtures import discover_sources, load_fixtures
from llm_extract.schemas import RawSnippet


def test_discover_sources(fixtures_root):
    sources = discover_sources(root=fixtures_root)
    assert sources == ["source_a", "source_b"]


def test_load_fixtures_all(fixtures_root):
    snippets = list(load_fixtures(root=fixtures_root))
    assert len(snippets) == 6
    assert all(isinstance(s, RawSnippet) for s in snippets)
    assert all(s.html.strip() for s in snippets)


def test_load_fixtures_single_source_has_provenance(fixtures_root):
    snippets = list(load_fixtures("source_a", root=fixtures_root))
    assert {s.record_id for s in snippets} == {
        "product_001",
        "product_002_missing_price",
        "product_003_nested_specs",
    }
    for s in snippets:
        assert s.source == "source_a"
        assert s.path.endswith(".html")
