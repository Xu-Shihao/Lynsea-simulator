"""Bounded multi-agent interaction loop (MiroFish/OASIS-inspired, ALG-13).

Medium/Heavy modes replace the single-pass `simulate.generate_branch_events`
with a month-by-month, agent-driven simulation. Each persona is an agent with its
own in-process `MemoryStream` (engine/memory.py) seeded from its key_concerns and
beliefs. For each step (months may be batched to bound LLM cost) every agent
retrieves the memories most relevant to the current situation and produces a
reaction/action; a lightweight "world step" reconciles those reactions into
`TimelineEvent`s:

  - **skeleton** events for the expected milestones each agent acts toward, and
  - **perturbation** events for *emergent conflict* (ALG-13) — produced whenever
    two agents' stances/beliefs clash on the same step. The clash is not scripted
    by any single LLM call; it falls out of the agents' opposed stances meeting in
    the world step, then is written back into BOTH agents' memory streams so the
    conflict is traceable to the agents that caused it.

Cost is bounded by capping the number of agents, batching the horizon into a few
steps, and one `config.complete_json` call per agent-step with a deterministic,
persona-trait-driven stub fallback. The whole loop respects
`config.force_stub_active()` (set by the orchestrator's budget escalation) and
runs deterministically on the stub path given a fixed seed, so tests pass with no
key.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .. import config
from ..contracts import Dimension, Persona, TimelineEvent
from .common import horizon_for_mode
from .memory import MemoryItem, MemoryStream

# Per-mode bounds: how many agents act, and how many world steps the horizon is
# batched into. Keeps total LLM calls = agents x steps small (NFR-04 / spec §4).
_MODE_AGENT_CAP = {"quick": 5, "medium": 12, "heavy": 16}
_MODE_STEPS = {"quick": 3, "medium": 4, "heavy": 6}

# Reflection threshold for an agent over a single simulation. Lower than the
# spec's ~150 default for a full lifetime so a multi-step run can realistically
# synthesize at least one belief.
_AGENT_REFLECTION_THRESHOLD = 18

_OPPOSED = {"supportive": "opposed", "opposed": "supportive"}

_AGENT_SYSTEM = (
    "You role-play a person reacting to someone's life decision over time. Given "
    "your psychology, beliefs, and what you remember, state your reaction this "
    "period as STRICT JSON only."
)


@dataclass
class InteractionResult:
    """Output of one branch's multi-agent interaction.

    `events` are the reconciled TimelineEvents (skeleton + emergent perturbation).
    `memories` maps persona id -> that agent's MemoryStream after the run, so the
    caller (and tests) can trace why an emergent event happened.
    """

    events: List[TimelineEvent]
    memories: Optional[Dict[str, MemoryStream]] = None


def _agent_cap(mode: str) -> int:
    return _MODE_AGENT_CAP.get((mode or "quick").lower(), _MODE_AGENT_CAP["quick"])


def _num_steps(mode: str) -> int:
    return _MODE_STEPS.get((mode or "quick").lower(), _MODE_STEPS["quick"])


def _seed_memories(persona: Persona, stream: MemoryStream) -> None:
    """Seed an agent's memory from its key_concerns + beliefs (engine-internal)."""
    for concern in persona.key_concerns or []:
        stream.add(MemoryItem(
            text="I care about %s" % concern, importance=6, month=0, source="concern",
        ))
    for belief in persona.beliefs or []:
        stream.add(MemoryItem(
            text="I believe %s" % belief, importance=7, month=0, source="belief",
        ))
    # Always anchor the agent's standing disposition so retrieval is never empty.
    stream.add(MemoryItem(
        text="My overall stance is %s." % (persona.stance or "unknown"),
        importance=4, month=0, source="stance",
    ))


def _trait_intensity(persona: Persona) -> float:
    """How strongly this agent pushes its stance (0..1), from traits + influence.

    Higher conscientiousness/extraversion and influence_weight => stronger push;
    higher agreeableness softens it slightly. Deterministic.
    """
    b5 = persona.big5
    raw = (b5.C + b5.E + persona.influence_weight - b5.A * 0.5) / 25.0
    return max(0.05, min(1.0, raw))


def _stub_reaction(
    persona: Persona, option_text: str, month: int, rng: random.Random,
) -> Dict[str, object]:
    """Deterministic, persona-trait-driven reaction for the stub path.

    Encodes a stance, an intensity, and a short action sentence. No LLM.
    """
    stance = persona.stance or "unknown"
    intensity = _trait_intensity(persona)
    # A small deterministic wobble so reactions are not identical across months.
    intensity = max(0.0, min(1.0, intensity + rng.uniform(-0.1, 0.1)))
    if stance == "supportive":
        action = "I support and help with '%s'." % option_text
    elif stance == "opposed":
        action = "I push back against '%s'." % option_text
    elif stance == "neutral":
        action = "I stay on the fence about '%s'." % option_text
    else:
        action = "I am still figuring out how I feel about '%s'." % option_text
    return {"stance": stance, "intensity": round(intensity, 3), "action": action}


def _llm_reaction(
    persona: Persona,
    option_text: str,
    decision: str,
    retrieved: List[MemoryItem],
    month: int,
) -> Optional[Dict[str, object]]:
    """Try to elicit an agent reaction via Claude; None on any failure/stub."""
    mem_blurb = "; ".join(it.text for it in retrieved) or "(no memories yet)"
    tom = "; ".join("%s:%s" % (k, v) for k, v in (persona.theory_of_mind or {}).items())
    prompt = (
        "Decision being made by someone close to you: %s\n"
        "They are leaning toward: %s\n"
        "You are %s (role: %s). Your stance so far: %s.\n"
        "Your beliefs: %s\n"
        "What you assume about others: %s\n"
        "What you remember right now: %s\n"
        "It is month %d.\n\n"
        "React this period. Return STRICT JSON: "
        '{"stance":"supportive|opposed|neutral|unknown",'
        '"intensity":0.0-1.0,"action":"one short sentence"}. JSON only.'
        % (
            decision, option_text, persona.name, persona.role,
            persona.stance or "unknown",
            "; ".join(persona.beliefs or []) or "(none stated)",
            tom or "(none)", mem_blurb, month,
        )
    )
    try:
        raw = config.complete_json(
            prompt, system=_AGENT_SYSTEM, max_tokens=200, temperature=0.6
        )
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None
    stance = raw.get("stance")
    if stance not in ("supportive", "opposed", "neutral", "unknown"):
        stance = persona.stance or "unknown"
    try:
        intensity = float(raw.get("intensity", _trait_intensity(persona)))
    except (TypeError, ValueError):
        intensity = _trait_intensity(persona)
    intensity = max(0.0, min(1.0, intensity))
    action = str(raw.get("action", "")).strip() or (
        "I react to '%s'." % option_text
    )
    return {"stance": stance, "intensity": intensity, "action": action}


def _agent_step(
    persona: Persona,
    stream: MemoryStream,
    option_text: str,
    decision: str,
    month: int,
    rng: random.Random,
) -> Dict[str, object]:
    """One agent's turn: retrieve memories then react (LLM or deterministic stub)."""
    query = "%s %s %s" % (
        decision, option_text, " ".join(persona.key_concerns or [])
    )
    retrieved = stream.retrieve(query=query, now_month=month, k=5)
    reaction: Optional[Dict[str, object]] = None
    if not config.force_stub_active():
        reaction = _llm_reaction(persona, option_text, decision, retrieved, month)
    if reaction is None:
        reaction = _stub_reaction(persona, option_text, month, rng)
    reaction["persona_id"] = persona.id
    return reaction


def _stances_clash(a: Dict[str, object], b: Dict[str, object]) -> bool:
    """Two reactions clash if their stances are direct opposites (ALG-13)."""
    sa = str(a.get("stance"))
    sb = str(b.get("stance"))
    return _OPPOSED.get(sa) == sb and sa != sb


def run_interaction(
    branch: str,
    option_text: str,
    decision: str,
    personas: List[Persona],
    backbone: List[Dict[str, object]],
    dimensions: List[Dimension],
    seed: int,
    mode: str,
) -> InteractionResult:
    """Run the bounded multi-agent interaction for one branch.

    Returns an InteractionResult holding the reconciled TimelineEvents and each
    agent's post-run MemoryStream. Deterministic on the stub path given `seed`.
    Event ids are unique; involved_personas are always real persona ids.
    """
    horizon = horizon_for_mode(mode)
    cap = _agent_cap(mode)
    agents = list(personas)[:cap]
    valid_ids = {p.id for p in agents}
    user_id = agents[0].id if agents else "p_user"

    # Each agent gets its own memory stream, seeded from concerns + beliefs.
    memories: Dict[str, MemoryStream] = {}
    for p in agents:
        ms = MemoryStream(reflection_threshold=_AGENT_REFLECTION_THRESHOLD)
        _seed_memories(p, ms)
        memories[p.id] = ms

    # Batch the horizon into a few world steps (bounds LLM cost). Each step maps
    # to a representative month spread across the horizon.
    n_steps = max(1, _num_steps(mode))
    step_months = [
        max(1, min(horizon, round((s + 1) * horizon / float(n_steps))))
        for s in range(n_steps)
    ]

    events: List[TimelineEvent] = []
    counter = 0

    def _new_event(month: int, title: str, desc: str, kind: str,
                   involved: List[str], evidence: Optional[str]) -> TimelineEvent:
        nonlocal counter
        ev_id = "ev_%s_int_%02d" % (branch, counter)
        counter += 1
        return TimelineEvent(
            id=ev_id,
            branch=branch,
            month=month,
            title=title,
            description=desc,
            kind=kind,
            is_shared_exogenous=False,
            shared_event_id=None,
            involved_personas=[i for i in involved if i in valid_ids] or [user_id],
            evidence=evidence,
        )

    for month in step_months:
        # 1) Each agent acts. Per-agent deterministic RNG keyed by seed so the
        #    stub path is stable across runs.
        reactions: List[Dict[str, object]] = []
        for p in agents:
            arng = random.Random("%d:%s:%s:%d" % (seed, branch, p.id, month))
            reactions.append(_agent_step(p, memories[p.id], option_text, decision, month, arng))

        # 2) World step — skeleton milestone: the agents acting toward the option.
        actors = [r["persona_id"] for r in reactions]
        skeleton = _new_event(
            month=month,
            title="Period %d: acting on '%s'" % (month, option_text),
            desc=(
                "The people involved respond to the choice. "
                + " ".join(str(r["action"]) for r in reactions[:3])
            ),
            kind="skeleton",
            involved=actors[:3] or [user_id],
            evidence="agent interaction (month %d)" % month,
        )
        events.append(skeleton)
        # Record the milestone in every actor's memory.
        for r in reactions:
            pid = str(r["persona_id"])
            memories[pid].add(MemoryItem(
                text="Month %d: %s" % (month, r["action"]),
                importance=4 + int(round(float(r.get("intensity", 0.5)) * 4)),
                month=month,
                source=skeleton.id,
            ))

        # 3) Emergent conflict (ALG-13): any pair of agents whose stances are
        #    direct opposites this step produces a perturbation event, written
        #    back into BOTH agents' memory so it is traceable.
        seen_pairs: set = set()
        for i in range(len(reactions)):
            for j in range(i + 1, len(reactions)):
                ra, rb = reactions[i], reactions[j]
                if not _stances_clash(ra, rb):
                    continue
                pid_a, pid_b = str(ra["persona_id"]), str(rb["persona_id"])
                pair = tuple(sorted((pid_a, pid_b)))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                name_a = next((p.name for p in agents if p.id == pid_a), pid_a)
                name_b = next((p.name for p in agents if p.id == pid_b), pid_b)
                conflict = _new_event(
                    month=month,
                    title="Conflict between %s and %s" % (name_a, name_b),
                    desc=(
                        "A clash emerges: %s (%s) and %s (%s) pull in opposite "
                        "directions over '%s'. The tension forces a hard "
                        "conversation." % (
                            name_a, ra.get("stance"), name_b, rb.get("stance"),
                            option_text,
                        )
                    ),
                    kind="perturbation",
                    involved=[pid_a, pid_b],
                    evidence="emergent conflict from opposed agent stances (ALG-13)",
                )
                events.append(conflict)
                # Trace it into both agents' memories (high importance so it can
                # drive a later reflection).
                for pid, other in ((pid_a, name_b), (pid_b, name_a)):
                    memories[pid].add(MemoryItem(
                        text="Month %d: conflict with %s over '%s' — real tension."
                             % (month, other, option_text),
                        importance=8,
                        month=month,
                        source=conflict.id,
                    ))

        # 4) Each agent may reflect on the accumulated step outcomes.
        for p in agents:
            memories[p.id].maybe_reflect(now_month=month)

    # Stable ordering: skeleton first, then perturbation, by month then id.
    kind_rank = {"skeleton": 0, "perturbation": 1, "exogenous": 2}
    events.sort(key=lambda e: (kind_rank.get(e.kind, 3), e.month, e.id))
    return InteractionResult(events=events, memories=memories)
