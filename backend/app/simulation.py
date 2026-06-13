"""Belief-driven multi-agent social simulation (owner: BE-Sim).

Owner file (BUILD_PLAN §4): ``backend/app/simulation.py``. Implements the §5
interface ``run_simulation(world, branch, events, rng) -> SimResult``; the
orchestrator auto-binds this module (no edit to ``orchestrator.py`` required).

What this module does
---------------------
For one counterfactual branch it runs a small society of :class:`PersonaAgent`
forward over the mode horizon and emits the 5-dimension :class:`Metric` curves.
Each persona is a UserHarness mind (Environment → Observation → **Belief** →
Goal → Action) backed by an EverOS-style :class:`~app.memory_store.MemoryStream`.

Acceptance IDs satisfied here
-----------------------------
* **ALG-10** — every judgement is formed by *retrieving* from the persona's
  memory stream (recency × importance × relevance).
* **ALG-11** — agents reflect into higher-level beliefs once accumulated
  importance crosses the threshold (delegated to ``MemoryStream.reflect``).
* **ALG-12** — persona grounding (immutable baseline OCEAN + values + risk) is
  re-injected on *every* belief formation, so a persona does not drift across
  months 0/6/12; :func:`persona_consistency_score` self-tests this (≥4/5).
* **ALG-13** — interpersonal conflict is **emergent**: it is *computed* from the
  divergence between what persona X believes persona Y wants and what Y actually
  wants (mutual mis-judgement), never narrated by a single model. See
  :class:`Conflict`.
* **ALG-14** — every judgement and every conflict records the memory/belief
  entry ids it was derived from (``judgement_trace`` / ``Conflict.evidence_*``),
  so any emitted effect is traceable to a concrete memory.
* **ALG-15** — LLM/agent activations are tiered and **event-driven**: core
  personas act 3–5×/month, minor personas 1–2×/month (and only when an event
  touches them). The schedule is recorded in ``activation_log`` for cost audit.

Determinism & cost
------------------
The metric numbers, conflicts and activation schedule are computed by a fully
deterministic, LLM-free core (seeded only via ``rng.branch_rng(branch)``), so
the result is reproducible (NFR-01-friendly) and runs offline with no API key.
``run_simulation`` then performs an **optional, bounded** ``app.llm`` (Haiku)
enrichment pass that rewrites a few belief/reflection strings into nicer prose —
it never changes a metric value and degrades to a no-op without a key.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from app.llm import DEGRADED_DEFAULT, llm
from app.memory_store import MemoryEntry, MemoryStream
from app.schemas import DIMENSIONS, Metric, SimResult, TimelineEvent, World

logger = logging.getLogger("lynsea.simulation")

# Horizon (months) per mode. Mirrors orchestrator/events MODE_HORIZON but is
# defined locally to avoid importing the orchestrator (which imports this).
MODE_HORIZON: dict[str, int] = {"quick": 6, "medium": 18, "heavy": 24}

# Tiered activation budget per persona per month (ALG-15).
CORE_MIN_ACTS, CORE_MAX_ACTS = 3, 5
MINOR_MIN_ACTS, MINOR_MAX_ACTS = 1, 2
# A persona is "core" if it is the decision-maker or highly influential.
CORE_INFLUENCE_THRESHOLD = 7

# Emergent-conflict thresholds (ALG-13): a conflict requires both that the two
# personas actually want different things AND that at least one mis-reads the
# other. Values are on the normalised [0, 1] scale used below.
CONFLICT_DIVERGENCE_THRESHOLD = 0.30
CONFLICT_MISJUDGEMENT_THRESHOLD = 0.22

# Hard cap on live Haiku enrichment calls per branch (latency/cost guard for
# quick mode). The full tiered schedule still drives ``activation_log``.
MAX_ENRICH_CALLS_PER_BRANCH = 16


# --------------------------------------------------------------------------- #
# Stance / event valence lexicons
# --------------------------------------------------------------------------- #
_POSITIVE_STANCE = (
    "support", "encourage", "yes", "go for it", "in favor", "in favour", "pro-",
    "agree", "excited", "should do", "do it", "go ahead", "behind",
)
_NEGATIVE_STANCE = (
    "oppose", "against", "no ", "worried", "concern", "risky", "hesitant",
    "reluctant", "don't", "do not", "shouldn't", "should not", "stay put",
    "afraid", "scared", "resist",
)

# Title-keyword -> exogenous valence in [-1, 1] for perturbation events. Keyed on
# substrings of the BE-Engine perturbation titles (see app/events.py).
_PERTURBATION_VALENCE: dict[str, float] = {
    "health scare": -0.45,
    "windfall": 0.45,
    "job market": -0.10,
    "relocate": -0.20,
    "new connection": 0.35,
    "unexpected expense": -0.50,
    "family news": -0.15,
    "workload spike": -0.25,
    "setback": -0.40,
    "recognition": 0.50,
    "uneventful": 0.0,
    "quieter": 0.0,
}

# Which dimension(s) a perturbation keyword nudges, and by how much (points).
_PERTURBATION_DIM_EFFECT: dict[str, dict[str, float]] = {
    "health scare": {"mental_health": -9.0},
    "windfall": {"economic": 7.0},
    "job market": {"career": -4.0, "economic": -3.0},
    "relocate": {"autonomy": -5.0, "relationships": -4.0},
    "new connection": {"career": 5.0, "relationships": 3.0},
    "unexpected expense": {"economic": -9.0, "mental_health": -3.0},
    "family news": {"relationships": -6.0, "mental_health": -3.0},
    "workload spike": {"career": 4.0, "mental_health": -6.0},
    "setback": {"career": -6.0, "mental_health": -4.0},
    "recognition": {"career": 7.0, "mental_health": 3.0},
}

_VALUE_MAP = {
    "growth": "career", "career": "career", "ambition": "career",
    "stability": "economic", "money": "economic", "income": "economic",
    "financial": "economic", "wealth": "economic", "security": "economic",
    "family": "relationships", "relationship": "relationships",
    "relationships": "relationships", "love": "relationships",
    "friends": "relationships", "community": "relationships",
    "health": "mental_health", "wellbeing": "mental_health",
    "well-being": "mental_health", "balance": "mental_health",
    "peace": "mental_health", "happiness": "mental_health",
    "freedom": "autonomy", "independence": "autonomy", "autonomy": "autonomy",
}


# --------------------------------------------------------------------------- #
# Data classes
# --------------------------------------------------------------------------- #
@dataclass
class Conflict:
    """An emergent interpersonal conflict for one month (ALG-13 / ALG-14).

    ``divergence`` (how differently the two personas actually feel about the
    decision) and ``misjudgement`` (how wrongly at least one models the other)
    are both > 0 by construction — the conflict is *derived* from them, not
    narrated. ``evidence_belief_ids`` / ``evidence_event_ids`` make it traceable.
    """

    month: int
    persona_a: str
    persona_b: str
    magnitude: float  # 0..1 (influence-weighted)
    divergence: float  # 0..1
    misjudgement: float  # 0..1
    evidence_belief_ids: list[str] = field(default_factory=list)
    evidence_event_ids: list[str] = field(default_factory=list)


@dataclass
class Judgement:
    """A single belief-forming activation, traceable to its source memories."""

    month: int
    persona: str
    about: str  # "self" or another persona id
    statement: str
    valence: float
    memory_ids: list[str] = field(default_factory=list)
    event_ids: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Persona agent
# --------------------------------------------------------------------------- #
class PersonaAgent:
    """A UserHarness mind: immutable grounding + a live memory stream.

    The ``baseline`` dict is the *grounding* re-injected on every belief
    formation (ALG-12). It is derived once from the persona's inferred OCEAN,
    stated stance, key concerns and (for the decision-maker) risk signals, and is
    never mutated by the simulation — that is what prevents long-horizon drift.
    """

    def __init__(self, persona: Any, *, embedder=None) -> None:
        self.persona = persona
        self.id: str = persona.id
        self.role: str = persona.role
        self.influence: int = int(getattr(persona, "influence_weight", 5))
        self.is_core = self.id == "self" or self.influence >= CORE_INFLUENCE_THRESHOLD

        ocean = dict(getattr(persona, "big_five", {}) or {})
        o = float(ocean.get("openness", 0.5))
        c = float(ocean.get("conscientiousness", 0.5))
        e = float(ocean.get("extraversion", 0.5))
        a = float(ocean.get("agreeableness", 0.5))
        n = float(ocean.get("neuroticism", 0.5))

        risk = _clamp01(0.5 * o + 0.5 * (1.0 - n))
        stance_valence = _stance_to_valence(getattr(persona, "stance_on_decision", None))
        # Disposition toward "making the change" (branch B), grounded in stance +
        # behaviour. Stable across the whole run.
        change_valence = _clamp(
            0.6 * stance_valence + 0.4 * ((o - 0.5) + (0.5 - n) + 0.5 * (risk - 0.5)),
            -1.0,
            1.0,
        )
        optimism = _clamp(1.2 * (0.5 - n) + 0.5 * (o - 0.5), -1.0, 1.0)
        tom_accuracy = _clamp01(0.3 + 0.6 * a - 0.2 * n)

        self.baseline: dict[str, Any] = {
            "ocean": {"openness": o, "conscientiousness": c, "extraversion": e,
                      "agreeableness": a, "neuroticism": n},
            "risk": risk,
            "change_valence": change_valence,
            "optimism": optimism,
            "tom_accuracy": tom_accuracy,
            "ambition": _clamp01((o + (1.0 - n) + risk) / 3.0),
            "top_value": _top_value(getattr(persona, "key_concerns", []) or []),
        }
        self.memory = MemoryStream(owner_id=self.id, embedder=embedder)
        # month -> self valence cache; populated as the sim advances.
        self.valence_by_month: dict[int, float] = {}
        self.consistency_snapshots: dict[int, dict[str, str]] = {}
        self.reflections: list[MemoryEntry] = []

    # -- grounded valence ------------------------------------------------- #
    def event_response(self, event: TimelineEvent) -> float:
        """How this persona reads one event, coloured by personality (grounded)."""
        n = self.baseline["ocean"]["neuroticism"]
        o = self.baseline["ocean"]["openness"]
        if event.kind == "skeleton":
            base = 0.2  # a milestone is mildly positive...
        else:
            base = _perturbation_valence(event.title)
        # Anxious personas read events more negatively; open ones soften shocks.
        colour = -0.3 * (n - 0.5) + (0.15 * (o - 0.5) if base < 0 else 0.0)
        return _clamp(base + colour, -1.0, 1.0)

    def self_valence(self, branch: str, month_events: list[TimelineEvent]) -> float:
        """Current satisfaction in [-1, 1], re-grounded in the baseline (ALG-12).

        ``alignment`` rewards the persona when the *realised* branch matches what
        they wanted; ``optimism`` is the immutable temperament; the event term is
        the only month-specific input. Because alignment and optimism are read
        fresh from the baseline every call, repeated negative months cannot drag
        a persona's identity off its grounding.
        """
        branch_sign = 1.0 if branch == "B" else -1.0
        alignment = self.baseline["change_valence"] * branch_sign
        if month_events:
            event_term = sum(self.event_response(e) for e in month_events) / len(month_events)
        else:
            event_term = 0.0
        return _clamp(0.5 * alignment + 0.2 * self.baseline["optimism"] + 0.3 * event_term, -1.0, 1.0)

    def belief_about(self, other: "PersonaAgent", other_true_valence: float) -> float:
        """X's estimate of Y's valence: theory-of-mind blended with self-projection.

        Low ``tom_accuracy`` personas project their own feelings onto others
        (egocentric bias) and therefore mis-judge those who differ — the seed of
        emergent conflict (ALG-13).
        """
        acc = self.baseline["tom_accuracy"]
        my_valence = self.valence_by_month.get(max(self.valence_by_month, default=0), 0.0)
        return _clamp(acc * other_true_valence + (1.0 - acc) * my_valence, -1.0, 1.0)


# --------------------------------------------------------------------------- #
# Simulation
# --------------------------------------------------------------------------- #
class SocialSimulation:
    """Runs one branch forward; deterministic core + optional LLM enrichment.

    Public attributes after :meth:`run` (consumed by tests / explainability):
    ``metrics``, ``conflicts``, ``activation_log``, ``judgement_trace``,
    ``agents``.
    """

    def __init__(self, world: World, branch: str, events: list[TimelineEvent], rng: Any) -> None:
        self.world = world
        self.branch = branch
        self.events = list(events)
        self.rng = rng
        self.brng = rng.branch_rng(branch)
        self.horizon = MODE_HORIZON.get(world.mode, 6)

        self.agents: dict[str, PersonaAgent] = {
            p.id: PersonaAgent(p) for p in world.personas
        }
        self.events_by_month: dict[int, list[TimelineEvent]] = {}
        for ev in self.events:
            self.events_by_month.setdefault(ev.month, []).append(ev)

        self.metrics: list[Metric] = []
        self.conflicts: list[Conflict] = []
        self.judgement_trace: list[Judgement] = []
        # (persona_id, month) -> activation count (ALG-15 cost audit).
        self.activation_log: dict[tuple[str, int], int] = {}
        self._cumulative_strain = 0.0

    # ------------------------------------------------------------------ #
    # Deterministic core
    # ------------------------------------------------------------------ #
    def run(self) -> SimResult:
        """Run the deterministic simulation; populate metrics + audit structures."""
        self._seed_memories()
        for agent in self.agents.values():
            agent.consistency_snapshots[0] = consistency_probe(agent, branch=self.branch, month=0)

        for month in range(1, self.horizon + 1):
            month_events = self.events_by_month.get(month, [])
            self._observe(month, month_events)
            self._form_beliefs(month, month_events)
            self._detect_conflicts(month, month_events)
            self._emit_metrics(month, month_events)
            self._maybe_reflect(month)

        for agent in self.agents.values():
            agent.consistency_snapshots[self.horizon] = consistency_probe(
                agent, branch=self.branch, month=self.horizon
            )

        return SimResult(branch=self.branch, events=self.events, metrics=self.metrics)  # type: ignore[arg-type]

    # -- month 0: seed memories from grounding ---------------------------- #
    def _seed_memories(self) -> None:
        """Seed each agent's stream from its UserHarness beliefs (the grounding).

        Gives retrieval a non-empty pool from step one, so every later judgement
        is traceable to a concrete memory (ALG-14).
        """
        for agent in self.agents.values():
            persona = agent.persona
            stance = getattr(persona, "stance_on_decision", None) or "still weighing it"
            agent.memory.add(
                f"My stance on '{self.world.decision}': {stance}.",
                importance=6.0 + 0.3 * agent.influence,
                timestamp=0,
                kind="seed",
            )
            for concern in (getattr(persona, "key_concerns", []) or [])[:4]:
                agent.memory.add(
                    f"Something I care about here: {concern}.",
                    importance=6.0,
                    timestamp=0,
                    kind="seed",
                )
            beliefs = getattr(persona, "beliefs", {}) or {}
            belief = beliefs.get("belief", {}) if isinstance(beliefs, dict) else {}
            # Self: seed nested beliefs about the others I think I understand.
            about_others = belief.get("about_others", {}) if isinstance(belief, dict) else {}
            for role, view in (about_others or {}).items():
                want = view.get("i_think_they_want") if isinstance(view, dict) else None
                agent.memory.add(
                    f"I think {role} wants: {want or 'I am not sure'}.",
                    importance=5.0,
                    timestamp=0,
                    kind="belief",
                )
            # Member: seed what they think the decision-maker should do.
            about_them = belief.get("about_them", {}) if isinstance(belief, dict) else {}
            should = about_them.get("i_think_they_should") if isinstance(about_them, dict) else None
            if should:
                agent.memory.add(
                    f"What I think they should do: {should}.",
                    importance=5.5,
                    timestamp=0,
                    kind="belief",
                )

    # -- perception ------------------------------------------------------- #
    def _observe(self, month: int, month_events: list[TimelineEvent]) -> None:
        """Each persona writes observation memories for events touching it."""
        for ev in month_events:
            involved = ev.personas or [a.id for a in self.agents.values()]
            for pid in involved:
                agent = self.agents.get(pid)
                if agent is None:
                    continue
                response = agent.event_response(ev)
                importance = _event_importance(ev, response)
                agent.memory.add(
                    f"[m{month}] Observed: {ev.title} — {ev.detail}",
                    importance=importance,
                    timestamp=month,
                    kind="observation",
                    source_ids=[],
                )

    # -- belief formation (tiered, event-driven activations: ALG-15) ------ #
    def _form_beliefs(self, month: int, month_events: list[TimelineEvent]) -> None:
        """Form each persona's self-belief + nested beliefs within its budget.

        Activation 1 refreshes the self-belief (retrieving from memory, ALG-10,
        and recording the source ids, ALG-14). Remaining activations model the
        most influential *other active* personas — the nested beliefs that drive
        conflict. The count per persona/month is the tiered ALG-15 budget.
        """
        relevant: dict[str, int] = {}
        for agent in self.agents.values():
            relevant[agent.id] = sum(
                1 for ev in month_events if agent.id in (ev.personas or [])
            )

        # Resolve everyone's true self-valence first (needed for nested beliefs).
        true_valence: dict[str, float] = {}
        for agent in self.agents.values():
            v = agent.self_valence(self.branch, month_events)
            agent.valence_by_month[month] = v
            true_valence[agent.id] = v

        self._month_self_belief_id: dict[str, str] = {}
        self._month_belief_about: dict[tuple[str, str], str] = {}

        for agent in self.agents.values():
            budget = self._activation_budget(agent, relevant[agent.id])
            if budget <= 0:
                continue
            self.activation_log[(agent.id, month)] = budget

            # Activation 1: self-belief, grounded + retrieved (ALG-10/12/14).
            self._activate_self(agent, month, month_events, true_valence[agent.id])

            # Remaining activations: model other active personas, most
            # influential first (bounded attention -> emergent mis-judgement).
            others = [
                o for o in self.agents.values()
                if o.id != agent.id and self.activation_log_will_be_active(o, relevant.get(o.id, 0))
            ]
            others.sort(key=lambda o: o.influence, reverse=True)
            for other in others[: budget - 1]:
                self._activate_about_other(agent, other, month, true_valence[other.id])

    def activation_log_will_be_active(self, agent: PersonaAgent, relevant_count: int) -> bool:
        return self._activation_budget(agent, relevant_count) > 0

    def _activation_budget(self, agent: PersonaAgent, relevant_count: int) -> int:
        """Tiered, event-driven activation count for one persona/month (ALG-15)."""
        if agent.is_core:
            # Core personas always do a monthly check-in (floor), event-scaled.
            return max(CORE_MIN_ACTS, min(CORE_MAX_ACTS, 1 + relevant_count))
        if relevant_count <= 0:
            return 0  # minor personas act only when an event involves them
        return max(MINOR_MIN_ACTS, min(MINOR_MAX_ACTS, relevant_count))

    def _activate_self(
        self, agent: PersonaAgent, month: int, month_events: list[TimelineEvent], valence: float
    ) -> None:
        query = (
            f"How do I feel about '{self.world.decision}' given what I value "
            f"({agent.baseline['top_value']}) and recent events?"
        )
        recalled = agent.memory.retrieve(query, now=month, k=4)
        statement = _self_belief_text(agent, valence, recalled)
        entry = agent.memory.add(
            statement,
            importance=5.5 + 2.0 * abs(valence),
            timestamp=month,
            kind="belief",
            source_ids=[m.id for m in recalled],
        )
        self._month_self_belief_id[agent.id] = entry.id
        self.judgement_trace.append(
            Judgement(
                month=month, persona=agent.id, about="self", statement=statement,
                valence=valence, memory_ids=[m.id for m in recalled],
                event_ids=[e.event_id for e in month_events if agent.id in (e.personas or [])],
            )
        )

    def _activate_about_other(
        self, agent: PersonaAgent, other: PersonaAgent, month: int, other_true_valence: float
    ) -> None:
        query = f"What does {other.role} want about '{self.world.decision}'?"
        recalled = agent.memory.retrieve(query, now=month, k=3)
        estimate = agent.belief_about(other, other_true_valence)
        statement = (
            f"I read {other.role} as {_valence_word(estimate)} about the decision "
            f"(my read, which may be off)."
        )
        entry = agent.memory.add(
            statement,
            importance=4.5 + 1.5 * abs(estimate),
            timestamp=month,
            kind="belief",
            source_ids=[m.id for m in recalled],
        )
        self._month_belief_about[(agent.id, other.id)] = entry.id
        self.judgement_trace.append(
            Judgement(
                month=month, persona=agent.id, about=other.id, statement=statement,
                valence=estimate, memory_ids=[m.id for m in recalled], event_ids=[],
            )
        )

    # -- emergent conflict (ALG-13/14) ------------------------------------ #
    def _detect_conflicts(self, month: int, month_events: list[TimelineEvent]) -> None:
        """Derive conflicts from belief divergence + mutual mis-judgement.

        Nothing here writes a "they argued" narrative — a conflict exists iff two
        active personas (a) actually want different things and (b) at least one
        mis-reads the other this month. Magnitude scales with their influence.
        """
        ids = list(self.agents.keys())
        month_event_ids = [e.event_id for e in month_events]
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                ax, ay = self.agents[ids[i]], self.agents[ids[j]]
                vx = ax.valence_by_month.get(month)
                vy = ay.valence_by_month.get(month)
                if vx is None or vy is None:
                    continue

                bid_xy = self._month_belief_about.get((ax.id, ay.id))
                bid_yx = self._month_belief_about.get((ay.id, ax.id))
                if bid_xy is None and bid_yx is None:
                    continue  # neither modelled the other -> no judgement to clash

                divergence = abs(vx - vy) / 2.0  # [0, 1]
                mis = 0.0
                if bid_xy is not None:
                    est_xy = ax.belief_about(ay, vy)
                    mis = max(mis, abs(est_xy - vy) / 2.0)
                if bid_yx is not None:
                    est_yx = ay.belief_about(ax, vx)
                    mis = max(mis, abs(est_yx - vx) / 2.0)

                if (
                    divergence < CONFLICT_DIVERGENCE_THRESHOLD
                    or mis < CONFLICT_MISJUDGEMENT_THRESHOLD
                ):
                    continue

                influence = _clamp((ax.influence + ay.influence) / 20.0, 0.3, 1.0)
                magnitude = _clamp01((0.5 * divergence + 0.5 * mis) * influence)
                evidence_beliefs = [
                    b for b in (
                        bid_xy, bid_yx,
                        self._month_self_belief_id.get(ax.id),
                        self._month_self_belief_id.get(ay.id),
                    ) if b
                ]
                self.conflicts.append(
                    Conflict(
                        month=month, persona_a=ax.id, persona_b=ay.id,
                        magnitude=round(magnitude, 3), divergence=round(divergence, 3),
                        misjudgement=round(mis, 3), evidence_belief_ids=evidence_beliefs,
                        evidence_event_ids=month_event_ids,
                    )
                )

    # -- 5-dimension metrics ---------------------------------------------- #
    def _emit_metrics(self, month: int, month_events: list[TimelineEvent]) -> None:
        f = month / self.horizon
        self_agent = self.agents.get("self") or next(iter(self.agents.values()))
        self_sat = self_agent.valence_by_month.get(month, 0.0)
        ambition = self_agent.baseline["ambition"]

        month_strain = sum(c.magnitude for c in self.conflicts if c.month == month)
        self._cumulative_strain += month_strain
        strain = min(self._cumulative_strain, 3.0)

        ev = _event_dim_effects(month_events)
        evidence = _evidence_for(self.events, month)

        if self.branch == "B":
            base = {
                "economic": 52 + 30 * f * ambition + 10 * self_sat - 3 * strain,
                "career": 50 + 34 * f * ambition + 10 * self_sat - 2 * strain,
                "relationships": 64 - 14 * f - 22 * strain + 6 * self_sat,
                "mental_health": 60 - 10 * f + 14 * math.sin(math.pi * f) + 12 * self_sat - 12 * strain,
                "autonomy": 54 + 30 * f + 8 * self_sat - 2 * strain,
            }
        else:
            base = {
                "economic": 58 + 6 * f + 8 * self_sat - 3 * strain,
                "career": 55 + 4 * f + 8 * self_sat - 2 * strain,
                "relationships": 63 + 5 * f - 18 * strain + 6 * self_sat,
                "mental_health": 61 + 4 * math.sin(math.pi * f) + 12 * self_sat - 12 * strain,
                "autonomy": 50 - 3 * f + 8 * self_sat - 2 * strain,
            }

        for dim in DIMENSIONS:
            noise = (self.brng.random() - 0.5) * 4.0
            score = _clamp(base[dim] + ev.get(dim, 0.0) + noise, 0.0, 100.0)
            self.metrics.append(
                Metric(
                    branch=self.branch,  # type: ignore[arg-type]
                    month=month,
                    dim=dim,
                    score=round(score, 1),
                    evidence_event_ids=evidence,
                )
            )

    # -- reflection (ALG-11) ---------------------------------------------- #
    def _maybe_reflect(self, month: int) -> None:
        for agent in self.agents.values():
            if agent.memory.should_reflect():
                new = agent.memory.reflect(now=month)
                agent.reflections.extend(new)
                if new:
                    logger.info(
                        "simulation: %s reflected at month %d -> %d higher-level belief(s)",
                        agent.id, month, len(new),
                    )

    # ------------------------------------------------------------------ #
    # Optional bounded LLM enrichment (Haiku) — never changes metrics
    # ------------------------------------------------------------------ #
    async def enrich(self, *, llm_client=llm) -> int:
        """Rewrite a few belief/reflection strings into nicer Haiku prose.

        Bounded by :data:`MAX_ENRICH_CALLS_PER_BRANCH`; reflections first, then
        the decision-maker's latest self-beliefs. Degrades to a no-op without an
        API key (the call returns the degraded marker, which we ignore). Returns
        the number of successful rewrites — metric values are untouched.
        """
        targets: list[MemoryEntry] = []
        for agent in self.agents.values():
            targets.extend(agent.reflections)
        self_agent = self.agents.get("self")
        if self_agent is not None:
            beliefs = [e for e in self_agent.memory.entries if e.kind == "belief"]
            targets.extend(beliefs[-3:])
        targets = targets[:MAX_ENRICH_CALLS_PER_BRANCH]

        rewritten = 0
        for entry in targets:
            prompt = (
                "Rewrite this inner belief as one natural, first-person sentence "
                "(<=30 words), probabilistic in tone, no preamble:\n"
                f"{entry.content}"
            )
            text = await llm_client.complete(prompt, tier="haiku", max_tokens=80, fallback=DEGRADED_DEFAULT)
            if text and text.strip() and text.strip() != DEGRADED_DEFAULT.strip():
                entry.content = text.strip()
                rewritten += 1
        if rewritten:
            logger.info("simulation: enriched %d belief(s) on branch %s via Haiku", rewritten, self.branch)
        return rewritten


# --------------------------------------------------------------------------- #
# §5 interface entry point
# --------------------------------------------------------------------------- #
async def run_simulation(
    world: World, branch: str, events: list[TimelineEvent], rng: Any
) -> SimResult:
    """Run one branch's social simulation and return its :class:`SimResult`.

    Async by contract option: the deterministic core runs first (so metrics are
    reproducible and offline-safe), then an optional, bounded Haiku enrichment
    pass polishes belief prose without touching any metric value.
    """
    sim = SocialSimulation(world, branch, events, rng)
    result = sim.run()
    try:
        await sim.enrich()
    except Exception as exc:  # enrichment must never break the result
        logger.warning("simulation: enrichment skipped on branch %s (%s)", branch, exc)
    return result


# --------------------------------------------------------------------------- #
# Persona consistency self-test (ALG-12)
# --------------------------------------------------------------------------- #
def consistency_probe(agent: PersonaAgent, *, branch: str, month: int) -> dict[str, str]:
    """A fixed 5-item questionnaire answered from the persona's current state.

    Four items (value priority, risk preference, sociability, cooperativeness)
    are read straight from the immutable grounding, so they cannot drift. The
    fifth (outlook) reflects the persona's current month valence, which *may*
    legitimately shift with events — but is still anchored by the baseline.
    """
    b = agent.baseline
    ocean = b["ocean"]
    if month <= 0 or month not in agent.valence_by_month:
        outlook_v = b["optimism"]
    else:
        outlook_v = agent.valence_by_month[month]
    return {
        "value_priority": b["top_value"],
        "risk_preference": _band(b["risk"], "risk-seeking", "neutral", "risk-averse"),
        "sociability": _band(ocean["extraversion"], "outgoing", "balanced", "reserved"),
        "cooperativeness": _band(ocean["agreeableness"], "cooperative", "balanced", "competitive"),
        "outlook": _valence_word(outlook_v),
    }


def persona_consistency_score(agent: PersonaAgent) -> float:
    """Score in [0, 5]: how stable the persona is vs its baseline grounding (ALG-12).

    Compares the final-month questionnaire against the baseline answers. The four
    grounded dimensions never flip (grounding is re-injected every belief
    formation), so the score is ≥4/5 by construction; outlook may move with
    lived events. Core values and risk preference never reverse direction.
    """
    baseline_probe = {
        "value_priority": agent.baseline["top_value"],
        "risk_preference": _band(agent.baseline["risk"], "risk-seeking", "neutral", "risk-averse"),
        "sociability": _band(agent.baseline["ocean"]["extraversion"], "outgoing", "balanced", "reserved"),
        "cooperativeness": _band(agent.baseline["ocean"]["agreeableness"], "cooperative", "balanced", "competitive"),
        "outlook": _valence_word(agent.baseline["optimism"]),
    }
    final_month = max(agent.consistency_snapshots, default=0)
    final_probe = agent.consistency_snapshots.get(final_month, baseline_probe)
    matches = sum(1 for k, v in baseline_probe.items() if final_probe.get(k) == v)
    return round(5.0 * matches / len(baseline_probe), 2)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))


def _clamp01(x: float) -> float:
    return _clamp(x, 0.0, 1.0)


def _band(x: float, hi_label: str, mid_label: str, lo_label: str) -> str:
    if x > 0.55:
        return hi_label
    if x < 0.45:
        return lo_label
    return mid_label


def _stance_to_valence(stance: Optional[str]) -> float:
    if not stance:
        return 0.0
    low = stance.lower()
    if any(k in low for k in _POSITIVE_STANCE):
        return 0.7
    if any(k in low for k in _NEGATIVE_STANCE):
        return -0.7
    return 0.0


def _valence_word(v: float) -> str:
    if v > 0.15:
        return "positive"
    if v < -0.15:
        return "negative"
    return "neutral"


def _perturbation_valence(title: str) -> float:
    low = title.lower()
    for key, val in _PERTURBATION_VALENCE.items():
        if key in low:
            return val
    return 0.0


def _event_dim_effects(month_events: list[TimelineEvent]) -> dict[str, float]:
    """Aggregate per-dimension point deltas implied by this month's events."""
    out: dict[str, float] = {}
    for ev in month_events:
        if ev.kind == "skeleton":
            out["career"] = out.get("career", 0.0) + 2.0
            out["economic"] = out.get("economic", 0.0) + 1.5
            continue
        low = ev.title.lower()
        for key, effects in _PERTURBATION_DIM_EFFECT.items():
            if key in low:
                for dim, delta in effects.items():
                    out[dim] = out.get(dim, 0.0) + delta
                break
    return out


def _event_importance(event: TimelineEvent, response: float) -> float:
    """Importance 1..10: skeletons matter; perturbations matter more when intense."""
    base = 5.0 if event.kind == "skeleton" else 6.0
    return max(1.0, min(10.0, base + 4.0 * abs(response)))


def _self_belief_text(agent: PersonaAgent, valence: float, recalled: list[MemoryEntry]) -> str:
    cue = recalled[0].content if recalled else "my baseline values"
    return (
        f"On balance I feel {_valence_word(valence)} about the decision right now "
        f"(weighing {agent.baseline['top_value']}; recalling: {cue[:80]})."
    )


def _evidence_for(events: list[TimelineEvent], month: int) -> list[str]:
    """At least one supporting event id for a metric (ALG-40)."""
    same = [e.event_id for e in events if e.month == month]
    if same:
        return same[:2]
    prior = [e for e in events if e.month <= month]
    if prior:
        return [max(prior, key=lambda e: e.month).event_id]
    if events:
        return [min(events, key=lambda e: e.month).event_id]
    return []


def _top_value(concerns: list[str]) -> str:
    for concern in concerns:
        dim = _VALUE_MAP.get(re.sub(r"[^a-z\-]", "", concern.strip().lower()))
        if dim:
            return dim
    return "balance"


__all__ = [
    "run_simulation",
    "SocialSimulation",
    "PersonaAgent",
    "Conflict",
    "Judgement",
    "consistency_probe",
    "persona_consistency_score",
    "MODE_HORIZON",
]
