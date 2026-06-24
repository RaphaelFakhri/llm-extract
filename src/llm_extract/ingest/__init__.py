"""Ingestion: turn source HTML into :class:`RawSnippet` objects."""

from __future__ import annotations

from llm_extract.ingest.fixtures import discover_sources, load_fixtures
from llm_extract.ingest.preprocess import reduce_html

__all__ = ["discover_sources", "load_fixtures", "reduce_html"]
