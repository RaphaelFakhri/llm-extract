"""Live-source tests with a fully mocked httpx transport (no real network)."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from llm_extract.config import Settings
from llm_extract.ingest.live_source import (
    LiveSourceDisabledError,
    RobotsDisallowedError,
    fetch_live_source,
)

SNAPSHOT = (Path(__file__).parent / "data" / "live_source_snapshot.html").read_text()


def _mock_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_disabled_by_default():
    settings = Settings(LIVE_SOURCE_ENABLED=False, LIVE_SOURCE_URL="https://example.com/p")
    with pytest.raises(LiveSourceDisabledError):
        fetch_live_source(settings, client=_mock_client(lambda r: httpx.Response(200)))


def test_fetch_respects_robots(monkeypatch):
    settings = Settings(
        LIVE_SOURCE_ENABLED=True,
        LIVE_SOURCE_URL="https://example.com/product",
        LIVE_RATE_LIMIT_SECONDS=0,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /product\n")
        return httpx.Response(200, text=SNAPSHOT)

    with pytest.raises(RobotsDisallowedError):
        fetch_live_source(settings, client=_mock_client(handler))


def test_fetch_success(monkeypatch):
    settings = Settings(
        LIVE_SOURCE_ENABLED=True,
        LIVE_SOURCE_URL="https://example.com/product",
        LIVE_RATE_LIMIT_SECONDS=0,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, text=SNAPSHOT)

    snippet = fetch_live_source(settings, client=_mock_client(handler))
    assert snippet.source == "live"
    assert "Helios Solar Charger" in snippet.html
