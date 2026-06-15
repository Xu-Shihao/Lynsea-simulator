"""BE-Twin acceptance tests for ``app.personas.build_world`` (ALG-01/02/03/04).

These run WITHOUT a live model key: ``app.llm`` degrades, so Big-Five inference
falls through to the deterministic heuristic. That is intentional — the world
must boot and stay schema-valid even when the LLM is unavailable (`BE-12`).

Covered:
* ALG-01 — a 5–7-field request boots a full World (user + 3–5 personas).
* ALG-02 — Big Five inferred from behaviour; every trait has a rationale; the
  scores are NOT the user-entered risk number.
* ALG-03 — every persona validates against the ``Persona`` schema.
* ALG-04 — low-info personas tagged confidence="low" + cold_start + a
  human-readable "信息有限 / limited info" note.
"""

from __future__ import annotations

import pytest

from app.personas import (
    BIG_FIVE_TRAITS,
    COLD_START_NOTE,
    build_world,
)
from app.schemas import (
    Persona,
    ProfileInput,
    SimulateRequest,
    SocialCircleMember,
    World,
)


class _RNG:
    """Minimal SeededRNG stand-in (build_world only reads ``.seed``)."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def full_request() -> SimulateRequest:
    """A well-specified request (well over the 5–7 field minimum)."""
    return SimulateRequest(
        decision="Should I quit my job to join an early-stage startup?",
        mode="quick",
        profile=ProfileInput(
            age=29,
            city="Shanghai",
            occupation="product manager",
            risk_tolerance=7,
            core_values=["growth", "stability", "family"],
            decision_style="analytic",
        ),
        social_circle=[
            SocialCircleMember(
                role="partner",
                influence_weight=9,
                stance_on_decision="worried about losing stable income",
                key_concerns=["financial security", "stress"],
            ),
            SocialCircleMember(
                role="mentor",
                influence_weight=6,
                stance_on_decision="supportive of taking the leap",
                key_concerns=["career growth"],
            ),
        ],
        seed=42,
    )


@pytest.fixture
def minimal_request() -> SimulateRequest:
    """The smallest legal request: a bare decision (cold start everywhere)."""
    return SimulateRequest(decision="Should I move abroad for a new role?")


# --------------------------------------------------------------------------- #
# ALG-01 — min info set boots a full world
# --------------------------------------------------------------------------- #
def test_alg01_minimal_request_boots_full_world(minimal_request):
    world = build_world(minimal_request, _RNG())
    assert isinstance(world, World)
    assert 3 <= len(world.personas) <= 5
    assert set(world.options.keys()) == {"A", "B"}
    assert world.options["A"] != world.options["B"]
    # The decision-maker is always present.
    assert any(p.id == "self" for p in world.personas)


def test_alg01_five_to_seven_fields_boots_full_world(full_request):
    world = build_world(full_request, _RNG())
    assert 3 <= len(world.personas) <= 5
    roles = {p.role for p in world.personas}
    assert "you" in roles
    assert "partner" in roles and "mentor" in roles


def test_alg01_personas_capped_at_five():
    req = SimulateRequest(
        decision="Big decision",
        social_circle=[
            SocialCircleMember(role=f"friend{i}", stance_on_decision="ok")
            for i in range(8)
        ],
    )
    world = build_world(req, _RNG())
    assert len(world.personas) <= 5


# --------------------------------------------------------------------------- #
# ALG-02 — Big Five inferred from behaviour, with a rationale per trait
# --------------------------------------------------------------------------- #
def test_alg02_big_five_present_for_every_persona(full_request):
    world = build_world(full_request, _RNG())
    for p in world.personas:
        assert set(p.big_five.keys()) == set(BIG_FIVE_TRAITS)
        for trait, score in p.big_five.items():
            assert 0.0 <= score <= 1.0, f"{trait} out of range"


def test_alg02_each_trait_has_a_rationale(full_request):
    world = build_world(full_request, _RNG())
    for p in world.personas:
        rationale = getattr(p, "big_five_rationale", None)
        assert isinstance(rationale, dict)
        assert set(rationale.keys()) == set(BIG_FIVE_TRAITS)
        for trait, why in rationale.items():
            assert isinstance(why, str) and why.strip(), f"empty rationale for {trait}"


def test_alg02_scores_are_inferred_not_user_numbers(full_request):
    """Big Five must come from behaviour, never the user's risk_tolerance=7."""
    world = build_world(full_request, _RNG())
    me = next(p for p in world.personas if p.id == "self")
    # 7/10 = 0.7 entered as risk; assert OCEAN is not just that literal value.
    assert me.big_five != {t: 0.7 for t in BIG_FIVE_TRAITS}
    # Higher risk tolerance should push openness above the neutral midpoint.
    assert me.big_five["openness"] > 0.5


def test_alg02_behaviour_changes_inferred_traits():
    """Different behavioural descriptions yield different inferred traits."""
    cautious = SimulateRequest(
        decision="Should I change careers?",
        profile=ProfileInput(risk_tolerance=1, decision_style="cautious"),
    )
    bold = SimulateRequest(
        decision="Should I change careers?",
        profile=ProfileInput(risk_tolerance=9, decision_style="spontaneous"),
    )
    w_cautious = build_world(cautious, _RNG())
    w_bold = build_world(bold, _RNG())
    me_c = next(p for p in w_cautious.personas if p.id == "self")
    me_b = next(p for p in w_bold.personas if p.id == "self")
    # Bolder behaviour -> higher openness, lower neuroticism than cautious.
    assert me_b.big_five["openness"] > me_c.big_five["openness"]
    assert me_b.big_five["neuroticism"] < me_c.big_five["neuroticism"]


# --------------------------------------------------------------------------- #
# ALG-03 — every persona validates against the schema
# --------------------------------------------------------------------------- #
def test_alg03_personas_validate_against_schema(full_request):
    world = build_world(full_request, _RNG())
    for p in world.personas:
        # Round-trips through the wire shape without loss / extra fields.
        revalidated = Persona.model_validate(p.model_dump())
        assert revalidated.id == p.id
        assert 0 <= revalidated.influence_weight <= 10
        assert revalidated.confidence in ("high", "low")
        # public() view must expose exactly the world_ready subset.
        # ALG-04 / FE-23: PersonaPublic now also carries the optional, back-
        # compatible cold-start flag + bilingual "信息有限 / limited info" note.
        pub = p.public()
        assert pub.model_dump().keys() == {
            "id",
            "role",
            "influence_weight",
            "confidence",
            "cold_start",
            "note",
        }


def test_alg03_belief_data_is_off_the_wire_shape(full_request):
    """UserHarness belief data is attached as live attrs, not wire fields."""
    world = build_world(full_request, _RNG())
    me = next(p for p in world.personas if p.id == "self")
    # Beliefs are reachable for BE-Sim ...
    beliefs = getattr(me, "beliefs")
    assert "belief" in beliefs and "about_others" in beliefs["belief"]
    # ... but never leak into the serialized persona.
    assert "beliefs" not in me.model_dump()
    assert "big_five_rationale" not in me.model_dump()


def test_userharness_nested_beliefs_present(full_request):
    """Self holds nested beliefs about others -> enables emergent conflict."""
    world = build_world(full_request, _RNG())
    me = next(p for p in world.personas if p.id == "self")
    nested = me.beliefs["belief"]["about_others"]
    assert "partner" in nested
    assert "i_think_they_want" in nested["partner"]


# --------------------------------------------------------------------------- #
# ALG-04 — cold start tagging
# --------------------------------------------------------------------------- #
def test_alg04_minimal_request_personas_are_low_confidence(minimal_request):
    world = build_world(minimal_request, _RNG())
    for p in world.personas:
        assert p.confidence == "low"
        assert p.cold_start is True
        assert getattr(p, "cold_start_note") == COLD_START_NOTE


def test_alg04_note_is_human_readable_bilingual(minimal_request):
    world = build_world(minimal_request, _RNG())
    note = getattr(world.personas[0], "cold_start_note")
    assert "信息有限" in note
    assert "limited info" in note


def test_alg04_stated_members_are_high_confidence_not_cold_start(full_request):
    world = build_world(full_request, _RNG())
    partner = next(p for p in world.personas if p.role == "partner")
    assert partner.confidence == "high"
    assert partner.cold_start is False


def test_alg04_member_without_stance_is_cold_start():
    req = SimulateRequest(
        decision="Should I take the promotion?",
        social_circle=[SocialCircleMember(role="colleague", influence_weight=4)],
    )
    world = build_world(req, _RNG())
    colleague = next(p for p in world.personas if p.role == "colleague")
    assert colleague.confidence == "low"
    assert colleague.cold_start is True


# --------------------------------------------------------------------------- #
# Determinism / interface conformance
# --------------------------------------------------------------------------- #
def test_build_world_is_deterministic(full_request):
    a = build_world(full_request, _RNG(7))
    b = build_world(full_request, _RNG(7))
    assert [p.model_dump() for p in a.personas] == [p.model_dump() for p in b.personas]
    assert a.options == b.options


def test_build_world_matches_interface_signature(full_request):
    import inspect

    # BuildWorld is a (non-runtime-checkable) Protocol; assert the structural
    # contract instead: callable with (req, rng) -> World.
    assert callable(build_world)
    params = list(inspect.signature(build_world).parameters)
    assert params[:2] == ["req", "rng"]
    world = build_world(full_request, _RNG())
    assert isinstance(world, World)
