"""Per-branch monthly metric scoring, dimension-agnostic (ALG-40).

For each branch and each month 0..horizon, produce a MetricPoint whose `scores`
map carries a 0-100 value for EVERY generated dimension id. The baseline is
deterministic, derived from the events up to that month + persona traits + option
semantics. Every MetricPoint references at least one supporting event id: the
events in/before that month for that branch, falling back to the earliest known
branch event so the list is never empty (ALG-40).

Dimensions are dynamic per decision. Known ids (the original five) keep their
hand-tuned keyword effects; unknown dims get a neutral baseline plus a small
event-driven drift oriented by the dimension's polarity (skeleton events nudge a
higher_is_better dim up and a lower_is_better dim down, and vice versa).
"""
from __future__ import annotations

import random
from typing import Dict, List

from ..contracts import DEFAULT_DIMENSIONS, Dimension, MetricPoint, Persona, TimelineEvent
from .common import clamp, horizon_for_mode

# Keyword -> per-dimension nudges, keyed by the canonical dimension ids. Crude
# but deterministic option-semantics signal. Only applied to dims whose id is
# present in the generated set (others are handled generically below).
_KEYWORD_EFFECTS: Dict[str, Dict[str, float]] = {
    "quit": {"economic": -6, "autonomy": +6, "mental": +2, "career": -3},
    "leave": {"economic": -4, "autonomy": +5, "relationship": -2},
    "stay": {"economic": +3, "autonomy": -3, "mental": -1, "career": +2},
    "move": {"relationship": -4, "autonomy": +4, "mental": -2},
    "job": {"career": +5, "economic": +4},
    "startup": {"economic": -7, "autonomy": +7, "career": +4, "mental": -3},
    "study": {"career": +5, "economic": -4, "autonomy": +1},
    "school": {"career": +5, "economic": -4},
    "marry": {"relationship": +7, "autonomy": -3, "mental": +2},
    "breakup": {"relationship": -8, "autonomy": +5, "mental": -4},
    "save": {"economic": +6, "autonomy": -1},
    "invest": {"economic": +3, "mental": -1},
    "travel": {"mental": +5, "economic": -4, "autonomy": +4},
    "relocate": {"relationship": -5, "autonomy": +4, "career": +3},
}

_DEFAULT_IDS = {d.id for d in DEFAULT_DIMENSIONS}


def _option_bias(option_text: str, dim_ids: List[str]) -> Dict[str, float]:
    """Aggregate per-dimension bias from keywords in the option text.

    Effects are recorded only for dimension ids present in the generated set.
    """
    bias = {d: 0.0 for d in dim_ids}
    low = (option_text or "").lower()
    for kw, effects in _KEYWORD_EFFECTS.items():
        if kw in low:
            for dim, delta in effects.items():
                if dim in bias:
                    bias[dim] += delta
    return bias


def _persona_baseline(personas: List[Persona], dims: List[Dimension]) -> Dict[str, float]:
    """Trait-derived baseline offsets (user-centric, mild)."""
    base = {d.id: 0.0 for d in dims}
    if not personas:
        return base
    user = personas[0]
    b5 = user.big5
    # Known dims get their tuned offset; unknown dims get a small openness/
    # conscientiousness blend so the curve is not flat.
    known = {
        "economic": (user.risk_tolerance - 5.0) * 0.8,
        "career": (b5.C - 5.0) * 1.2,
        "relationship": (b5.A - 5.0) * 1.2,
        "mental": (5.0 - b5.N) * 1.4,
        "autonomy": (b5.O - 5.0) * 1.0,
    }
    generic = (b5.O + b5.C - 10.0) * 0.5
    for d in dims:
        base[d.id] = known.get(d.id, generic)
    return base


def _event_month_effects(
    events: List[TimelineEvent], option_bias: Dict[str, float], dims: List[Dimension]
) -> Dict[int, Dict[str, float]]:
    """Per-month incremental effect contributed by each event.

    Skeleton events carry the strongest signal, perturbations less, exogenous a
    small shared nudge. For dimensions without a tuned keyword effect, the
    event drift is oriented by the dimension polarity.
    """
    weight_by_kind = {"skeleton": 1.0, "perturbation": 0.5, "exogenous": 0.3}
    polarity = {d.id: d.polarity for d in dims}
    dim_ids = [d.id for d in dims]
    # Magnitude of the decision's overall "push" (used to drive unknown dims).
    push = sum(abs(v) for v in option_bias.values()) or 1.0

    per_month: Dict[int, Dict[str, float]] = {}
    for ev in events:
        w = weight_by_kind.get(ev.kind, 0.5)
        slot = per_month.setdefault(ev.month, {d: 0.0 for d in dim_ids})
        if ev.kind == "exogenous":
            # Exogenous backbone is a mild, mostly-negative drag, identical-ish
            # in both branches (it does not encode the option bias). Orient by
            # polarity so a lower_is_better dim is dragged the right way.
            for d in dims:
                drag = -1.0 * w if d.polarity == "higher_is_better" else +1.0 * w
                # Only the canonical economic/mental dims carried the original
                # explicit drag; keep that intensity, smaller for others.
                slot[d.id] += drag * (1.0 if d.id in ("economic", "mental") else 0.4)
        else:
            for d in dims:
                if d.id in _DEFAULT_IDS and d.id in option_bias:
                    slot[d.id] += option_bias[d.id] * 0.12 * w
                else:
                    # Unknown dim: small drift in the option's overall direction,
                    # oriented by polarity (skeleton => toward "better").
                    direction = 1.0 if polarity.get(d.id) == "higher_is_better" else -1.0
                    slot[d.id] += direction * (push * 0.02) * w
    return per_month


def score_branch(
    branch: str,
    option_text: str,
    personas: List[Persona],
    events: List[TimelineEvent],
    seed: int,
    mode: str,
    dimensions: List[Dimension],
) -> List[MetricPoint]:
    """Produce MetricPoints (scores keyed by every dim id) for one branch (ALG-40)."""
    horizon = horizon_for_mode(mode)
    rng = random.Random("score:%d:%s" % (seed, branch))

    dims = list(dimensions) if dimensions else [d.model_copy() for d in DEFAULT_DIMENSIONS]
    dim_ids = [d.id for d in dims]

    option_bias = _option_bias(option_text, dim_ids)
    base_offsets = _persona_baseline(personas, dims)
    month_effects = _event_month_effects(events, option_bias, dims)

    branch_events = [e for e in events if e.branch == branch]
    branch_events_sorted = sorted(branch_events, key=lambda e: (e.month, e.id))
    earliest_id = branch_events_sorted[0].id if branch_events_sorted else None

    # Running metric state starts near neutral 50 + persona offset.
    state = {d: clamp(50.0 + base_offsets[d]) for d in dim_ids}

    points: List[MetricPoint] = []
    for month in range(0, horizon + 1):
        if month in month_effects:
            for d in dim_ids:
                state[d] = clamp(state[d] + month_effects[month][d])
        # Small deterministic monthly drift so curves are not flat.
        for d in dim_ids:
            state[d] = clamp(state[d] + rng.uniform(-0.8, 0.8))

        # Supporting events: everything in/before this month for this branch.
        supporting = [e.id for e in branch_events_sorted if e.month <= month]
        if not supporting:
            # ALG-40: never empty. Fall back to earliest branch event.
            if earliest_id is not None:
                supporting = [earliest_id]
            else:
                supporting = ["%s_seed" % branch]

        points.append(
            MetricPoint(
                branch=branch,
                month=month,
                scores={d: round(state[d], 1) for d in dim_ids},
                supporting_event_ids=supporting,
            )
        )
    return points
