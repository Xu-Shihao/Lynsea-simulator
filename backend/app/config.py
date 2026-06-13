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
import threading
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

# Per-request timeout (seconds). Bounded so a stalled call can never hang the
# pipeline — it errors out and callers fall back to the deterministic stub.
REQUEST_TIMEOUT: float = float(os.environ.get("LYNSEA_LLM_TIMEOUT") or 45.0)
# Bounded SDK-level retries. Set to 0 so the SDK does NOT add its own
# (0.5s + 1s + 2s ...) backoff on top of complete()'s retry — that stacking was
# the worst-case latency amplifier (BE-04). complete() owns the single retry.
_MAX_RETRIES: int = 0
# Cap on exponential backoff so 2^n can never run away (BE-04).
_BACKOFF_CAP: float = 10.0

# --- Per-phase timeout budgets (seconds) ---------------------------------
# Each engine phase gets its own wall-clock budget. A single LLM call that
# exceeds REQUEST_TIMEOUT already aborts; these budgets let callers bound a
# *phase* (which may issue several calls) and fall back to the deterministic
# stub the moment the budget is blown, rather than accumulating retries.
PERSONA_TIMEOUT: float = float(os.environ.get("LYNSEA_PERSONA_TIMEOUT") or 25.0)
BACKBONE_TIMEOUT: float = float(os.environ.get("LYNSEA_BACKBONE_TIMEOUT") or 5.0)
EVENT_GEN_TIMEOUT: float = float(os.environ.get("LYNSEA_EVENT_GEN_TIMEOUT") or 30.0)
SCORING_TIMEOUT: float = float(os.environ.get("LYNSEA_SCORING_TIMEOUT") or 20.0)

# --- Whole-simulation wall-clock thresholds by mode (seconds) ------------
# These are the "complete comparable result" strong targets from the spec
# (§2: Quick <=90s, Medium <=10min, Heavy by-estimate). The orchestrator wraps
# the run in asyncio.wait_for(MODE_TIMEOUT + buffer) and, past 80% of the
# threshold, preemptively escalates remaining work to zero-retry stubs.
MODE_TIMEOUT: dict = {
    "quick": float(os.environ.get("LYNSEA_QUICK_TIMEOUT") or 90.0),
    "medium": float(os.environ.get("LYNSEA_MEDIUM_TIMEOUT") or 600.0),
    "heavy": float(os.environ.get("LYNSEA_HEAVY_TIMEOUT") or 900.0),
}


def mode_timeout(mode: str) -> float:
    """Whole-simulation wall-clock budget (seconds) for a mode."""
    return MODE_TIMEOUT.get((mode or "quick").lower(), MODE_TIMEOUT["quick"])

# IMPORTANT: the Anthropic sync client is NOT safe to share across threads here —
# concurrent use of one client from multiple worker threads corrupts requests
# (observed BadRequestError) or wedges a pooled connection. The engine runs the
# two branches concurrently via asyncio.to_thread, so we give each thread its OWN
# client via thread-local storage. This keeps branch parallelism (BE-03) safe.
_thread_local = threading.local()
_client_init_failed = False

# Process-wide "degrade to stub" switch (BE-04 / NFR-04). When set, get_client()
# returns None so every LLM-bearing call falls back to the deterministic stub.
# The orchestrator sets this to preemptively shed load once a simulation has
# burned most of its wall-clock budget, preventing uncontrolled accumulation
# under API throttle. It is cleared at the start of each run.
_force_stub = threading.Event()


def set_force_stub(on: bool) -> None:
    """Force (or release) the stub fallback for all subsequent LLM calls."""
    if on:
        _force_stub.set()
    else:
        _force_stub.clear()


def force_stub_active() -> bool:
    return _force_stub.is_set()


def get_client() -> Any:
    """Return a thread-local Anthropic client, or None if no key / SDK unavailable."""
    global _client_init_failed
    if _force_stub.is_set():
        return None
    existing = getattr(_thread_local, "client", None)
    if existing is not None:
        return existing
    if _client_init_failed or not CLAUDE_API_KEY:
        return None
    try:
        from anthropic import Anthropic  # type: ignore

        client = Anthropic(
            api_key=CLAUDE_API_KEY,
            timeout=REQUEST_TIMEOUT,
            max_retries=_MAX_RETRIES,
        )
        _thread_local.client = client
        return client
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
    retries: int = 1,
) -> Optional[str]:
    """Call Claude and return the text output, or None on failure.

    Never raises and never logs the API key. Callers should treat None as
    "LLM unavailable" and fall back to a deterministic generator.

    `retries` defaults to 1 (one extra attempt = a single ~1.5s backoff at
    most). Backoff is capped at _BACKOFF_CAP so it can never run away (BE-04).
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
                backoff = min(backoff * 2, _BACKOFF_CAP)
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
    retries: int = 1,
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
