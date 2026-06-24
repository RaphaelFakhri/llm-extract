"""Load committed, synthetic, deliberately-messy HTML fixtures.

Fixtures live under ``fixtures/<source>/<record>.html``. Each file becomes a
:class:`RawSnippet` carrying provenance so every downstream record is traceable
back to its origin file.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from llm_extract.schemas import RawSnippet


def _fixtures_root(root: str | os.PathLike[str] | None = None) -> Path:
    """Resolve the fixtures directory.

    Search order: explicit arg, ``LLM_EXTRACT_FIXTURES`` env var, then the
    repo-relative ``fixtures/`` directory (works for editable installs and the
    Docker image where fixtures are copied alongside the package).
    """
    if root is not None:
        return Path(root)
    env = os.environ.get("LLM_EXTRACT_FIXTURES")
    if env:
        return Path(env)
    # repo layout: <repo>/src/llm_extract/ingest/fixtures.py -> <repo>/fixtures
    repo_root = Path(__file__).resolve().parents[3]
    candidate = repo_root / "fixtures"
    if candidate.is_dir():
        return candidate
    # Docker layout: /app/fixtures next to the installed package.
    return Path.cwd() / "fixtures"


def discover_sources(root: str | os.PathLike[str] | None = None) -> list[str]:
    """Return the sorted list of source ids that contain HTML fixtures."""
    base = _fixtures_root(root)
    if not base.is_dir():
        return []
    sources = [
        d.name
        for d in base.iterdir()
        if d.is_dir() and d.name not in {"expected"} and any(d.glob("*.html"))
    ]
    return sorted(sources)


def load_fixtures(
    source: str | None = None,
    root: str | os.PathLike[str] | None = None,
) -> Iterator[RawSnippet]:
    """Yield :class:`RawSnippet` for one source, or all sources if ``source`` is None."""
    base = _fixtures_root(root)
    sources = [source] if source else discover_sources(root)
    for src in sources:
        src_dir = base / src
        for html_path in sorted(src_dir.glob("*.html")):
            yield RawSnippet(
                source=src,
                record_id=html_path.stem,
                path=str(html_path),
                html=html_path.read_text(encoding="utf-8"),
            )
