"""BE-Sim unit tests: memory stream + multi-agent social simulation.

Covers the acceptance gates owned by BE-Sim (BUILD_PLAN §4, issue LIN-52):

* ALG-10 — retrieval ordered by recency × importance × relevance.
* ALG-11 — reflection fires at the cumulative-importance threshold and writes
  traceable higher-level beliefs.
* ALG-12 — persona consistency self-check ≥ 4/5 (structural, offline).
* ALG-13 — interpersonal conflict emerges from mutual mis-judgement.
* ALG-14 — every judgement / conflict is traceable to a memory entry.
* ALG-15 — tiered, event-driven activation budget (core 3–5/mo, minor 1–2/mo).

All tests run offline (no API key): the simulation's deterministic core is
LLM-free and the optional Haiku enrichment degrades to a no-op.
"""

from __future__ import annotations

import asyncio
import os
import sys

# Put backend/ on the import path regardless of pytest's rootdir/invocation cwd.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.memory_store import (  # noqa: E402
    DEFAULT_REFLECTION_THRESHOLD,
    MemoryStream,
    cosine_similarity,
    hashing_embedding,
)
from app.rng import SeededRNG  # noqa: E402
from app.schemas import DIMENSIONS, Persona, ValueWeights, World  # noqa: E402
from app.simulation import (  # noqa: E402
    MODE_HORIZON,
    PersonaAgent,
    SocialSimulation,
    consistency_probe,
    persona_consistency_score,
    run_simulation,
)


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #
def _persona(
    pid, role, influence, stance, big_five, *, key_concerns=None, beliefs=None
):
    p = Persona(
        id=pid,
        role=role,
        influence_weight=influence,
        confidence="high",
        stance_on_decision=stance,
        key_concerns=key_concerns or [],
        big_five=big_five,
        cold_start=False,
    )
    if beliefs is not None:
        # personas.py attaches the UserHarness mind model as a live attribute.
        object.__setattr__(p, "beliefs", beliefs)
    return p


_OPTIMIST = {"openness": 0.8, "conscientiousness": 0.5, "extraversion": 0.7,
             "agreeableness": 0.6, "neuroticism": 0.2}
_ANXIOUS_LOW_AGREE = {"openness": 0.3, "conscientiousness": 0.6, "extraversion": 0.4,
                      "agreeableness": 0.2, "neuroticism": 0.8}
_NEUTRAL = {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
            "agreeableness": 0.5, "neuroticism": 0.5}


def _divergent_world():
    """A world primed for emergent conflict: a pro 'self' vs an anxious, opposed,
    low-agreeableness high-influence parent (poor theory-of-mind -> mis-judges)."""
    personas = [
        _persona(
            "self", "you", 10, "excited — I want to go for it", _OPTIMIST,
            key_concerns=["growth", "freedom"],
            beliefs={"belief": {"about_others": {
                "parent": {"i_think_they_want": "they'll be supportive"}}}},
        ),
        _persona(
            "parent", "parent", 9, "I'm worried, I think they should stay put",
            _ANXIOUS_LOW_AGREE, key_concerns=["stability", "security"],
            beliefs={"belief": {"about_them": {"i_think_they_should": "stay put"}}},
        ),
        _persona("friend", "close friend", 4, None, _NEUTRAL, key_concerns=["balance"]),
    ]
    return World(
        run_id="test-run", decision="quit my job to start a company", mode="quick",
        seed=4242, options={"A": "Keep the job", "B": "Start the company"},
        personas=personas, values=ValueWeights(),
    )


def _events_for(world, branch):
    from app.events import generate_events

    return generate_events(world, branch, SeededRNG(world.seed))


# --------------------------------------------------------------------------- #
# ALG-10: retrieval ordering
# --------------------------------------------------------------------------- #
def test_alg10_retrieval_orders_by_recency_importance_relevance():
    ms = MemoryStream("self")
    e_best = ms.add("partner relationship love marriage trust", 9.0, timestamp=5)
    e_old_irrelevant = ms.add("mortgage budget interest rate tax filing", 2.0, timestamp=0)
    e_relevant_mid = ms.add("partner relationship feelings", 5.0, timestamp=1)
    e_career = ms.add("career promotion office project deadline", 6.0, timestamp=4)

    ranked = ms.retrieve("how does my partner feel in our relationship", now=5, k=4)
    assert ranked, "retrieval returned nothing"
    # The recent, important, highly-relevant memory must rank first.
    assert ranked[0].id == e_best.id
    # The old, low-importance, irrelevant memory must not rank first.
    assert ranked[0].id != e_old_irrelevant.id
    order = [m.id for m in ranked]
    assert order.index(e_relevant_mid.id) < order.index(e_old_irrelevant.id)
    assert e_career.id in order

    # Deterministic: identical query -> identical ranking.
    assert [m.id for m in ms.retrieve("partner relationship", now=5, k=4)] == [
        m.id for m in ms.retrieve("partner relationship", now=5, k=4)
    ]
    # k is honored.
    assert len(ms.retrieve("partner", now=5, k=2)) == 2


def test_alg10_recency_breaks_ties():
    ms = MemoryStream("self")
    old = ms.add("identical content token alpha", 5.0, timestamp=0)
    new = ms.add("identical content token alpha", 5.0, timestamp=5)
    ranked = ms.retrieve("identical content token alpha", now=5, k=2)
    assert ranked[0].id == new.id and ranked[1].id == old.id


def test_hashing_embedding_is_deterministic_and_offline():
    a = hashing_embedding("partner relationship")
    b = hashing_embedding("partner relationship")
    assert a == b
    # Related text is more similar than unrelated text.
    rel = cosine_similarity(a, hashing_embedding("relationship with my partner"))
    unrel = cosine_similarity(a, hashing_embedding("mortgage interest tax"))
    assert rel > unrel


# --------------------------------------------------------------------------- #
# ALG-11: reflection at threshold
# --------------------------------------------------------------------------- #
def test_alg11_reflection_fires_at_threshold():
    ms = MemoryStream("self")
    assert not ms.should_reflect()
    # 20 observations x importance 8 = 160 >= 150 threshold.
    ids = [ms.add(f"recurring worry about money month {i}", 8.0, timestamp=i).id
           for i in range(20)]
    assert ms.cumulative_importance >= DEFAULT_REFLECTION_THRESHOLD
    assert ms.should_reflect()

    new = ms.reflect(now=20)
    assert new, "reflection produced no higher-level belief"
    for r in new:
        assert r.kind == "reflection"
        assert r.importance >= 7.0
        # Reflection tree + ALG-14 traceability: sources are real prior memories.
        assert r.source_ids and set(r.source_ids).issubset(set(ids))
    # Budget resets; reflection does not retrigger itself.
    assert ms.cumulative_importance == 0.0
    assert not ms.should_reflect()
    # The new belief is retrievable.
    hits = ms.retrieve("money worry pattern", now=20, k=5, kinds=["reflection"])
    assert any(h.id == new[0].id for h in hits)


def test_alg11_below_threshold_does_not_reflect():
    ms = MemoryStream("self")
    for i in range(5):
        ms.add("minor note", 5.0, timestamp=i)
    assert ms.cumulative_importance == 25.0
    assert not ms.should_reflect()


def test_alg11_custom_synthesizer_is_used():
    ms = MemoryStream("self")
    for i in range(20):
        ms.add(f"event {i}", 8.0, timestamp=i)
    new = ms.reflect(now=20, synthesizer=lambda contents: ["SYNTH belief"])
    assert len(new) == 1 and new[0].content == "SYNTH belief"


# --------------------------------------------------------------------------- #
# ALG-12: persona consistency
# --------------------------------------------------------------------------- #
def test_alg12_persona_consistency_no_drift():
    world = _divergent_world()
    sim = SocialSimulation(world, "B", _events_for(world, "B"), SeededRNG(world.seed))
    sim.run()
    for agent in sim.agents.values():
        score = persona_consistency_score(agent)
        assert score >= 4.0, f"{agent.id} drifted: {score}/5"
        baseline = consistency_probe(agent, branch="B", month=0)
        final = agent.consistency_snapshots[sim.horizon]
        # Core values + risk preference never flip direction (grounded).
        assert baseline["value_priority"] == final["value_priority"]
        assert baseline["risk_preference"] == final["risk_preference"]


# --------------------------------------------------------------------------- #
# ALG-13 / ALG-14: emergent, traceable conflict
# --------------------------------------------------------------------------- #
def test_alg13_conflict_emerges_from_misjudgement():
    world = _divergent_world()
    sim = SocialSimulation(world, "B", _events_for(world, "B"), SeededRNG(world.seed))
    sim.run()
    assert sim.conflicts, "no conflict emerged between divergent personas"
    # Every conflict is *derived* from real divergence + mis-judgement, not narrated.
    for c in sim.conflicts:
        assert c.divergence > 0.0 and c.misjudgement > 0.0
        assert c.magnitude > 0.0
        assert c.evidence_belief_ids, "conflict not traceable to belief entries"
    # The pro-self vs opposed-parent pair is among the conflicts.
    pairs = {frozenset((c.persona_a, c.persona_b)) for c in sim.conflicts}
    assert frozenset(("self", "parent")) in pairs


def test_alg14_every_judgement_traces_to_memory():
    world = _divergent_world()
    sim = SocialSimulation(world, "B", _events_for(world, "B"), SeededRNG(world.seed))
    sim.run()
    assert sim.judgement_trace
    # 100% of judgements locate to >=1 memory/belief entry.
    for j in sim.judgement_trace:
        assert j.memory_ids, f"judgement by {j.persona} about {j.about} has no source"
        # Referenced ids exist in that persona's stream.
        stream_ids = {m.id for m in sim.agents[j.persona].memory.entries}
        assert set(j.memory_ids).issubset(stream_ids)


# --------------------------------------------------------------------------- #
# ALG-15: tiered, event-driven activation budget
# --------------------------------------------------------------------------- #
def test_alg15_tiered_activation_budget():
    world = _divergent_world()
    sim = SocialSimulation(world, "B", _events_for(world, "B"), SeededRNG(world.seed))
    sim.run()
    assert sim.activation_log
    saw_core = False
    for (pid, _month), count in sim.activation_log.items():
        agent = sim.agents[pid]
        if agent.is_core:
            saw_core = True
            assert 3 <= count <= 5, f"core {pid} activated {count}x (want 3-5)"
        else:
            assert 1 <= count <= 2, f"minor {pid} activated {count}x (want 1-2)"
    assert saw_core
    # Event-driven: the minor 'friend' only logs activations in months it has an event.
    friend_events = {e.month for e in sim.events if "friend" in (e.personas or [])}
    friend_months = {m for (pid, m) in sim.activation_log if pid == "friend"}
    assert friend_months.issubset(friend_events)


# --------------------------------------------------------------------------- #
# run_simulation contract + determinism + ALG-40 evidence
# --------------------------------------------------------------------------- #
def test_run_simulation_contract_and_evidence():
    world = _divergent_world()
    events = _events_for(world, "B")
    result = asyncio.run(run_simulation(world, "B", events, SeededRNG(world.seed)))

    assert result.branch == "B"
    horizon = MODE_HORIZON["quick"]
    assert len(result.metrics) == 5 * horizon
    event_ids = {e.event_id for e in events}
    seen_dims = set()
    for m in result.metrics:
        assert m.dim in DIMENSIONS
        assert 0.0 <= m.score <= 100.0
        assert 1 <= m.month <= horizon
        # ALG-40: every metric references >= 1 real evidence event.
        assert m.evidence_event_ids
        assert set(m.evidence_event_ids).issubset(event_ids)
        seen_dims.add(m.dim)
    assert seen_dims == set(DIMENSIONS)


def test_run_simulation_is_deterministic():
    world = _divergent_world()
    events = _events_for(world, "B")
    a = asyncio.run(run_simulation(world, "B", events, SeededRNG(world.seed)))
    b = asyncio.run(run_simulation(world, "B", events, SeededRNG(world.seed)))
    assert [(m.month, m.dim, m.score) for m in a.metrics] == [
        (m.month, m.dim, m.score) for m in b.metrics
    ]


def test_branches_diverge():
    """The decision variable should pull the two branches apart (a fork exists)."""
    world = _divergent_world()
    a = asyncio.run(run_simulation(world, "A", _events_for(world, "A"), SeededRNG(world.seed)))
    b = asyncio.run(run_simulation(world, "B", _events_for(world, "B"), SeededRNG(world.seed)))

    def final_by_dim(res):
        h = MODE_HORIZON["quick"]
        return {m.dim: m.score for m in res.metrics if m.month == h}

    fa, fb = final_by_dim(a), final_by_dim(b)
    total_gap = sum(abs(fa[d] - fb[d]) for d in DIMENSIONS)
    assert total_gap > 10.0, f"branches barely diverge (gap={total_gap})"


def test_personaagent_grounding_is_stable():
    world = _divergent_world()
    self_p = world.personas[0]
    agent = PersonaAgent(self_p)
    grounding_before = dict(agent.baseline)
    # Simulating should never mutate the immutable grounding.
    sim = SocialSimulation(world, "B", _events_for(world, "B"), SeededRNG(world.seed))
    sim.run()
    agent2 = sim.agents["self"]
    assert agent2.baseline["change_valence"] == grounding_before["change_valence"]
    assert agent2.baseline["top_value"] == grounding_before["top_value"]
