"""Credibility card + value-weighted recommendation (SYS-15 / SYS-16).

CredibilityCard combines:
  - data_sufficiency: up with more/explicit personas, down with cold-start defaults.
  - causal_confidence: up with more decision-dependent events & clear divergence.
  - event_plausibility: from the simulate-stage resample/rejection rate.
The Recommendation applies the user's value weights to the final-month metrics
and picks the favored branch, phrased PROBABILISTICALLY (never "will"/"definitely").
A "simulation, not a prophecy" caveat is added when a high-risk dimension
(mental/relationship) drops sharply.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from ..contracts import (
    DEFAULT_DIMENSIONS,
    BranchPoint,
    CredibilityCard,
    Dimension,
    MetricPoint,
    Persona,
    Recommendation,
    TimelineEvent,
)
from .common import clamp


def build_credibility(
    personas: List[Persona],
    events: List[TimelineEvent],
    branch_points: List[BranchPoint],
    rejection_rate: float,
) -> CredibilityCard:
    """Assemble the credibility card from engine signals."""
    n_personas = len(personas)
    n_default = sum(1 for p in personas if p.is_default_inferred)
    low_conf = [p.id for p in personas if p.is_default_inferred]

    # Data sufficiency: baseline 40, +10 per explicitly-inferred persona (cap),
    # minus a penalty for each cold-start default.
    explicit = n_personas - n_default
    data_sufficiency = clamp(40.0 + explicit * 12.0 - n_default * 8.0)

    # Causal confidence: more decision-dependent events and clearer divergence help.
    decision_events = [e for e in events if not e.is_shared_exogenous]
    causal_confidence = clamp(
        35.0
        + min(len(decision_events), 12) * 3.0
        + min(len(branch_points), 3) * 5.0
    )

    # Event plausibility: 100 minus the rejection rate (as a percentage).
    event_plausibility = clamp(100.0 - rejection_rate * 100.0)

    overall = round(
        0.35 * data_sufficiency
        + 0.35 * causal_confidence
        + 0.30 * event_plausibility,
        1,
    )

    notes: List[str] = []
    if n_default:
        notes.append(
            "%d of %d personas use population defaults (cold start); treat their "
            "stance as low-confidence." % (n_default, n_personas)
        )
    else:
        notes.append("All personas were inferred from your description.")
    if rejection_rate > 0:
        notes.append(
            "Plausibility guard rejected ~%.0f%% of proposed events and resampled "
            "or downgraded them." % (rejection_rate * 100.0)
        )
    else:
        notes.append("No implausible events were generated.")
    notes.append(
        "Shared exogenous events are identical across both branches, so the gap "
        "you see is attributable to the decision."
    )

    return CredibilityCard(
        overall=overall,
        data_sufficiency=round(data_sufficiency, 1),
        causal_confidence=round(causal_confidence, 1),
        event_plausibility=round(event_plausibility, 1),
        notes=notes,
        low_confidence_personas=low_conf,
    )


def _final_metrics(metrics: List[MetricPoint], branch: str) -> Optional[MetricPoint]:
    pts = [m for m in metrics if m.branch == branch]
    if not pts:
        return None
    return max(pts, key=lambda m: m.month)


def _oriented(score: float, polarity: str) -> float:
    """Orient a 0-100 score so higher always means 'better' for aggregation."""
    return score if polarity == "higher_is_better" else (100.0 - score)


def _weighted_score(
    point: MetricPoint, weights: Dict[str, float], dims: List[Dimension]
) -> float:
    total_w = sum(weights.get(d.id, 0.0) for d in dims) or 1.0
    s = sum(
        _oriented(point.scores.get(d.id, 50.0), d.polarity) * weights.get(d.id, 0.0)
        for d in dims
    )
    return s / total_w


def _prob_phrase(diff: float) -> str:
    """Map a weighted-score gap to a probabilistic confidence phrase."""
    ad = abs(diff)
    if ad < 1.5:
        return "roughly a coin toss (~50/50)"
    if ad < 5:
        return "a slight lean, perhaps ~55% likely"
    if ad < 12:
        return "a moderate lean, perhaps ~65% likely"
    return "a fairly strong lean, perhaps ~75% likely"


def build_recommendation(
    metrics: List[MetricPoint],
    options: List[str],
    values: Optional[Dict[str, float]],
    dimensions: Optional[List[Dimension]] = None,
) -> Recommendation:
    """Value-weighted favored branch, phrased as probability (SYS-15/16).

    Weights default to a neutral 5 per dimension and are overridden by
    `values.get(dim.id, 5)`. Aggregation is polarity-aware so a lower_is_better
    dimension contributes correctly.
    """
    dims = list(dimensions) if dimensions else [d.model_copy() for d in DEFAULT_DIMENSIONS]
    weights = {d.id: 5.0 for d in dims}
    if values:
        for d in dims:
            if d.id in values and values[d.id] is not None:
                try:
                    weights[d.id] = float(values[d.id])
                except (TypeError, ValueError):
                    pass

    fa = _final_metrics(metrics, "A")
    fb = _final_metrics(metrics, "B")
    if fa is None or fb is None:
        return Recommendation(
            text=(
                "Not enough simulated data to lean either way; this is a "
                "simulation, not a prophecy."
            ),
            favored_branch="tie",
        )

    sa = _weighted_score(fa, weights, dims)
    sb = _weighted_score(fb, weights, dims)
    diff = sa - sb

    if abs(diff) < 1.5:
        favored = "tie"
        favored_text = "Neither option clearly dominates"
    elif diff > 0:
        favored = "A"
        favored_text = "Option A (%s) tends to come out ahead" % _short(options, 0)
    else:
        favored = "B"
        favored_text = "Option B (%s) tends to come out ahead" % _short(options, 1)

    phrase = _prob_phrase(diff)

    # SYS-16: caveat if a high-risk dimension drops sharply on the favored path.
    # High-risk axes are the well-being/relationship dims (by id) when present;
    # the "oriented" score is what matters so a lower_is_better risk dim is
    # interpreted correctly.
    caveat = ""
    risk_branch_pt = fa if favored != "B" else fb
    if risk_branch_pt is not None:
        risk_ids = {"mental", "relationship"}
        flagged = False
        for d in dims:
            if d.id in risk_ids and d.id in risk_branch_pt.scores:
                if _oriented(risk_branch_pt.scores[d.id], d.polarity) < 38:
                    flagged = True
                    break
        if flagged:
            caveat = (
                " Note: the favored path shows a sharp decline in a high-risk area "
                "(mental well-being or relationships). This is a simulation, not a "
                "prophecy — weigh it against your own judgment."
            )

    text = (
        "Weighing your stated values against the final-month outcomes, %s — %s. "
        "These are probabilities over many possible futures, not a guarantee.%s"
        % (favored_text, phrase, caveat)
    )

    return Recommendation(text=text, favored_branch=favored)


def _short(options: List[str], idx: int, limit: int = 40) -> str:
    if idx >= len(options):
        return "?"
    o = options[idx].strip()
    return o if len(o) <= limit else o[: limit - 1] + "…"
