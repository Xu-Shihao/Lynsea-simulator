"""Divergence detection between the two branches (dimension-agnostic).

Finds months where the summed |A-B| divergence across the generated dimensions
spikes (relative to the prior month), reports the dominant dimension id, the
magnitude, a short description, and a cause_chain referencing the divergent
events near that month.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ..contracts import DEFAULT_DIMENSIONS, BranchPoint, Dimension, MetricPoint, TimelineEvent


def _by_month(metrics: List[MetricPoint], branch: str) -> Dict[int, MetricPoint]:
    return {m.month: m for m in metrics if m.branch == branch}


def _label_for(dims: List[Dimension], dim_id: str) -> str:
    for d in dims:
        if d.id == dim_id:
            return d.label or dim_id
    return dim_id


def detect_branch_points(
    metrics: List[MetricPoint],
    events: List[TimelineEvent],
    dimensions: Optional[List[Dimension]] = None,
    max_points: int = 3,
) -> List[BranchPoint]:
    """Return up to `max_points` months with the largest divergence jumps."""
    dims = list(dimensions) if dimensions else [d.model_copy() for d in DEFAULT_DIMENSIONS]
    dim_ids = [d.id for d in dims]

    a = _by_month(metrics, "A")
    b = _by_month(metrics, "B")
    months = sorted(set(a.keys()) & set(b.keys()))
    if not months or not dim_ids:
        return []

    # Per-month total divergence and per-dimension gaps.
    total_div: Dict[int, float] = {}
    dim_gap: Dict[int, Dict[str, float]] = {}
    for m in months:
        gaps = {
            d: abs(a[m].scores.get(d, 0.0) - b[m].scores.get(d, 0.0)) for d in dim_ids
        }
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
        dom = max(dim_ids, key=lambda d: gaps[d])
        label = _label_for(dims, dom)
        cause = _cause_chain(events, month, label)
        points.append(
            BranchPoint(
                month=month,
                dimension=dom,
                magnitude=round(gaps[dom], 1),
                description=(
                    "Around month %d the two paths diverge most on %s "
                    "(gap ~%.1f points)." % (month, label, gaps[dom])
                ),
                cause_chain=cause,
            )
        )
    return points


def _cause_chain(events: List[TimelineEvent], month: int, dim_label: str) -> str:
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
            "backbone affected both paths equally." % dim_label
        )
    parts = []
    for e in window[:4]:
        parts.append("[%s m%d] %s" % (e.branch, e.month, e.title))
    return (
        "Divergence on %s traces to: " % dim_label
        + " -> ".join(parts)
        + ". Shared exogenous events cancel out across branches."
    )
