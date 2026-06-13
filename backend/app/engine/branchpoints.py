"""Divergence detection between the two branches.

Finds months where the summed |A-B| divergence across the five dimensions spikes
(relative to the prior month), reports the dominant dimension, magnitude, a short
description, and a cause_chain referencing the divergent events near that month.
"""
from __future__ import annotations

from typing import Dict, List

from ..contracts import METRIC_DIMS, BranchPoint, MetricPoint, TimelineEvent


def _by_month(metrics: List[MetricPoint], branch: str) -> Dict[int, MetricPoint]:
    return {m.month: m for m in metrics if m.branch == branch}


def detect_branch_points(
    metrics: List[MetricPoint],
    events: List[TimelineEvent],
    max_points: int = 3,
) -> List[BranchPoint]:
    """Return up to `max_points` months with the largest divergence jumps."""
    a = _by_month(metrics, "A")
    b = _by_month(metrics, "B")
    months = sorted(set(a.keys()) & set(b.keys()))
    if not months:
        return []

    # Per-month total divergence and per-dimension gaps.
    total_div: Dict[int, float] = {}
    dim_gap: Dict[int, Dict[str, float]] = {}
    for m in months:
        gaps = {d: abs(getattr(a[m], d) - getattr(b[m], d)) for d in METRIC_DIMS}
        dim_gap[m] = gaps
        total_div[m] = sum(gaps.values())

    # Score each month by the increase in divergence vs the previous month.
    scored = []
    prev = 0.0
    for m in months:
        jump = total_div[m] - prev
        scored.append((jump, total_div[m], m))
        prev = total_div[m]

    # Pick the top jumps (require a meaningful positive jump).
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    chosen = [s for s in scored if s[0] > 0.5][:max_points]
    if not chosen:
        # Fall back to the single month of maximum absolute divergence.
        m = max(months, key=lambda mm: total_div[mm])
        chosen = [(total_div[m], total_div[m], m)]

    points: List[BranchPoint] = []
    for _, magnitude, month in sorted(chosen, key=lambda t: t[2]):
        gaps = dim_gap[month]
        dom = max(METRIC_DIMS, key=lambda d: gaps[d])
        cause = _cause_chain(events, month, dom)
        points.append(
            BranchPoint(
                month=month,
                metric=dom,
                magnitude=round(gaps[dom], 1),
                description=(
                    "Around month %d the two paths diverge most on %s "
                    "(gap ~%.1f points)." % (month, dom, gaps[dom])
                ),
                cause_chain=cause,
            )
        )
    return points


def _cause_chain(events: List[TimelineEvent], month: int, dim: str) -> str:
    """Build a short cause chain from decision events near the branch month."""
    window = [
        e
        for e in events
        if not e.is_shared_exogenous and month - 2 <= e.month <= month + 1
    ]
    window.sort(key=lambda e: (e.month, e.branch, e.id))
    if not window:
        return (
            "Accumulated decision-dependent effects drove the %s gap; the shared "
            "backbone affected both paths equally." % dim
        )
    parts = []
    for e in window[:4]:
        parts.append("[%s m%d] %s" % (e.branch, e.month, e.title))
    return (
        "Divergence on %s traces to: " % dim
        + " -> ".join(parts)
        + ". Shared exogenous events cancel out across branches."
    )
