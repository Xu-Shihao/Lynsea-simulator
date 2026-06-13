"""Claude API client wrapper — the single choke point for all model calls.

`BE-11`: every LLM call in the system goes through this module, and the provider
is resolved from ``.env`` only (via :mod:`app.config`). There is no hardcoded
provider that isn't configured there.

`BE-12`: a single call failure is retried with exponential backoff; persistent
failure (or a missing API key) **degrades to a readable fallback string** rather
than crashing the whole simulation chain.

Uses the official ``anthropic`` async SDK. Tiering:
high-quality narrative/causal -> ``"opus"`` / ``"sonnet"``;
high-frequency state/scoring  -> ``"haiku"`` (the ``.env`` default).
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Optional

import anthropic

from app.config import Settings, Tier, get_settings

logger = logging.getLogger("lynsea.llm")

Message = dict[str, object]  # {"role": "user"|"assistant", "content": str|list}

# Returned when a call cannot be completed (no key, or persistent failure) and
# the caller did not supply its own fallback. Kept short + probabilistic-safe.
DEGRADED_DEFAULT = (
    "[model unavailable — returning a degraded placeholder; "
    "treat this run's narrative text as low-confidence]"
)


class LLMClient:
    """Thin async wrapper around ``anthropic.AsyncAnthropic``.

    The underlying SDK is created lazily so importing this module (and booting
    the app) never requires a key — calls degrade gracefully when it is absent.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._client: Optional[anthropic.AsyncAnthropic] = None

    @property
    def settings(self) -> Settings:
        return self._settings

    def _get_client(self) -> Optional[anthropic.AsyncAnthropic]:
        if not self._settings.has_api_key:
            return None
        if self._client is None:
            # SDK retries 429/5xx itself; we add an outer backoff loop for
            # BE-12 visibility + graceful degrade, and keep max_retries modest.
            self._client = anthropic.AsyncAnthropic(
                api_key=self._settings.claude_api_key,
                max_retries=2,
            )
        return self._client

    async def call(
        self,
        messages: list[Message],
        tier: Tier = "haiku",
        *,
        system: Optional[str] = None,
        max_tokens: int = 1024,
        fallback: Optional[str] = None,
        max_retries: int = 3,
        base_delay: float = 0.75,
    ) -> str:
        """Call Claude and return the concatenated text response.

        Never raises on model failure: on a missing key or persistent error it
        logs and returns ``fallback`` (or :data:`DEGRADED_DEFAULT`) so the
        orchestration chain degrades instead of crashing (`BE-12`).
        """
        degraded = fallback if fallback is not None else DEGRADED_DEFAULT

        client = self._get_client()
        if client is None:
            logger.warning("CLAUDE_API_KEY not set; degrading LLM call (tier=%s).", tier)
            return degraded

        model = self._settings.model_for_tier(tier)
        kwargs: dict[str, object] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        last_exc: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                resp = await client.messages.create(**kwargs)  # type: ignore[arg-type]
                return _extract_text(resp)
            except (
                anthropic.RateLimitError,
                anthropic.APITimeoutError,
                anthropic.APIConnectionError,
                anthropic.InternalServerError,
            ) as exc:
                # Transient — back off and retry.
                last_exc = exc
                delay = min(base_delay * (2**attempt) + random.uniform(0, 0.25), 20.0)
                logger.warning(
                    "LLM transient error (%s), retry %d/%d in %.1fs",
                    type(exc).__name__,
                    attempt + 1,
                    max_retries,
                    delay,
                )
                await asyncio.sleep(delay)
            except anthropic.APIStatusError as exc:
                if exc.status_code >= 500:
                    last_exc = exc
                    delay = min(base_delay * (2**attempt) + random.uniform(0, 0.25), 20.0)
                    logger.warning(
                        "LLM 5xx (%s), retry %d/%d in %.1fs",
                        exc.status_code,
                        attempt + 1,
                        max_retries,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    # 4xx: not retryable — degrade.
                    logger.error("LLM client error %s: %s", exc.status_code, exc)
                    return degraded
            except Exception as exc:  # pragma: no cover - defensive catch-all
                logger.exception("Unexpected LLM error: %s", exc)
                return degraded

        logger.error(
            "LLM call failed after %d retries (tier=%s); degrading. last=%s",
            max_retries,
            tier,
            last_exc,
        )
        return degraded

    async def complete(
        self,
        prompt: str,
        tier: Tier = "haiku",
        *,
        system: Optional[str] = None,
        max_tokens: int = 1024,
        fallback: Optional[str] = None,
    ) -> str:
        """Convenience wrapper for a single-user-turn prompt."""
        return await self.call(
            [{"role": "user", "content": prompt}],
            tier=tier,
            system=system,
            max_tokens=max_tokens,
            fallback=fallback,
        )


def _extract_text(resp: object) -> str:
    """Join all text blocks of an anthropic ``Message`` response."""
    content = getattr(resp, "content", None) or []
    parts: list[str] = []
    for block in content:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", ""))
    return "".join(parts).strip()


# Module-level singleton — import and use ``llm`` everywhere.
llm = LLMClient()
