"""Orchestrator mode switch (Phase 6 / Task 10): Quick = single-pass,
Medium/Heavy = bounded multi-agent interaction (agents.run_interaction).

All on the deterministic stub path (autouse conftest fixture). These confirm the
agent path is actually wired through the orchestrator, that emergent conflict
surfaces end-to-end for opposed stances, and that the shared exogenous backbone
is still merged identically into both branches (ALG-20).
"""
from __future__ import annotations

import asyncio

from app.contracts import Big5, Persona, SimRequest
from app.engine import orchestrator
from app.engine import personas as personas_mod


def _collect_run(req: SimRequest):
    events: list = []

    async def emit(etype, payload):
        events.append((etype, payload))

    async def _go():
        return await orchestrator.run_simulation(req, emit, sim_id="t")

    result = asyncio.run(_go())
    return result, events


def _opposed_personas(*_a, **_k):
    return [
        Persona(id="p_user", name="You", role="self",
                big5=Big5(O=6, C=7, E=6, A=4, N=5), decision_style="analytical",
                risk_tolerance=6.0, influence_weight=8.0, stance="supportive",
                key_concerns=["career growth"], beliefs=["this move is worth it"]),
        Persona(id="p_partner", name="Partner", role="partner",
                big5=Big5(O=4, C=6, E=5, A=5, N=6), decision_style="cautious",
                risk_tolerance=3.0, influence_weight=7.0, stance="opposed",
                key_concerns=["staying near family"], beliefs=["we should not move"]),
    ]


def test_medium_mode_uses_agent_interaction_events():
    req = SimRequest(
        decision="Should I relocate for a new job?",
        options=["Relocate", "Stay"],
        affected_people=["my partner"],
        mode="medium",
    )
    result, events = _collect_run(req)
    te = [p for t, p in events if t == "timeline_event"]
    # Agent-origin events carry the interaction id marker.
    interaction = [p for p in te if "_int_" in p["id"]]
    assert interaction, "medium mode produced multi-agent interaction events"
    # The shared exogenous backbone is still merged into both branches (ALG-20).
    exo_branches = {p["branch"] for p in te if p["kind"] == "exogenous"}
    assert exo_branches == {"A", "B"}
    # Dimensions emitted, metrics produced, run completes.
    assert any(t == "dimensions" for t, _ in events)
    assert any(t == "metric" for t, _ in events)
    assert any(t == "done" for t, _ in events)


def test_medium_mode_emergent_conflict_end_to_end(monkeypatch):
    monkeypatch.setattr(personas_mod, "build_personas", _opposed_personas)
    req = SimRequest(
        decision="Should I relocate for a new job?",
        options=["Relocate", "Stay"],
        affected_people=["my partner"],
        mode="medium",
    )
    result, events = _collect_run(req)
    te = [p for t, p in events if t == "timeline_event"]
    conflict = [
        p for p in te
        if p["kind"] == "perturbation"
        and {"p_user", "p_partner"} <= set(p["involved_personas"])
    ]
    assert conflict, "opposed stances produce an emergent conflict event end-to-end"


def test_quick_mode_uses_single_pass(monkeypatch):
    # Quick must NOT route through the agent loop: spy that run_interaction is
    # never called.
    from app.engine import agents as agents_mod

    called = {"n": 0}
    orig = agents_mod.run_interaction

    def _spy(*a, **k):
        called["n"] += 1
        return orig(*a, **k)

    monkeypatch.setattr(agents_mod, "run_interaction", _spy)
    monkeypatch.setattr(orchestrator.agents_mod, "run_interaction", _spy)

    req = SimRequest(
        decision="Should I switch teams?",
        options=["Switch", "Stay"],
        mode="quick",
    )
    _collect_run(req)
    assert called["n"] == 0, "quick mode must not invoke the agent interaction loop"
