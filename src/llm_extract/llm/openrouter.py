"""Real OpenRouter chat-completions client.

Only instantiated when ``OPENROUTER_API_KEY`` is present. Network calls are
guarded with tenacity retry/backoff and run at temperature 0 for determinism.
In tests the underlying ``httpx.Client`` is mocked, so no network is touched.
"""

from __future__ import annotations

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class OpenRouterError(RuntimeError):
    """Raised when OpenRouter returns an unusable response."""


class OpenRouterClient:
    """Thin client over the OpenRouter ``/chat/completions`` endpoint."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OpenRouterClient requires a non-empty api_key")
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                # Optional attribution headers recommended by OpenRouter.
                "HTTP-Referer": "https://github.com/RaphaelFakhri/llm-extract",
                "X-Title": "llm-extract",
            },
        )

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def complete(self, messages: list[dict[str, str]], *, temperature: float = 0.0) -> str:
        """Send a chat completion request and return the message content."""
        resp = self._client.post(
            f"{self._base_url}/chat/completions",
            json={
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
                "response_format": {"type": "json_object"},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:  # pragma: no cover - defensive
            raise OpenRouterError(f"unexpected OpenRouter response: {data!r}") from exc

    def close(self) -> None:
        self._client.close()
