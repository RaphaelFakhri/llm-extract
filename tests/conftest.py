"""Shared pytest fixtures. Guarantees zero real network/LLM/Sheets calls."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from llm_extract.ingest.fixtures import load_fixtures
from llm_extract.llm.mock import MockLLMClient

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_ROOT = REPO_ROOT / "fixtures"


@pytest.fixture
def fixtures_root() -> Path:
    return FIXTURES_ROOT


@pytest.fixture
def mock_llm() -> MockLLMClient:
    return MockLLMClient()


@pytest.fixture
def all_snippets():
    return list(load_fixtures(root=FIXTURES_ROOT))


@pytest.fixture
def expected_records() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for src in ("source_a", "source_b"):
        data = json.loads((FIXTURES_ROOT / "expected" / f"{src}.json").read_text())
        out[src] = data["records"]
    return out


class FakeWorksheet:
    """In-memory stand-in for a gspread worksheet."""

    def __init__(self) -> None:
        self.values: list[list[Any]] = []
        self.cleared = False

    def clear(self) -> None:
        self.cleared = True
        self.values = []

    def update(self, values: list[list[Any]], range_name: str | None = None) -> None:
        self.values = values


class FakeSpreadsheet:
    def __init__(self, worksheet: FakeWorksheet) -> None:
        self._ws = worksheet

    def get_worksheet(self, index: int) -> FakeWorksheet:
        return self._ws


class FakeGspreadClient:
    """Injectable fake matching the SheetsClient protocol surface."""

    def __init__(self) -> None:
        self.worksheet = FakeWorksheet()
        self._spreadsheet = FakeSpreadsheet(self.worksheet)
        self.opened_key: str | None = None

    def open_by_key(self, key: str) -> FakeSpreadsheet:
        self.opened_key = key
        return self._spreadsheet


@pytest.fixture
def fake_gspread_client() -> FakeGspreadClient:
    return FakeGspreadClient()
