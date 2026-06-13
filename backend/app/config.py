"""Claude client + environment loading (PROVIDED — do not reinvent secret handling).

- Reads CLAUDE_API_KEY and DEFAULT_MODEL from the repo-root .env.
- NEVER prints, logs, or returns the API key.
- `complete()` is a resilient text-completion helper: it retries with backoff and
  returns None on failure so callers can fall back to a deterministic stub. Tests
  and the demo therefore never hard-crash, with or without a live key.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger("lynsea.config")

# backend/app/config.py -> parents[2] == repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_PATH = REPO_ROOT / ".env"


def _load_env() -> None:
    """Load repo-root .env without overriding already-set process env vars."""
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(_ENV_PATH, override=False)
        return
    except Exception:
        pass
    # Minimal fallback parser if python-dotenv is unavailable.
    try:
        if _ENV_PATH.exists():
            for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                os.environ.setdefault(key, val)
    except Exception:
        logger.warning("Could not read .env file")


_load_env()

CLAUDE_API_KEY: str = (os.environ.get("CLAUDE_API_KEY") or "").strip()
DEFAULT_MODEL: str = (os.environ.get("DEFAULT_MODEL") or "").strip() or "claude-haiku-4-5-20251001"
LLM_AVAILABLE: bool = bool(CLAUDE_API_KEY)

_client: Any = None
_client_init_failed = False


def get_client() -> Any:
    """Return a cached Anthropic client, or None if no key / SDK unavailable."""
    global _client, _client_init_failed
    if _client is not None:
        return _client
    if _client_init_failed or not CLAUDE_API_KEY:
        return None
    try:
        from anthropic import Anthropic  # type: ignore

        _client = Anthropic(api_key=CLAUDE_API_KEY)
        return _client
    except Exception as exc:  # SDK missing or init error — degrade gracefully.
        _client_init_failed = True
        logger.warning("Anthropic client unavailable (%s); using stub fallback.", type(exc).__name__)
        return None


def complete(
    prompt: str,
    *,
    system: str = "",
    model: Optional[str] = None,
    max_tokens: int = 1500,
    temperature: float = 0.7,
    retries: int = 2,
) -> Optional[str]:
    """Call Claude and return the text output, or None on failure.

    Never raises and never logs the API key. Callers should treat None as
    "LLM unavailable" and fall back to a deterministic generator.
    """
    client = get_client()
    if client is None:
        return None
    model = model or DEFAULT_MODEL
    backoff = 0.5
    last_err_name = "unknown"
    for attempt in range(retries + 1):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system or None,
                messages=[{"role": "user", "content": prompt}],
            )
            parts: List[str] = []
            for block in getattr(resp, "content", []) or []:
                if getattr(block, "type", None) == "text":
                    parts.append(block.text)
            text = "".join(parts).strip()
            return text or None
        except Exception as exc:  # network/limit/etc — retry then give up.
            last_err_name = type(exc).__name__
            if attempt < retries:
                time.sleep(backoff)
                backoff *= 2
    logger.warning("Claude call failed after %d retries (%s).", retries, last_err_name)
    return None


def extract_json(text: Optional[str]) -> Optional[Any]:
    """Best-effort JSON extraction from an LLM response (handles ``` fences)."""
    if not text:
        return None
    cleaned = text.strip()
    # Strip markdown code fences if present.
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    # Fallback: grab the outermost JSON object/array.
    for opener, closer in (("{", "}"), ("[", "]")):
        start = cleaned.find(opener)
        end = cleaned.rfind(closer)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except Exception:
                continue
    return None


def complete_json(
    prompt: str,
    *,
    system: str = "",
    model: Optional[str] = None,
    max_tokens: int = 1500,
    temperature: float = 0.7,
    retries: int = 2,
) -> Optional[Any]:
    """Convenience: complete() then extract_json(). Returns None on any failure."""
    return extract_json(
        complete(
            prompt,
            system=system,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            retries=retries,
        )
    )
