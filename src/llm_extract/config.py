"""Application configuration loaded from environment variables.

The :class:`Settings` object is the single place that decides, based purely on
the *presence* of credentials, whether to use the real OpenRouter client or the
deterministic mock, and whether to deliver to Google Sheets or to JSON on disk.
This keeps every other module credential-agnostic and tests fully offline.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings sourced from the environment / ``.env`` file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- OpenRouter ---
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(default="openai/gpt-4o-mini", alias="OPENROUTER_MODEL")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL"
    )

    # --- Google Sheets ---
    google_service_account_json: str | None = Field(
        default=None, alias="GOOGLE_SERVICE_ACCOUNT_JSON"
    )
    gsheet_id: str | None = Field(default=None, alias="GSHEET_ID")

    # --- Live source ---
    live_source_enabled: bool = Field(default=False, alias="LIVE_SOURCE_ENABLED")
    live_source_url: str | None = Field(default=None, alias="LIVE_SOURCE_URL")
    live_user_agent: str = Field(
        default="llm-extract-bot/0.1 (+https://github.com/RaphaelFakhri/llm-extract)",
        alias="LIVE_USER_AGENT",
    )
    live_rate_limit_seconds: float = Field(default=2.0, alias="LIVE_RATE_LIMIT_SECONDS")

    # --- Consistency tolerances ---
    price_tolerance_pct: float = Field(default=5.0, alias="PRICE_TOLERANCE_PCT")

    @property
    def use_real_llm(self) -> bool:
        """True when an OpenRouter key is configured."""
        return bool(self.openrouter_api_key)

    @property
    def use_sheets(self) -> bool:
        """True when both Google Sheets credentials and a target id are present."""
        return bool(self.google_service_account_json and self.gsheet_id)


def get_settings(**overrides: object) -> Settings:
    """Construct :class:`Settings`, allowing explicit overrides (used in tests)."""
    return Settings(**overrides)  # type: ignore[arg-type]
