"""Fetch the single, explicitly-sanctioned live source.

Defaults to *off*. When enabled it checks ``robots.txt``, sets a descriptive
User-Agent, and rate-limits. Tests mock the ``httpx.Client`` so CI never hits
the network; a static snapshot lives under ``tests/data/`` for that purpose.
"""

from __future__ import annotations

import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from llm_extract.config import Settings
from llm_extract.schemas import RawSnippet


class LiveSourceDisabledError(RuntimeError):
    """Raised when a live fetch is attempted without explicit opt-in."""


class RobotsDisallowedError(RuntimeError):
    """Raised when robots.txt forbids the configured path."""


def _robots_allows(client: httpx.Client, url: str, user_agent: str) -> bool:
    parsed = urlparse(url)
    robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
    parser = RobotFileParser()
    try:
        resp = client.get(robots_url)
        if resp.status_code >= 400:
            # No robots.txt -> default allow.
            return True
        parser.parse(resp.text.splitlines())
    except httpx.HTTPError:
        return True
    return parser.can_fetch(user_agent, url)


def fetch_live_source(
    settings: Settings,
    *,
    client: httpx.Client | None = None,
) -> RawSnippet:
    """Fetch the configured live source, honoring robots.txt and rate limits.

    Parameters mirror the rest of the codebase: an injectable ``client`` allows
    tests to provide a mock transport.
    """
    if not settings.live_source_enabled:
        raise LiveSourceDisabledError(
            "Live source fetching is disabled. Set LIVE_SOURCE_ENABLED=true and "
            "LIVE_SOURCE_URL to an explicitly sanctioned URL to enable it."
        )
    if not settings.live_source_url:
        raise LiveSourceDisabledError("LIVE_SOURCE_URL is not configured.")

    url = settings.live_source_url
    own_client = client is None
    client = client or httpx.Client(
        timeout=30.0,
        headers={"User-Agent": settings.live_user_agent},
        follow_redirects=True,
    )
    try:
        if not _robots_allows(client, url, settings.live_user_agent):
            raise RobotsDisallowedError(f"robots.txt disallows fetching {url}")

        # Polite rate limit between requests.
        time.sleep(settings.live_rate_limit_seconds)

        resp = client.get(url, headers={"User-Agent": settings.live_user_agent})
        resp.raise_for_status()
        return RawSnippet(
            source="live",
            record_id=urlparse(url).path.strip("/").replace("/", "_") or "index",
            path=url,
            html=resp.text,
        )
    finally:
        if own_client:
            client.close()
