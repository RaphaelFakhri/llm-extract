"""LLM client implementations behind a common protocol."""

from __future__ import annotations

from llm_extract.llm.base import LLMClient
from llm_extract.llm.mock import MockLLMClient

__all__ = ["LLMClient", "MockLLMClient", "build_client"]


def build_client(settings: object | None = None) -> LLMClient:
    """Return the real OpenRouter client if a key is set, else the mock.

    Imported lazily so that ``httpx`` and credentials are only touched when a
    real client is actually requested.
    """
    from llm_extract.config import Settings, get_settings

    cfg: Settings = settings if isinstance(settings, Settings) else get_settings()
    if cfg.use_real_llm:
        from llm_extract.llm.openrouter import OpenRouterClient

        return OpenRouterClient(
            api_key=cfg.openrouter_api_key or "",
            model=cfg.openrouter_model,
            base_url=cfg.openrouter_base_url,
        )
    return MockLLMClient()
