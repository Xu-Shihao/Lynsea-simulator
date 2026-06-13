"""Bounded multi-agent interaction loop (Phase 4, MiroFish/OASIS-inspired).

These run entirely on the deterministic stub path (config.complete /
complete_json monkeypatched to None by the autouse conftest fixture), so
run_interaction must produce events from persona-trait-driven reactions, with
emergent conflict when two agents hold opposed stances (ALG-13). Every result
must be deterministic for a fixed seed and reference only real persona ids.
"""
from __future__ import annotations

from app.contracts import Big5, Persona
from app.engine.agents import InteractionResult, run_interaction
from app.engine.personas import build_personas


def _persona(pid, name, role, stance="unknown", concerns=None, beliefs=None):
    return Persona(
        id=pid,
        name=name,
        role=role,
        big5=Big5(O=5, C=5, E=5, A=5, N=5),
        decision_style="analytical",
        risk_tolerance=5.0,
        influence_weight=6.0,
        stance=stance,
        key_concerns=concerns or [],
        beliefs=beliefs or [],
    )


def test_run_interaction_returns_events_with_valid_personas():
    personas = build_personas(
        "relocate for partner", ["Move", "Stay"], ["my partner"], seed=1, mode="medium"
    )
    out = run_interaction(
        branch="A",
        option_text="Move",
        decision="relocate for partner",
        personas=personas,
        backbone=[],
        dimensions=[],
        seed=1,
        mode="medium",
    )
    assert isinstance(out, InteractionResult)
    assert out.events, "produced timeline events"
    ids = {p.id for p in personas}
    # Every interaction-origin event references only real persona ids.
    assert all(set(e.involved_personas) <= ids for e in out.events)
    # Event ids are unique.
    all_ids = [e.id for e in out.events]
    assert len(all_ids) == len(set(all_ids))
    # Events stay within the branch.
    assert all(e.branch == "A" for e in out.events)


def test_run_interaction_is_deterministic_for_seed():
    personas = build_personas(
        "take the startup offer", ["Take it", "Stay"], ["my spouse"], seed=7, mode="medium"
    )

    def go():
        return run_interaction(
            branch="B",
            option_text="Stay",
            decision="take the startup offer",
            personas=personas,
            backbone=[],
            dimensions=[],
            seed=7,
            mode="medium",
        )

    a = go()
    b = go()
    assert [e.model_dump() for e in a.events] == [e.model_dump() for e in b.events]


def test_emergent_conflict_for_opposed_stances():
    """Two agents with clashing stances produce an emergent conflict event that
    is traceable to both agents (ALG-13)."""
    personas = [
        _persona("p_user", "You", "self", stance="supportive",
                 concerns=["career growth"], beliefs=["this move is worth it"]),
        _persona("p_partner", "Partner", "partner", stance="opposed",
                 concerns=["staying near family"], beliefs=["we should not move"]),
    ]
    out = run_interaction(
        branch="A",
        option_text="Move across the country",
        decision="relocate for a new job",
        personas=personas,
        backbone=[],
        dimensions=[],
        seed=3,
        mode="medium",
    )
    conflict = [e for e in out.events if e.kind == "perturbation"
                and {"p_user", "p_partner"} <= set(e.involved_personas)]
    assert conflict, "an emergent conflict event references both opposed agents"
    # The conflict is memory-traceable: both agents recorded it in their streams.
    assert out.memories is not None
    for pid in ("p_user", "p_partner"):
        stream = out.memories[pid]
        texts = " ".join(it.text.lower() for it in stream.items)
        assert "conflict" in texts or "clash" in texts or "tension" in texts


def test_no_conflict_when_stances_aligned():
    personas = [
        _persona("p_user", "You", "self", stance="supportive"),
        _persona("p_friend", "Friend", "friend", stance="supportive"),
    ]
    out = run_interaction(
        branch="A",
        option_text="Take the trip",
        decision="plan a long trip together",
        personas=personas,
        backbone=[],
        dimensions=[],
        seed=2,
        mode="medium",
    )
    # Aligned stances => no two-agent emergent conflict event.
    multi_agent_conflict = [
        e for e in out.events
        if e.kind == "perturbation" and len(set(e.involved_personas)) >= 2
        and "conflict" in (e.title + e.description).lower()
    ]
    assert not multi_agent_conflict
