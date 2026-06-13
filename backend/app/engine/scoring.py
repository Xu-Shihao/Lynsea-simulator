"""Per-branch monthly metric scoring (ALG-40).

For each branch and each month 0..horizon, produce a MetricPoint with all five
0-100 dimensions. The baseline is deterministic, derived from the events up to
that month + persona traits + option semantics. Every MetricPoint references at
least one supporting event id: the events in/before that month for that branch,
falling back to the earliest known branch event so the list is never empty.
"""
from __future__ import annotations

import random
from typing import Dict, List

from ..contracts import METRIC_DIMS, MetricPoint, Persona, TimelineEvent
from .common import clamp, horizon_for_mode

# Keyword -> dimension nudges. Crude but deterministic option-semantics signal.
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


def _option_bias(option_text: str) -> Dict[str, float]:
    """Aggregate per-dimension bias from keywords in the option text."""
    bias = {d: 0.0 for d in METRIC_DIMS}
    low = (option_text or "").lower()
    for kw, effects in _KEYWORD_EFFECTS.items():
        if kw in low:
            for dim, delta in effects.items():
                bias[dim] += delta
    return bias


def _persona_baseline(personas: List[Persona]) -> Dict[str, float]:
    """Trait-derived baseline offsets (user-centric, mild)."""
    if not personas:
        return {d: 0.0 for d in METRIC_DIMS}
    user = personas[0]
    b5 = user.big5
    return {
        "economic": (user.risk_tolerance - 5.0) * 0.8,
        "career": (b5.C - 5.0) * 1.2,
        "relationship": (b5.A - 5.0) * 1.2,
        "mental": (5.0 - b5.N) * 1.4,
        "autonomy": (b5.O - 5.0) * 1.0,
    }


def _event_month_effects(
    events: List[TimelineEvent], option_bias: Dict[str, float]
) -> Dict[int, Dict[str, float]]:
    """Per-month incremental effect contributed by each event.

    Skeleton events carry the strongest signal, perturbations less, exogenous a
    small shared nudge.
    """
    weight_by_kind = {"skeleton": 1.0, "perturbation": 0.5, "exogenous": 0.3}
    per_month: Dict[int, Dict[str, float]] = {}
    for ev in events:
        w = weight_by_kind.get(ev.kind, 0.5)
        slot = per_month.setdefault(ev.month, {d: 0.0 for d in METRIC_DIMS})
        if ev.kind == "exogenous":
            # Exogenous backbone is a mild, mostly-negative drag, identical-ish
            # in both branches (it does not encode the option bias).
            slot["economic"] += -1.0 * w
            slot["mental"] += -0.8 * w
        else:
            for dim in METRIC_DIMS:
                slot[dim] += option_bias[dim] * 0.12 * w
    return per_month


def score_branch(
    branch: str,
    option_text: str,
    personas: List[Persona],
    events: List[TimelineEvent],
    seed: int,
    mode: str,
) -> List[MetricPoint]:
    """Produce MetricPoints for months 0..horizon for one branch (ALG-40)."""
    horizon = horizon_for_mode(mode)
    rng = random.Random("score:%d:%s" % (seed, branch))

    option_bias = _option_bias(option_text)
    base_offsets = _persona_baseline(personas)
    month_effects = _event_month_effects(events, option_bias)

    branch_events = [e for e in events if e.branch == branch]
    branch_events_sorted = sorted(branch_events, key=lambda e: (e.month, e.id))
    earliest_id = branch_events_sorted[0].id if branch_events_sorted else None

    # Running metric state starts near neutral 50 + persona offset.
    state = {d: clamp(50.0 + base_offsets[d]) for d in METRIC_DIMS}

    points: List[MetricPoint] = []
    for month in range(0, horizon + 1):
        if month in month_effects:
            for dim in METRIC_DIMS:
                state[dim] = clamp(state[dim] + month_effects[month][dim])
        # Small deterministic monthly drift so curves are not flat.
        for dim in METRIC_DIMS:
            state[dim] = clamp(state[dim] + rng.uniform(-0.8, 0.8))

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
                economic=round(state["economic"], 1),
                career=round(state["career"], 1),
                relationship=round(state["relationship"], 1),
                mental=round(state["mental"], 1),
                autonomy=round(state["autonomy"], 1),
                supporting_event_ids=supporting,
            )
        )
    return points
