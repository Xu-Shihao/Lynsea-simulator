"""test_score.py — BE-Score acceptance for ``app.scoring``.

Covers the IDs this module owns:

* ``ALG-40`` — five dimensions 0–100, and every dimension score is linked to
  >= 1 supporting evidence event.
* ``ALG-41`` / ``SYS-14`` — value-weighted total ("better for them"); flipping
  the value weights flips the recommendation, in the matching direction.
* ``ALG-42`` / ``SYS-17`` — credibility card with overall + 3 sub-scores +
  notes that flag the weakest area; cold-start personas drag data sufficiency.
* fork detection — the month of maximum A/B divergence (plus clear secondary
  peaks), each with dims, magnitude, and an explanation.
* ``SYS-15`` — copy-lint: zero "will / definitely / certainly / guaranteed" in
  any result text (the recommendation guardrail field is exempt, matching the
  QA convention in test_guardrails.py).
* ``SYS-16`` — high-risk results carry "this is a simulation, not a prophecy"
  plus a "how to change this outcome" affordance.
* the orchestrator binds the real ``app.scoring`` (not the Wave-1 stub).

Run: pytest backend/tests/test_score.py -v
"""
import os
import re
import sys

import pytest

# Make ``app`` importable no matter where pytest is invoked from.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.schemas import (  # noqa: E402
    DIMENSIONS,
    BranchScore,
    Credibility,
    Metric,
    Persona,
    SimResult,
    TimelineEvent,
    ValueWeights,
    World,
)
from app.scoring import (  # noqa: E402
    credibility,
    detect_forks,
    dimension_evidence,
    recommend,
    score_branch,
)

# Deterministic-language patterns (mirrors test_guardrails.DETERMINISTIC_PATTERNS).
DETERMINISTIC_PATTERNS = [
    re.compile(r"\bwill\b", re.IGNORECASE),
    re.compile(r"\bdefinitely\b", re.IGNORECASE),
    re.compile(r"\bcertainly\b", re.IGNORECASE),
    re.compile(r"\bguaranteed\b", re.IGNORECASE),
]
PROBABILISTIC_PATTERNS = [
    re.compile(r"\blikely\b", re.IGNORECASE),
    re.compile(r"\baround\b", re.IGNORECASE),
    re.compile(r"\b\d+%", re.IGNORECASE),
    re.compile(r"\bprobabilistic\b", re.IGNORECASE),
]


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #
def make_sim_flat(branch: str, dim_scores: dict, months: int = 6, evidence: bool = True) -> SimResult:
    """A branch whose every month repeats ``dim_scores`` (constant trajectory).

    With a constant curve the recency-weighted aggregate equals the constant, so
    the resulting breakdown is exactly ``dim_scores`` — handy for assertions.
    """
    events: list[TimelineEvent] = []
    metrics: list[Metric] = []
    for month in range(1, months + 1):
        eid = f"{branch}-m{month}-1"
        events.append(
            TimelineEvent(
                branch=branch,
                event_id=eid,
                month=month,
                kind="skeleton",
                title=f"Month {month}",
                detail="A likely milestone.",
                personas=["self"],
            )
        )
        for dim in DIMENSIONS:
            metrics.append(
                Metric(
                    branch=branch,
                    month=month,
                    dim=dim,
                    score=dim_scores[dim],
                    evidence_event_ids=[eid] if evidence else [],
                )
            )
    return SimResult(branch=branch, events=events, metrics=metrics)


def make_sim_curve(branch: str, curve: dict, kinds: dict | None = None) -> SimResult:
    """A branch with explicit ``{month: {dim: score}}`` control."""
    events: list[TimelineEvent] = []
    metrics: list[Metric] = []
    for month in sorted(curve):
        eid = f"{branch}-m{month}-1"
        kind = (kinds or {}).get(month, "skeleton")
        events.append(
            TimelineEvent(
                branch=branch,
                event_id=eid,
                month=month,
                kind=kind,
                title=f"Month {month}",
                detail="A likely milestone.",
                personas=["self"],
            )
        )
        for dim in DIMENSIONS:
            metrics.append(
                Metric(
                    branch=branch,
                    month=month,
                    dim=dim,
                    score=curve[month][dim],
                    evidence_event_ids=[eid],
                )
            )
    return SimResult(branch=branch, events=events, metrics=metrics)


def make_world(decision: str = "Should I take the new job?", mode: str = "quick",
               personas: list | None = None,
               options: dict | None = None) -> World:
    if personas is None:
        personas = [
            Persona(id="self", role="you", influence_weight=10, confidence="high"),
            Persona(id="partner", role="partner", influence_weight=8, confidence="high"),
            Persona(id="mentor", role="mentor", influence_weight=5, confidence="high"),
        ]
    return World(
        run_id="r1",
        decision=decision,
        mode=mode,
        seed=42,
        options=options or {"A": "Stay at current job", "B": "Take the new job"},
        personas=personas,
    )


def collect_nl_text(*objs) -> list[tuple[str, str]]:
    """(label, text) for every result field the SYS-15 lint scans (no guardrail)."""
    out: list[tuple[str, str]] = []
    for obj in objs:
        if isinstance(obj, list):
            for o in obj:
                out.extend(collect_nl_text(o))
        elif hasattr(obj, "explanation"):  # ForkPoint
            out.append(("fork.title", obj.title))
            out.append(("fork.explanation", obj.explanation))
        elif hasattr(obj, "notes"):  # Credibility
            out.append(("credibility.notes", obj.notes))
        elif hasattr(obj, "rationale"):  # Recommendation (guardrail intentionally excluded)
            out.append(("recommendation.rationale", obj.rationale))
    return out


# --------------------------------------------------------------------------- #
# ALG-40 — 5 dims, 0–100, every score links >= 1 evidence event
# --------------------------------------------------------------------------- #
class TestScoreBranchALG40:
    def test_breakdown_has_all_five_dims_in_range(self):
        sim = make_sim_flat("A", {d: 60.0 for d in DIMENSIONS})
        score = score_branch(sim, ValueWeights())
        assert isinstance(score, BranchScore)
        assert set(score.breakdown) == set(DIMENSIONS)
        for dim in DIMENSIONS:
            assert 0.0 <= score.breakdown[dim] <= 100.0
        assert 0.0 <= score.total <= 100.0
        assert score.weighted is True
        assert score.branch == "A"

    def test_every_metric_has_evidence(self):
        """ALG-40: each scored datapoint references >= 1 supporting event."""
        sim = make_sim_flat("A", {d: 50.0 for d in DIMENSIONS})
        assert sim.metrics
        for m in sim.metrics:
            assert len(m.evidence_event_ids) >= 1, f"metric {m.dim}@{m.month} lacks evidence"

    def test_every_dimension_score_is_evidence_linked(self):
        """ALG-40: the union of evidence per dimension is non-empty."""
        sim = make_sim_flat("B", {d: 70.0 for d in DIMENSIONS})
        ev = dimension_evidence(sim)
        for dim in DIMENSIONS:
            assert ev[dim], f"dimension {dim} score is not backed by any evidence event"

    def test_recency_weighting_favours_later_months(self):
        """A rising curve should aggregate above its midpoint (end-state weighted)."""
        curve = {m: {d: float(40 + 10 * m) for d in DIMENSIONS} for m in range(1, 7)}
        sim = make_sim_curve("A", curve)
        score = score_branch(sim, ValueWeights())
        # months 1..6 -> 50..100, plain mean = 75; recency weighting lifts it higher.
        assert score.breakdown["economic"] > 75.0


# --------------------------------------------------------------------------- #
# ALG-41 / SYS-14 — value-weighting moves the result for *them*
# --------------------------------------------------------------------------- #
class TestValueWeightingSYS14:
    def _ab(self):
        # A is stronger in economic; B is stronger in career; rest tied.
        sim_a = make_sim_flat("A", {"economic": 80, "career": 20, "relationships": 50,
                                    "mental_health": 50, "autonomy": 50})
        sim_b = make_sim_flat("B", {"economic": 20, "career": 80, "relationships": 50,
                                    "mental_health": 50, "autonomy": 50})
        return sim_a, sim_b

    def test_raising_a_dimension_weight_moves_total_toward_it(self):
        sim_a, _ = self._ab()
        # economic=80 (high), career=20 (low): weighting economic up raises the total.
        equal = score_branch(sim_a, ValueWeights()).total
        econ_heavy = score_branch(sim_a, ValueWeights(economic=10)).total
        career_heavy = score_branch(sim_a, ValueWeights(career=10)).total
        assert econ_heavy > equal > career_heavy

    def test_flipping_weights_flips_the_leaning(self):
        sim_a, sim_b = self._ab()
        world = make_world()
        cred = credibility(world, [sim_a, sim_b])

        econ_weights = ValueWeights(economic=10)
        rec_econ = recommend(
            world,
            [score_branch(sim_a, econ_weights), score_branch(sim_b, econ_weights)],
            [],
            cred,
        )
        career_weights = ValueWeights(career=10)
        rec_career = recommend(
            world,
            [score_branch(sim_a, career_weights), score_branch(sim_b, career_weights)],
            [],
            cred,
        )
        # A wins on an economic-weighted view; B wins on a career-weighted view.
        assert rec_econ.leaning == "A"
        assert rec_career.leaning == "B"


# --------------------------------------------------------------------------- #
# Fork detection
# --------------------------------------------------------------------------- #
class TestDetectForks:
    def test_picks_month_of_maximum_divergence(self):
        gaps = {1: 5, 2: 10, 3: 20, 4: 60, 5: 30, 6: 15}
        # economic baseline 30 so 30 + gap stays within the 0–100 Metric cap.
        a = make_sim_curve("A", {m: {**{d: 50.0 for d in DIMENSIONS}, "economic": 30.0} for m in gaps})
        b_curve = {m: {d: 50.0 for d in DIMENSIONS} for m in gaps}
        for m, g in gaps.items():
            b_curve[m]["economic"] = 30.0 + g
        b = make_sim_curve("B", b_curve)

        forks = detect_forks(a, b)
        assert forks, "expected >= 1 fork"
        primary = max(forks, key=lambda f: f.magnitude)
        assert primary.month == 4
        assert "economic" in primary.dims
        assert primary.magnitude == pytest.approx(60.0 / len(DIMENSIONS), abs=0.5)
        assert primary.explanation and primary.title

    def test_detects_secondary_peak(self):
        gaps = {1: 10, 2: 60, 3: 15, 4: 12, 5: 55, 6: 10}
        a = make_sim_curve("A", {m: {**{d: 50.0 for d in DIMENSIONS}, "economic": 30.0} for m in gaps})
        b_curve = {m: {d: 50.0 for d in DIMENSIONS} for m in gaps}
        for m, g in gaps.items():
            b_curve[m]["economic"] = 30.0 + g
        b = make_sim_curve("B", b_curve)

        forks = detect_forks(a, b)
        months = {f.month for f in forks}
        assert {2, 5}.issubset(months), f"expected forks at months 2 and 5, got {months}"

    def test_no_common_months_returns_empty(self):
        a = make_sim_curve("A", {1: {d: 50.0 for d in DIMENSIONS}})
        b = make_sim_curve("B", {2: {d: 50.0 for d in DIMENSIONS}})
        assert detect_forks(a, b) == []


# --------------------------------------------------------------------------- #
# ALG-42 / SYS-17 — credibility card
# --------------------------------------------------------------------------- #
class TestCredibilityALG42:
    def test_card_shape_and_ranges(self):
        world = make_world()
        sims = [make_sim_flat("A", {d: 60.0 for d in DIMENSIONS}),
                make_sim_flat("B", {d: 55.0 for d in DIMENSIONS})]
        cred = credibility(world, sims)
        assert isinstance(cred, Credibility)
        assert 0 <= cred.overall <= 100
        for v in (cred.breakdown.data_sufficiency, cred.breakdown.causal_confidence,
                  cred.breakdown.event_plausibility):
            assert 0 <= v <= 100
        assert cred.notes.strip()

    def test_cold_start_lowers_data_sufficiency(self):
        sims = [make_sim_flat("A", {d: 60.0 for d in DIMENSIONS}),
                make_sim_flat("B", {d: 55.0 for d in DIMENSIONS})]
        high_world = make_world(personas=[
            Persona(id="self", role="you", influence_weight=10, confidence="high"),
            Persona(id="p2", role="partner", influence_weight=8, confidence="high"),
            Persona(id="p3", role="mentor", influence_weight=5, confidence="high"),
        ])
        cold_world = make_world(personas=[
            Persona(id="self", role="you", influence_weight=10, confidence="low", cold_start=True),
            Persona(id="p2", role="partner", influence_weight=8, confidence="low", cold_start=True),
            Persona(id="p3", role="mentor", influence_weight=5, confidence="low", cold_start=True),
        ])
        hi = credibility(high_world, sims)
        lo = credibility(cold_world, sims)
        assert lo.breakdown.data_sufficiency < hi.breakdown.data_sufficiency
        assert "reference only" in lo.notes or "population defaults" in lo.notes

    def test_quick_mode_caps_causal_confidence_below_heavy(self):
        sims = [make_sim_flat("A", {d: 60.0 for d in DIMENSIONS}),
                make_sim_flat("B", {d: 55.0 for d in DIMENSIONS})]
        quick = credibility(make_world(mode="quick"), sims)
        heavy = credibility(make_world(mode="heavy"), sims)
        assert quick.breakdown.causal_confidence < heavy.breakdown.causal_confidence

    def test_notes_flag_the_weakest_area(self):
        world = make_world()
        sims = [make_sim_flat("A", {d: 60.0 for d in DIMENSIONS}),
                make_sim_flat("B", {d: 55.0 for d in DIMENSIONS})]
        cred = credibility(world, sims)
        sub = {
            "data sufficiency": cred.breakdown.data_sufficiency,
            "causal confidence": cred.breakdown.causal_confidence,
            "event plausibility": cred.breakdown.event_plausibility,
        }
        weakest = min(sub, key=sub.get)
        assert weakest in cred.notes


# --------------------------------------------------------------------------- #
# SYS-15 — copy-lint over all result text
# --------------------------------------------------------------------------- #
class TestProbabilisticCopySYS15:
    def _full_result(self, decision="Should I take the new job?"):
        sim_a = make_sim_flat("A", {"economic": 70, "career": 60, "relationships": 75,
                                    "mental_health": 68, "autonomy": 55})
        sim_b = make_sim_flat("B", {"economic": 50, "career": 82, "relationships": 60,
                                    "mental_health": 55, "autonomy": 85})
        world = make_world(decision=decision)
        weights = ValueWeights()
        scores = [score_branch(sim_a, weights), score_branch(sim_b, weights)]
        forks = detect_forks(sim_a, sim_b)
        cred = credibility(world, [sim_a, sim_b])
        rec = recommend(world, scores, forks, cred)
        return forks, cred, rec

    def test_no_deterministic_language_in_any_result_text(self):
        forks, cred, rec = self._full_result()
        violations = []
        for label, text in collect_nl_text(forks, cred, rec):
            for pat in DETERMINISTIC_PATTERNS:
                if pat.search(text):
                    violations.append((label, pat.pattern, text))
        assert not violations, f"SYS-15 FAIL — deterministic language: {violations}"

    def test_neither_leaning_text_is_probabilistic_and_clean(self):
        # Near-tied branches -> "neither"; rationale must stay probabilistic.
        sim_a = make_sim_flat("A", {d: 60.0 for d in DIMENSIONS})
        sim_b = make_sim_flat("B", {d: 61.0 for d in DIMENSIONS})
        world = make_world()
        scores = [score_branch(sim_a, ValueWeights()), score_branch(sim_b, ValueWeights())]
        cred = credibility(world, [sim_a, sim_b])
        rec = recommend(world, scores, detect_forks(sim_a, sim_b), cred)
        assert rec.leaning == "neither"
        for pat in DETERMINISTIC_PATTERNS:
            assert not pat.search(rec.rationale)

    def test_recommendation_rationale_uses_probabilistic_language(self):
        _, _, rec = self._full_result()
        assert any(p.search(rec.rationale) for p in PROBABILISTIC_PATTERNS), rec.rationale


# --------------------------------------------------------------------------- #
# SYS-16 — high-risk guardrails
# --------------------------------------------------------------------------- #
class TestGuardrailsSYS16:
    def _recommend_for(self, decision, dim_scores_b=None):
        dim_scores_b = dim_scores_b or {d: 60.0 for d in DIMENSIONS}
        sim_a = make_sim_flat("A", {d: 60.0 for d in DIMENSIONS})
        sim_b = make_sim_flat("B", dim_scores_b)
        world = make_world(decision=decision)
        scores = [score_branch(sim_a, ValueWeights()), score_branch(sim_b, ValueWeights())]
        cred = credibility(world, [sim_a, sim_b])
        return recommend(world, scores, detect_forks(sim_a, sim_b), cred)

    def test_guardrail_always_carries_simulation_and_change_affordance(self):
        rec = self._recommend_for("Should I repaint my living room?")
        g = rec.guardrail.lower()
        assert "simulation" in g and "not a prophecy" in g
        assert "change this outcome" in g

    def test_high_risk_decision_gets_extra_heads_up(self):
        rec = self._recommend_for("Should I end my 3-year relationship?")
        assert "high-stakes" in rec.guardrail.lower()

    def test_fragile_dimension_score_triggers_high_risk(self):
        # Benign decision text, but a collapsing relationships score is high-risk.
        rec = self._recommend_for(
            "Should I accept the transfer?",
            dim_scores_b={"economic": 60, "career": 60, "relationships": 20,
                          "mental_health": 60, "autonomy": 60},
        )
        assert "high-stakes" in rec.guardrail.lower()

    def test_benign_result_has_no_heads_up(self):
        rec = self._recommend_for("Should I repaint my living room?")
        assert "high-stakes" not in rec.guardrail.lower()


# --------------------------------------------------------------------------- #
# Orchestrator binds the real module (not the Wave-1 stub)
# --------------------------------------------------------------------------- #
class TestOrchestratorBinding:
    def test_orchestrator_uses_real_scoring(self):
        import importlib

        import app.orchestrator as orch
        importlib.reload(orch)  # re-run the _bind block now that scoring.py exists
        for fn in (orch.score_branch, orch.detect_forks, orch.credibility, orch.recommend):
            assert fn.__module__ == "app.scoring", (
                f"{fn.__name__} bound to {fn.__module__}, expected app.scoring"
            )
