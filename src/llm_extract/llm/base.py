"""The LLM client seam.

Both the real OpenRouter client and the deterministic mock satisfy this
protocol, which is what makes the whole pipeline testable offline.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Minimal chat-completion interface used by the chain."""

    def complete(self, messages: list[dict[str, str]], *, temperature: float = 0.0) -> str:
        """Return the assistant message content for the given chat messages."""
        ...
