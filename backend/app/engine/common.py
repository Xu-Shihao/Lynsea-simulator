"""Shared helpers for the Lynsea engine: deterministic seeding, slugs, horizons."""
from __future__ import annotations

import hashlib
import re
from typing import Dict

# Horizon (months) by simulation mode. Quick mode is the demo default.
HORIZON_BY_MODE: Dict[str, int] = {
    "quick": 6,
    "medium": 18,
    "heavy": 24,
}


def horizon_for_mode(mode: str) -> int:
    """Return the simulation horizon (in months) for a given mode."""
    return HORIZON_BY_MODE.get((mode or "quick").lower(), HORIZON_BY_MODE["quick"])


def stable_seed(decision: str, seed: object = None) -> int:
    """Derive a deterministic integer seed.

    If an explicit seed is provided use it; otherwise hash the decision text
    (first 4 bytes of sha256). Same decision => same seed (NFR-01).
    """
    if seed is not None:
        try:
            return int(seed)
        except (TypeError, ValueError):
            pass
    digest = hashlib.sha256((decision or "").encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


_slug_re = re.compile(r"[^a-z0-9]+")


def slugify(text: str, fallback: str = "x") -> str:
    """Lowercase, ASCII, hyphen-free slug suitable for stable persona ids."""
    s = _slug_re.sub("_", (text or "").strip().lower()).strip("_")
    return s or fallback


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp a number into [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value
