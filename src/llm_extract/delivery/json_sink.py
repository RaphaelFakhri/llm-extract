"""Deterministic JSON delivery.

Writes the validated :class:`ExtractionResult` to disk as sorted, indented JSON
so diffs are stable across runs. This is also the offline fallback when Google
Sheets credentials are not configured.
"""

from __future__ import annotations

import json
from pathlib import Path

from llm_extract.schemas import ExtractionResult


def serialize(result: ExtractionResult) -> str:
    """Serialize an :class:`ExtractionResult` to deterministic JSON text."""
    records = sorted(
        (r.model_dump() for r in result.records),
        key=lambda d: (d["source"], d["record_id"]),
    )
    return json.dumps({"records": records}, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_json(result: ExtractionResult, path: str | Path) -> Path:
    """Write ``result`` to ``path`` as deterministic JSON and return the path."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(serialize(result), encoding="utf-8")
    return out
