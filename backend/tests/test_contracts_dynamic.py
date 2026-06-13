"""Phase 1: dynamic-dimension + clarification contract models."""
from __future__ import annotations

import pytest

from app.contracts import (
    DEFAULT_DIMENSIONS,
    BranchPoint,
    ClarificationPlan,
    Dimension,
    MetricPoint,
    Persona,
    SimResult,
)


def test_dimension_model():
    d = Dimension(
        id="economic",
        label="Economic",
        description="money & security",
        polarity="higher_is_better",
    )
    assert d.polarity == "higher_is_better"


def test_dimension_polarity_coerced():
    d = Dimension(id="stress", label="Stress", description="", polarity="bogus")
    assert d.polarity == "higher_is_better"  # invalid coerced to default


def test_metricpoint_scores_map():
    mp = MetricPoint(
        branch="A",
        month=1,
        scores={"economic": 60.0, "career": 55.0},
        supporting_event_ids=["ev_A_00"],
    )
    assert mp.scores["economic"] == 60.0 and mp.supporting_event_ids


def test_metricpoint_score_out_of_range_rejected():
    with pytest.raises(Exception):
        MetricPoint(branch="A", month=1, scores={"economic": 140.0})


def test_branchpoint_uses_dimension():
    bp = BranchPoint(
        month=3,
        dimension="mental",
        magnitude=12.0,
        description="diverges",
        cause_chain="...",
    )
    assert bp.dimension == "mental"


def test_clarification_plan():
    cp = ClarificationPlan(
        suggested_options=["A", "B"],
        affected_people=[{"name": "partner", "role": "partner", "suggested_stance": "unknown"}],
        key_factors=["stress"],
        value_prompts=[{"dim_hint": "mental", "question": "How much does wellbeing matter?"}],
        constraints=["mortgage"],
        followup_questions=["Does your partner know?"],
    )
    assert cp.suggested_options == ["A", "B"]
    assert cp.affected_people[0].role == "partner"
    assert cp.value_prompts[0].dim_hint == "mental"


def test_default_dimensions():
    assert len(DEFAULT_DIMENSIONS) == 5
    ids = [d.id for d in DEFAULT_DIMENSIONS]
    assert len(set(ids)) == len(ids)
    assert set(ids) == {"economic", "career", "relationship", "mental", "autonomy"}
    assert all(d.polarity == "higher_is_better" for d in DEFAULT_DIMENSIONS)


def test_persona_beliefs_and_tom():
    p = Persona(
        id="p_user",
        name="You",
        role="self",
        big5={"O": 5, "C": 5, "E": 5, "A": 5, "N": 5},
        decision_style="analytical",
        risk_tolerance=5,
        influence_weight=8,
        beliefs=["work matters"],
        theory_of_mind={"p_partner": "wants stability"},
    )
    assert p.beliefs == ["work matters"]
    assert p.theory_of_mind["p_partner"] == "wants stability"


def test_simresult_dimensions_default_empty():
    r = SimResult(
        sim_id="x",
        decision="d",
        options=["A", "B"],
        mode="quick",
        seed=1,
        created_at="now",
    )
    assert r.dimensions == []
