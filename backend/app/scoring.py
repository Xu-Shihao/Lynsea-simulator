"""backend/app/scoring.py — BE-Score (Wave 2).

Five-dimension value-weighted scoring, fork detection, the credibility card,
and a probabilistic recommendation with guardrails. This module replaces the
Wave-1 stubs in ``orchestrator.py`` (auto-bound by its ``_bind`` block — no edit
to that file is needed).

Design notes
------------
* **Pure-Python and deterministic — no LLM.** Scoring is arithmetic over the
  metric curves and the world state. Keeping it deterministic means a fixed
  seed reproduces byte-identical scores (``NFR-01``) and the natural-language
  copy is *guaranteed* probabilistic (``SYS-15``) rather than relying on a model
  to stay on-message. (Per ``BUILD_PLAN.md`` §2 the LLM is for narrative/causal
  text, which lives in other modules.)
* All result copy uses probabilistic phrasing ("likely", "around a 60% chance")
  and never the deterministic words "will / definitely / certainly / guaranteed"
  (``SYS-15`` — enforced by the copy-lint in ``tests/test_score.py``).

Public API (matches ``app.interfaces`` / ``BUILD_PLAN.md`` §5):

* ``score_branch(sim, values) -> BranchScore``   — ``ALG-40``, ``ALG-41``, ``SYS-14``
* ``detect_forks(a, b) -> list[ForkPoint]``       — month of maximum A/B divergence
* ``credibility(world, sims) -> Credibility``     — ``ALG-42``, ``SYS-17``
* ``recommend(world, scores, forks, cred) -> Recommendation`` — ``SYS-15``, ``SYS-16``
"""

from __future__ import annotations

from app.schemas import (
    DIMENSIONS,
    BranchScore,
    Credibility,
    CredibilityBreakdown,
    Dimension,
    ForkPoint,
    Recommendation,
    SimResult,
    ValueWeights,
    World,
)

# --------------------------------------------------------------------------- #
# Tuning constants
# --------------------------------------------------------------------------- #
_NEUTRAL = 50.0  # score for a dimension with no metric data (no opinion)

# Below this weighted-total gap the two branches are "too close to call".
_LEAN_THRESHOLD = 3.0

# A secondary fork must clear this fraction of the strongest fork's divergence
# to be worth surfacing (keeps the list to genuine turning points).
_SECONDARY_FORK_RATIO = 0.6
_MAX_FORKS = 3

# Mode → baseline causal confidence. Quick mode skips a formal structural causal
# model (ALG-22), so causal confidence is capped lower there.
_CAUSAL_BASE: dict[str, int] = {"quick": 55, "medium": 66, "heavy": 74}

# A relationships/mental-health score at or below this in either branch marks a
# result as high-risk (mirrors the QA heuristic in tests/test_guardrails.py).
_FRAGILE_DIM_FLOOR = 35.0
_FRAGILE_DIMS: tuple[Dimension, ...] = ("relationships", "mental_health")

# High-stakes decision keywords → always surface the SYS-16 guardrail. Substring
# match on the lower-cased decision text (EN + the common ZH terms).
_HIGH_RISK_TERMS: tuple[str, ...] = (
    "quit", "resign", "fire", "divorce", "break up", "breakup", "split",
    "relationship", "marriage", "marry", "health", "sick", "illness", "loan",
    "debt", "mortgage", "bankrupt", "invest", "savings", "abroad", "emigrate",
    "辞职", "离职", "分手", "离婚", "结婚", "搬家", "投资", "创业", "贷款", "破产",
)


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _metric_map(sim: SimResult) -> dict[tuple[int, str], float]:
    """``(month, dim) -> score`` view of a branch's metric curve."""
    return {(m.month, m.dim): m.score for m in sim.metrics}


def dimension_evidence(sim: SimResult) -> dict[str, list[str]]:
    """Evidence event ids backing each dimension's score (``ALG-40``).

    A dimension's score is the aggregate of its metric datapoints, and every
    metric references >= 1 supporting event. This returns, per dimension, the
    de-duplicated union of those evidence ids so the linkage is explicit and
    testable at the scoring layer. Dimensions with no metric data map to ``[]``.
    """
    out: dict[str, list[str]] = {dim: [] for dim in DIMENSIONS}
    for m in sim.metrics:
        bucket = out.setdefault(m.dim, [])
        for eid in m.evidence_event_ids:
            if eid not in bucket:
                bucket.append(eid)
    return out


# --------------------------------------------------------------------------- #
# ALG-40 / ALG-41 / SYS-14 — value-weighted 5-dimension score
# --------------------------------------------------------------------------- #
def score_branch(sim: SimResult, values: ValueWeights) -> BranchScore:
    """Aggregate a branch's metric curves into one value-weighted score.

    * **Five dimensions, 0–100** (``ALG-40``): the breakdown always covers all of
      ``economic / career / relationships / mental_health / autonomy``; each
      dimension's score is a recency-weighted mean of its metric datapoints, so
      *where the trajectory ends up* counts more than transient early swings,
      while still reflecting the whole path. Every contributing metric links to
      >= 1 evidence event (see :func:`dimension_evidence`).
    * **Value-weighted total** (``ALG-41`` / ``M-d``): "better" means better
      *for them*. The total aggregates the breakdown by the user-calibrated
      :class:`ValueWeights`. Because the weights are normalised, raising a
      dimension's weight moves the total toward that dimension's score, so the
      total — and therefore the leaning — shifts in the matching direction
      (``SYS-14``).
    """
    # Bucket every datapoint by dimension, keyed by month for recency weighting.
    by_dim: dict[str, list[tuple[int, float]]] = {d: [] for d in DIMENSIONS}
    for m in sim.metrics:
        by_dim.setdefault(m.dim, []).append((m.month, m.score))

    breakdown: dict[str, float] = {}
    for dim in DIMENSIONS:
        points = by_dim.get(dim, [])
        if not points:
            breakdown[dim] = _NEUTRAL
            continue
        # Recency weight = month index (later months dominate). With a single
        # month this reduces to that month's score.
        min_month = min(month for month, _ in points)
        wsum = 0.0
        acc = 0.0
        for month, score in points:
            w = float(month - min_month + 1)  # >= 1, grows toward the horizon
            wsum += w
            acc += w * score
        breakdown[dim] = round(_clamp(acc / wsum), 1)

    weights = values.normalized()
    total = round(_clamp(sum(breakdown[d] * weights[d] for d in DIMENSIONS)), 1)

    return BranchScore(branch=sim.branch, total=total, breakdown=breakdown, weighted=True)


# --------------------------------------------------------------------------- #
# Fork detection — month(s) of maximum A/B divergence (causal-effect proxy)
# --------------------------------------------------------------------------- #
def _divergence_by_month(
    a: SimResult, b: SimResult
) -> tuple[list[int], dict[int, dict[str, float]], dict[int, float]]:
    """Per-month, per-dimension |A − B| gap and its cross-dimension mean."""
    a_map = _metric_map(a)
    b_map = _metric_map(b)
    months = sorted({m for (m, _d) in a_map} & {m for (m, _d) in b_map})

    per_dim: dict[int, dict[str, float]] = {}
    mean_gap: dict[int, float] = {}
    for month in months:
        diffs = {
            dim: abs(a_map.get((month, dim), _NEUTRAL) - b_map.get((month, dim), _NEUTRAL))
            for dim in DIMENSIONS
        }
        per_dim[month] = diffs
        mean_gap[month] = sum(diffs.values()) / len(DIMENSIONS)
    return months, per_dim, mean_gap


def _fork_for_month(
    month: int, diffs: dict[str, float], gap: float, *, primary: bool
) -> ForkPoint:
    top_dims = [d for d, _ in sorted(diffs.items(), key=lambda kv: -kv[1])[:2] if diffs[d] > 0.5]
    dims_text = ", ".join(top_dims) if top_dims else "several dimensions"
    magnitude = round(_clamp(gap), 1)
    lead = "The paths likely diverge most" if primary else "The paths likely pull apart again"
    title = (
        f"Paths diverge most around month {month}"
        if primary
        else f"A second divergence around month {month}"
    )
    explanation = (
        f"{lead} around month {month} — roughly a {int(round(magnitude))}-point "
        f"average gap across {dims_text}. This separation likely traces back to "
        "the decision itself rather than to chance events, since both branches "
        "share the same random event stream."
    )
    return ForkPoint(
        month=month,
        magnitude=magnitude,
        title=title,
        explanation=explanation,
        dims=top_dims,  # type: ignore[arg-type]
    )


def detect_forks(a: SimResult, b: SimResult) -> list[ForkPoint]:
    """Locate where the two branches diverge sharply.

    A fork is the month of maximum cross-dimension divergence between A and B
    (a causal-effect proxy: with a shared random-event stream, the gap is driven
    by the decision variable). The strongest month is always returned; clear
    secondary turning points (local peaks above
    ``_SECONDARY_FORK_RATIO`` of the max) are added so a long trajectory can show
    more than one fork. Each fork carries an explanation, the affected
    dimensions, and a magnitude.
    """
    months, per_dim, mean_gap = _divergence_by_month(a, b)
    if not months:
        return []

    primary_month = max(months, key=lambda mo: mean_gap[mo])
    primary_gap = mean_gap[primary_month]
    forks = [_fork_for_month(primary_month, per_dim[primary_month], primary_gap, primary=True)]

    if primary_gap > 0:
        threshold = _SECONDARY_FORK_RATIO * primary_gap
        idx = {mo: i for i, mo in enumerate(months)}
        candidates: list[int] = []
        for mo in months:
            if mo == primary_month or abs(mo - primary_month) <= 1:
                continue  # skip the primary and its immediate neighbours
            gap = mean_gap[mo]
            if gap < threshold:
                continue
            i = idx[mo]
            left = mean_gap[months[i - 1]] if i > 0 else -1.0
            right = mean_gap[months[i + 1]] if i + 1 < len(months) else -1.0
            if gap >= left and gap >= right:  # local peak
                candidates.append(mo)
        for mo in sorted(candidates, key=lambda m: -mean_gap[m])[: _MAX_FORKS - 1]:
            forks.append(_fork_for_month(mo, per_dim[mo], mean_gap[mo], primary=False))

    forks.sort(key=lambda f: f.month)
    return forks


# --------------------------------------------------------------------------- #
# ALG-42 / SYS-17 — credibility card
# --------------------------------------------------------------------------- #
def _branch_horizon(sims: list[SimResult]) -> int:
    months = [m.month for s in sims for m in s.metrics]
    return max(months) if months else 0


def _perturbation_share(sims: list[SimResult]) -> float:
    total = sum(len(s.events) for s in sims)
    if total == 0:
        return 0.0
    pert = sum(1 for s in sims for e in s.events if e.kind == "perturbation")
    return pert / total


def credibility(world: World, sims: list[SimResult]) -> Credibility:
    """Self-assess confidence in the result and surface the weak spots.

    Three sub-scores (``ALG-42``):

    * **data_sufficiency** — how much real signal the personas carry vs.
      population defaults (cold-start personas drag it down; ``ALG-04``).
    * **causal_confidence** — quick mode skips a formal structural causal model
      (``ALG-22``), so it is capped lower there and lifts with horizon coverage.
    * **event_plausibility** — events are whitelist-constrained (``ALG-31``), so
      this starts high and dips a little as the perturbation share rises.

    ``notes`` names the weakest area explicitly (``SYS-17`` — "mark what is
    reliable vs. directional") in probabilistic phrasing (``SYS-15``).
    """
    personas = world.personas
    n = len(personas) or 1
    high = sum(1 for p in personas if p.confidence == "high")
    cold = sum(1 for p in personas if getattr(p, "cold_start", False))

    data_sufficiency = int(round(_clamp(30 + 55 * (high / n) - 6 * (cold / n) - (8 if n < 3 else 0))))

    base = _CAUSAL_BASE.get(world.mode, 55)
    horizon = _branch_horizon(sims)
    coverage_bonus = 6 if horizon >= 6 else (3 if horizon >= 3 else 0)
    causal_confidence = int(round(_clamp(base + coverage_bonus)))

    event_plausibility = int(round(_clamp(86 - 18 * _perturbation_share(sims))))

    overall = int(
        round(0.40 * data_sufficiency + 0.35 * causal_confidence + 0.25 * event_plausibility)
    )

    sub = {
        "data sufficiency": data_sufficiency,
        "causal confidence": causal_confidence,
        "event plausibility": event_plausibility,
    }
    weakest_name, weakest_val = min(sub.items(), key=lambda kv: kv[1])
    cold_note = (
        f" {cold} of {n} personas rely on population defaults "
        "(information limited — for reference only)."
        if cold
        else ""
    )
    notes = (
        f"Overall confidence sits around {overall}%. Treat these trajectories as "
        f"directional rather than predictive: the weakest area is {weakest_name} "
        f"(about {weakest_val}%), so read results there with extra caution."
        f"{cold_note}"
    )

    return Credibility(
        overall=overall,
        breakdown=CredibilityBreakdown(
            data_sufficiency=data_sufficiency,
            causal_confidence=causal_confidence,
            event_plausibility=event_plausibility,
        ),
        notes=notes,
    )


# --------------------------------------------------------------------------- #
# SYS-15 / SYS-16 — probabilistic recommendation + guardrail
# --------------------------------------------------------------------------- #
def _is_high_risk(world: World, scores: list[BranchScore]) -> bool:
    decision = (world.decision or "").lower()
    if any(term in decision for term in _HIGH_RISK_TERMS):
        return True
    for s in scores:
        for dim in _FRAGILE_DIMS:
            if s.breakdown.get(dim, _NEUTRAL) <= _FRAGILE_DIM_FLOOR:
                return True
    return False


def _lean_percent(gap: float, cred_overall: int) -> int:
    """Map a weighted-total gap to a soft probability, damped by credibility.

    Never reaches certainty: bounded to [52, 80] for a real lean. Lower overall
    credibility pulls the figure back toward a coin-flip.
    """
    raw = min(30.0, gap * 1.6)  # 0..30 above the 50% baseline
    damped = raw * (cred_overall / 100.0)
    return int(round(_clamp(50 + damped, 52, 80)))


def recommend(
    world: World,
    scores: list[BranchScore],
    forks: list[ForkPoint],
    cred: Credibility,
) -> Recommendation:
    """A probabilistic leaning plus a guardrail.

    * **Probabilistic, never deterministic** (``SYS-15``): the rationale states a
      soft likelihood ("around a 62% lean") and avoids "will / definitely".
    * **Guardrail** (``SYS-16``): every result carries "this is a simulation, not
      a prophecy" plus a concrete "how to change this outcome" affordance;
      high-stakes decisions (health / relationships / finances, or a fragile
      relationships/mental-health score) get an extra heads-up.
    """
    by_branch = {s.branch: s for s in scores}
    a = by_branch.get("A")
    b = by_branch.get("B")
    a_total = a.total if a else _NEUTRAL
    b_total = b.total if b else _NEUTRAL
    diff = b_total - a_total
    gap = abs(diff)

    if gap < _LEAN_THRESHOLD:
        leaning: str = "neither"
    elif diff > 0:
        leaning = "B"
    else:
        leaning = "A"

    lean_pct = _lean_percent(gap, cred.overall)
    label_a = world.options.get("A", "Option A")
    label_b = world.options.get("B", "Option B")

    if leaning == "neither":
        rationale = (
            "Weighted against what matters most to you, the two paths look close — "
            f"around {a_total:.0f}/100 for '{label_a}' versus {b_total:.0f}/100 for "
            f"'{label_b}'. Neither option is clearly ahead, so the choice likely "
            "comes down to which trade-offs feel more livable for you."
        )
    else:
        leader_label = label_b if leaning == "B" else label_a
        hi, lo = max(a_total, b_total), min(a_total, b_total)
        conf_word = "lower" if cred.overall < 55 else "moderate"
        rationale = (
            f"Weighted against what matters most to you, '{leader_label}' looks like "
            f"the stronger path — around {hi:.0f}/100 versus {lo:.0f}/100, roughly a "
            f"{lean_pct}% lean. This is a probabilistic read rather than a fixed "
            f"outcome, and a {conf_word}-confidence one given the data."
        )

    guardrail = (
        "This is a simulation, not a prophecy — the trajectories are probabilistic "
        "and could shift. Here is how to change this outcome: try adjusting one "
        "assumption (a key relationship, your risk tolerance, or the timing) and "
        "re-run to see how the branches move."
    )
    if _is_high_risk(world, scores):
        guardrail = (
            "⚠ This looks like a high-stakes decision, so weigh it slowly and "
            "consider talking it through with someone you trust. " + guardrail
        )

    return Recommendation(
        leaning=leaning,  # type: ignore[arg-type]
        rationale=rationale,
        guardrail=guardrail,
    )


__all__ = [
    "score_branch",
    "detect_forks",
    "credibility",
    "recommend",
    "dimension_evidence",
]
