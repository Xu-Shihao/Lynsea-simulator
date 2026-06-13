"""Shared exogenous backbone (ALG-20 / NFR-01).

Decision-INDEPENDENT life events drawn from a curated template pool using a
seeded RNG. NO LLM is used here so the backbone is byte-identical for the same
decision+seed and is emitted identically into BOTH branches. This is what makes
the paired counterfactual fair: both futures share the same exogenous shocks and
differ only by the decision.
"""
from __future__ import annotations

import random
from typing import Dict, List

from .common import horizon_for_mode

# Curated pool of decision-independent life events. Each entry is a (title,
# description) template. Kept generic so it plausibly applies to any decision.
_EVENT_POOL: List[Dict[str, str]] = [
    {"title": "A close friend moves abroad",
     "description": "Someone in your circle relocates to another country, changing your social rhythm."},
    {"title": "Rent goes up",
     "description": "Housing costs rise at renewal, tightening the monthly budget regardless of the decision."},
    {"title": "Flu season hits",
     "description": "A seasonal illness sweeps through, costing a week of energy and focus."},
    {"title": "A relative's wedding",
     "description": "A family wedding requires travel, time off, and some unplanned spending."},
    {"title": "An old hobby resurfaces",
     "description": "An interest you had set aside comes back, competing for your free time."},
    {"title": "A neighborhood cafe closes",
     "description": "A familiar local spot shuts down, nudging your daily routine."},
    {"title": "A minor car or device repair",
     "description": "An unexpected repair eats into savings and a weekend."},
    {"title": "A former colleague reconnects",
     "description": "An old contact reaches out, reopening a dormant part of your network."},
    {"title": "City transit fares change",
     "description": "Commute costs shift after a fare adjustment, affecting the budget slightly."},
    {"title": "A seasonal mood dip",
     "description": "Shorter days bring a predictable seasonal lull in motivation."},
    {"title": "A family member needs a small favor",
     "description": "A relative asks for help with a short-term task, claiming some attention."},
    {"title": "A streaming subscription price hike",
     "description": "Recurring subscriptions increase, a small but steady budget drag."},
]


def build_backbone(decision: str, seed: int, mode: str) -> List[Dict[str, object]]:
    """Build the shared exogenous backbone deterministically.

    Returns a list of plain dicts: {shared_event_id, month, title, description}.
    Same (seed, mode) => identical output (order, ids, months, text).
    """
    horizon = horizon_for_mode(mode)
    rng = random.Random(seed)

    # Number of backbone events scales gently with horizon.
    if horizon <= 6:
        n_events = 3
    elif horizon <= 18:
        n_events = 5
    else:
        n_events = 7
    n_events = min(n_events, len(_EVENT_POOL))

    # Deterministic sample of distinct templates (indices), then sort by index
    # so the assignment order is stable regardless of sample() internals.
    chosen_idx = sorted(rng.sample(range(len(_EVENT_POOL)), n_events))

    events: List[Dict[str, object]] = []
    for n, idx in enumerate(chosen_idx):
        tpl = _EVENT_POOL[idx]
        # Spread events across the horizon (months 1..horizon, never month 0).
        month = rng.randint(1, max(1, horizon))
        events.append(
            {
                "shared_event_id": "x_%02d" % n,
                "month": month,
                "title": tpl["title"],
                "description": tpl["description"],
            }
        )
    # Stable ordering by month then id for deterministic emission.
    events.sort(key=lambda e: (e["month"], e["shared_event_id"]))
    return events
