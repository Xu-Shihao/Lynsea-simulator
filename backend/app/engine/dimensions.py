"""Per-decision dimension generation (Phase 2).

`generate_dimensions(decision, seed)` produces 4-8 decision-specific outcome
dimensions via a strict-JSON LLM call, with a deterministic fallback to the
canonical DEFAULT_DIMENSIONS whenever the LLM is unavailable or returns an
invalid payload. Generated ONCE per simulation by the orchestrator and shared by
both branches, which keeps the paired counterfactual comparable (M-c).

The LLM is reached only through `config.complete_json` so tests on the stub path
(no key) deterministically get DEFAULT_DIMENSIONS. `seed` affects only the stub
ordering, never the LLM call.
"""
from __future__ import annotations

from typing import Any, List, Optional

from .. import config
from ..contracts import DEFAULT_DIMENSIONS, Dimension
from .common import slugify

_MIN_DIMS = 4
_MAX_DIMS = 8

_DIM_SYSTEM = (
    "You design decision-analysis dimensions. Given a personal decision, propose "
    "the 4-8 outcome axes that matter most for comparing the options. Output "
    "STRICT JSON only, no prose."
)


def _default_dimensions() -> List[Dimension]:
    """A fresh copy of the canonical fallback set (deterministic)."""
    return [d.model_copy() for d in DEFAULT_DIMENSIONS]


def _coerce_polarity(value: Any) -> str:
    if value in ("higher_is_better", "lower_is_better"):
        return value
    return "higher_is_better"


def _validate(raw: Any) -> Optional[List[Dimension]]:
    """Validate an LLM payload into 4-8 unique Dimensions, or None if unusable."""
    if not isinstance(raw, list) or not raw:
        return None
    seen: set = set()
    dims: List[Dimension] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("id") or "").strip()
        raw_id = str(item.get("id") or label).strip()
        if not raw_id and not label:
            continue
        did = slugify(raw_id or label)
        if not did or did in seen:
            continue
        seen.add(did)
        dims.append(
            Dimension(
                id=did,
                label=label or did.replace("_", " ").title(),
                description=str(item.get("description") or "").strip(),
                polarity=_coerce_polarity(item.get("polarity")),
            )
        )
        if len(dims) >= _MAX_DIMS:
            break
    if len(dims) < _MIN_DIMS:
        return None
    return dims


def generate_dimensions(decision: str, seed: int) -> List[Dimension]:
    """Return 4-8 decision-specific dimensions (LLM with deterministic fallback).

    Generated once per simulation and shared by both branches.
    """
    prompt = (
        "Decision: %s\n\n"
        "Propose 4 to 8 distinct outcome dimensions for evaluating this decision. "
        "Return STRICT JSON: a list of objects "
        '{"id":short_snake_case,"label":string,"description":short string,'
        '"polarity":"higher_is_better|lower_is_better"}. '
        "Use lower_is_better for axes where less is better (e.g. stress, risk). "
        "JSON list only." % (decision or "")
    )
    raw: Optional[Any] = None
    try:
        raw = config.complete_json(prompt, system=_DIM_SYSTEM, max_tokens=600, temperature=0.4)
    except Exception:
        raw = None

    dims = _validate(raw)
    if dims is None:
        return _default_dimensions()
    return dims
