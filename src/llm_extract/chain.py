"""LangChain-style composable extraction chain.

The chain is a small, explicit pipeline of pure-ish functions:

    reduce_html -> render_messages -> llm.complete -> parse+repair JSON
    -> normalize -> pydantic validate -> ProductRecord

Each step is a callable, and :class:`ExtractionChain` composes them. Keeping the
steps as plain functions (rather than a heavyweight framework) makes the data
flow obvious and trivially unit-testable, while still being "chain-shaped".
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass

from llm_extract.ingest.preprocess import reduce_html
from llm_extract.llm.base import LLMClient
from llm_extract.normalize import normalize_record_dict
from llm_extract.prompts import render_messages
from llm_extract.schemas import (
    ExtractionResult,
    ProductRecord,
    RawSnippet,
    coerce_record,
)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)
_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


class ChainError(RuntimeError):
    """Raised when a snippet cannot be turned into a valid record."""


def parse_and_repair_json(text: str) -> dict:
    """Best-effort extraction of a single JSON object from model output.

    Handles markdown fences and leading/trailing prose, which free-form models
    sometimes add despite instructions.
    """
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fence = _JSON_FENCE_RE.search(text)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            text = fence.group(1).strip()  # parse the fenced body below

    # Decode the FIRST JSON object and ignore any trailing prose. Chatty models
    # (e.g. Grok) often emit a valid object followed by an explanation; a greedy
    # object regex would swallow that trailing text and fail with "Extra data".
    start = text.find("{")
    if start != -1:
        snippet = text[start:]
        for candidate in (snippet, re.sub(r",\s*([}\]])", r"\1", snippet)):
            try:
                obj, _end = json.JSONDecoder().raw_decode(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                return obj

    raise ChainError(f"could not parse JSON from model output: {text[:200]!r}")


@dataclass
class ExtractionChain:
    """Composable pipeline that converts a :class:`RawSnippet` into a record."""

    llm: LLMClient
    temperature: float = 0.0
    max_chars: int = 6000

    def extract_one(self, snippet: RawSnippet) -> ProductRecord:
        """Run the full chain for a single snippet."""
        content = reduce_html(snippet.html, max_chars=self.max_chars)
        messages = render_messages(
            source=snippet.source,
            record_id=snippet.record_id,
            content=content,
        )
        raw = self.llm.complete(messages, temperature=self.temperature)
        data = parse_and_repair_json(raw)
        normalized = normalize_record_dict(data)
        try:
            return coerce_record(
                normalized,
                source=snippet.source,
                record_id=snippet.record_id,
            )
        except Exception as exc:  # pydantic ValidationError, ValueError, ...
            raise ChainError(
                f"{snippet.source}/{snippet.record_id}: validation failed: {exc}"
            ) from exc

    def run(self, snippets: Iterable[RawSnippet]) -> ExtractionResult:
        """Run the chain over many snippets, collecting valid records.

        Records that fail are skipped here; the verification gate is responsible
        for the explicit pass/fail accounting. We re-raise nothing so a single
        bad page never aborts the whole batch.
        """
        records: list[ProductRecord] = []
        for snippet in snippets:
            try:
                records.append(self.extract_one(snippet))
            except ChainError:
                continue
        return ExtractionResult(records=records)

    def run_with_errors(
        self, snippets: Iterable[RawSnippet]
    ) -> tuple[ExtractionResult, list[tuple[RawSnippet, str]]]:
        """Like :meth:`run` but also returns per-snippet failures for reporting."""
        records: list[ProductRecord] = []
        errors: list[tuple[RawSnippet, str]] = []
        for snippet in snippets:
            try:
                records.append(self.extract_one(snippet))
            except ChainError as exc:
                errors.append((snippet, str(exc)))
        return ExtractionResult(records=records), errors
