"""Configuration: loads ``.env`` and exposes typed settings + model-tier map.

`BE-11` requires that every LLM call resolves its provider/model from `.env`
only — no hardcoded provider that isn't configured here. The orchestrator and
specialists pick a *tier* (``"opus" | "sonnet" | "haiku"``); this module maps
that tier to a concrete Claude model id.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Tier = Literal["opus", "sonnet", "haiku"]


class Settings(BaseSettings):
    """App settings, populated from environment / ``backend/.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- LLM access (BE-11) -------------------------------------------------
    claude_api_key: str = ""
    # High-frequency state/scoring default tier -> Haiku (per BUILD_PLAN §2).
    default_model: str = "claude-haiku-4-5"
    # Per-tier overrides. The "haiku" tier resolves to ``default_model`` so the
    # .env DEFAULT_MODEL stays the single source of truth for the cheap tier.
    opus_model: str = "claude-opus-4-8"
    sonnet_model: str = "claude-sonnet-4-6"

    # --- HTTP ---------------------------------------------------------------
    frontend_origin: str = "http://localhost:3000"

    # --- App metadata -------------------------------------------------------
    app_version: str = "0.1.0"

    def model_for_tier(self, tier: Tier) -> str:
        """Map a capability tier to a concrete Claude model id.

        high-quality narrative/causal -> Opus/Sonnet;
        high-frequency state/scoring  -> Haiku (the .env default).
        """
        mapping: dict[str, str] = {
            "opus": self.opus_model,
            "sonnet": self.sonnet_model,
            "haiku": self.default_model,
        }
        return mapping.get(tier, self.default_model)

    @property
    def has_api_key(self) -> bool:
        return bool(self.claude_api_key and self.claude_api_key.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
