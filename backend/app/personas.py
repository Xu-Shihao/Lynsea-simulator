"""Belief-based digital twins — the UserHarness world builder (BE-Twin).

Owner file (BUILD_PLAN §4): ``backend/app/personas.py``.
Implements the §5 interface ``build_world(req, rng) -> World``; the orchestrator
auto-binds this module (no edit to ``orchestrator.py`` required).

UserHarness grounding (arXiv:2605.27721)
----------------------------------------
Every persona — the decision-maker ("self") and 3–5 social-circle members — is
modelled as a mind, not a label:

    Environment -> Observation -> **Belief** -> Goal -> Action

The *belief* layer is what makes interpersonal conflict **emergent** rather than
narrated: each persona carries (a) first-order beliefs about the decision itself
and (b) **nested beliefs about other people** (what they think the others want /
will do). When BE-Sim later lets these personas act on mutually mis-calibrated
beliefs, conflict falls out of the mis-judgement instead of being scripted.

Acceptance IDs satisfied here
-----------------------------
* **ALG-01 (min info set)** — 5–7 fields are enough to boot a full ``World``
  (the user + 3–5 personas). Everything else is inferred or defaulted.
* **ALG-02 (Big Five from behaviour)** — O/C/E/A/N are *inferred from the
  behavioural description*, never read from user-entered numbers, and each trait
  carries an explainable rationale string. Inference uses ``app.llm`` (Sonnet
  tier) with a deterministic heuristic fallback so the build never crashes when
  the model is unavailable (`BE-12`).
* **ALG-03 (schema validity)** — every profile validates against ``Persona``.
* **ALG-04 (cold start)** — personas built from population/group defaults are
  tagged ``confidence="low"`` and carry a human-readable
  "信息有限，仅供参考 / limited info" note surfaced to the UI.

Belief/rationale data that has no field in the wire-level ``Persona`` schema is
attached as a *live Python attribute* (via :func:`_attach`) so the schema (and
therefore the ``world_ready`` payload) stays byte-for-byte unchanged while
BE-Sim can still read the richer mind-model off ``world.personas``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Optional

from app.llm import DEGRADED_DEFAULT, llm
from app.schemas import (
    Persona,
    ProfileInput,
    SimulateRequest,
    SocialCircleMember,
    ValueWeights,
    World,
)

logger = logging.getLogger("lynsea.personas")

# The five OCEAN trait keys, in canonical order.
BIG_FIVE_TRAITS: tuple[str, ...] = (
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
)

# Human-readable cold-start note surfaced to the UI (ALG-04). Bilingual on
# purpose — the product copy is zh-first with an English gloss.
COLD_START_NOTE = "信息有限，仅供参考 / limited info — built from group defaults"

# Upper bound on personas in a World (api-contract: quick = 3–5 personas).
MAX_PERSONAS = 5
MIN_PERSONAS = 3

# Default social roles used to pad a sparse circle up to the 3-persona floor.
# Each is a cold-start (population-default) persona.
_DEFAULT_ROLES: tuple[str, ...] = ("partner", "close friend", "mentor")


# --------------------------------------------------------------------------- #
# Public interface — build_world(req, rng) -> World  (§5 BuildWorld)
# --------------------------------------------------------------------------- #
def build_world(req: SimulateRequest, rng: Any) -> World:
    """Build the seeded world: the user's digital twin + 3–5 social personas.

    Synchronous by contract (the orchestrator runs it in a worker thread). LLM
    inference for Big-Five-from-behaviour is async, so it is driven on a private
    event loop here; if no model is reachable (no key / failure) every persona
    falls back to a deterministic heuristic so the build always succeeds.
    """
    # Option labels (A/B). Use the caller's first two options, else infer a
    # neutral status-quo vs. change pair so a bare ``decision`` still boots a
    # full world (ALG-01).
    if req.options and len(req.options) >= 2:
        opt_a, opt_b = req.options[0], req.options[1]
    else:
        opt_a, opt_b = _infer_options(req.decision)

    personas: list[Persona] = _assemble_personas(req)

    # Big-Five-from-behaviour inference for every persona (ALG-02). Run the
    # batch on a private loop; never let a model failure break world-build.
    _infer_big_five_for_all(personas, req, opt_a, opt_b)

    return World(
        run_id="",  # the orchestrator stamps run_id after the handshake
        decision=req.decision,
        mode=req.mode,
        seed=int(getattr(rng, "seed", 0)),
        options={"A": opt_a, "B": opt_b},
        personas=personas[:MAX_PERSONAS],
        values=_value_weights(req),
    )


# --------------------------------------------------------------------------- #
# Persona assembly (min info set + cold start)
# --------------------------------------------------------------------------- #
def _assemble_personas(req: SimulateRequest) -> list[Persona]:
    """Build the user + social-circle personas with belief grounding.

    ALG-01: this needs only the request's 5–7 fields. ALG-04: any persona built
    from group defaults (no stated stance / no profile) is ``confidence="low"``
    and ``cold_start=True`` with the bilingual limited-info note.
    """
    personas: list[Persona] = [_build_self(req)]

    seen_roles = {"you"}
    for i, member in enumerate(req.social_circle):
        if len(personas) >= MAX_PERSONAS:
            break
        role_key = member.role.strip().lower()
        if role_key in seen_roles:
            continue
        seen_roles.add(role_key)
        personas.append(_build_circle_member(member, i, req))

    # Pad to the 3-persona floor with population-default (cold-start) roles so a
    # bare decision still produces a believable little society (ALG-01/04).
    for role in _DEFAULT_ROLES:
        if len(personas) >= MIN_PERSONAS:
            break
        if role.lower() in seen_roles:
            continue
        seen_roles.add(role.lower())
        personas.append(_build_default_member(role, req))

    return personas


def _build_self(req: SimulateRequest) -> Persona:
    """The decision-maker. High-confidence iff a profile was supplied (ALG-04)."""
    profile: Optional[ProfileInput] = req.profile
    has_profile = profile is not None and _profile_is_informative(profile)

    concerns = list(profile.core_values) if profile and profile.core_values else []
    persona = Persona(
        id="self",
        role="you",
        influence_weight=10,
        confidence="high" if has_profile else "low",
        stance_on_decision="considering",
        key_concerns=concerns,
        big_five={},  # filled by ALG-02 inference
        cold_start=not has_profile,
    )

    beliefs = _self_beliefs(req, profile)
    _attach(persona, beliefs=beliefs, big_five_rationale={})
    if not has_profile:
        _attach(persona, cold_start_note=COLD_START_NOTE)
    return persona


def _build_circle_member(
    member: SocialCircleMember, index: int, req: SimulateRequest
) -> Persona:
    """A social-circle persona supplied by the user.

    A member with a stated stance is treated as well-specified (high
    confidence); otherwise it is a cold-start default (ALG-04).
    """
    has_stance = bool(member.stance_on_decision)
    persona = Persona(
        id=f"{_slug(member.role)}-{index + 1}",
        role=member.role,
        influence_weight=member.influence_weight,
        confidence="high" if has_stance else "low",
        stance_on_decision=member.stance_on_decision,
        key_concerns=list(member.key_concerns),
        big_five={},
        cold_start=not has_stance,
    )

    beliefs = _member_beliefs(member, req)
    _attach(persona, beliefs=beliefs, big_five_rationale={})
    if not has_stance:
        _attach(persona, cold_start_note=COLD_START_NOTE)
    return persona


def _build_default_member(role: str, req: SimulateRequest) -> Persona:
    """A population-default persona used to pad a sparse circle (cold start)."""
    persona = Persona(
        id=_slug(role),
        role=role,
        influence_weight=5,
        confidence="low",
        stance_on_decision=None,
        key_concerns=[],
        big_five={},
        cold_start=True,
    )
    beliefs = _default_beliefs(role, req)
    _attach(
        persona,
        beliefs=beliefs,
        big_five_rationale={},
        cold_start_note=COLD_START_NOTE,
    )
    return persona


# --------------------------------------------------------------------------- #
# UserHarness belief construction (Environment -> Observation -> Belief ...)
# --------------------------------------------------------------------------- #
def _self_beliefs(req: SimulateRequest, profile: Optional[ProfileInput]) -> dict:
    """Beliefs for the decision-maker, incl. nested beliefs about the circle."""
    values = list(profile.core_values) if profile and profile.core_values else []
    nested = {
        m.role: {
            "i_think_they_want": m.stance_on_decision or "unknown — I'm guessing",
            "their_concerns_as_i_see_them": list(m.key_concerns),
        }
        for m in req.social_circle
    }
    return {
        "environment": f"Facing the decision: {req.decision!r}.",
        "observation": (
            f"Risk tolerance ~{profile.risk_tolerance}/10; "
            f"decision style: {profile.decision_style or 'unspecified'}."
            if profile
            else "Little is known about my own profile yet (cold start)."
        ),
        "belief": {
            "about_decision": "I am genuinely undecided and weighing trade-offs.",
            "about_my_values": values or ["unspecified"],
            "about_others": nested,  # nested beliefs -> emergent conflict
        },
        "goal": "Choose the path that best fits what I actually value.",
        "action_tendency": (profile.decision_style if profile else "deliberating"),
    }


def _member_beliefs(member: SocialCircleMember, req: SimulateRequest) -> dict:
    """Beliefs for a stated social-circle member, incl. a nested belief about
    the decision-maker (what *they* think the user should do)."""
    return {
        "environment": f"Someone close to me is deciding: {req.decision!r}.",
        "observation": f"My role: {member.role}; influence ~{member.influence_weight}/10.",
        "belief": {
            "about_decision": member.stance_on_decision or "I haven't formed a clear view.",
            "my_concerns": list(member.key_concerns),
            "about_them": {
                "i_think_they_should": member.stance_on_decision
                or "do what makes them happy — though I'm unsure what that is",
            },
        },
        "goal": "Push the outcome toward what I believe is best for them (and me).",
        "action_tendency": "advocate" if member.stance_on_decision else "observe",
    }


def _default_beliefs(role: str, req: SimulateRequest) -> dict:
    """Population-default beliefs for a cold-start persona (ALG-04)."""
    return {
        "environment": f"A {role} of someone deciding: {req.decision!r}.",
        "observation": "Built from group averages — specifics are unknown.",
        "belief": {
            "about_decision": "No stated view; defaults to typical group attitude.",
            "my_concerns": [],
            "about_them": {"i_think_they_should": "I don't have enough info to say."},
        },
        "goal": "Generic supportive stance.",
        "action_tendency": "observe",
        "note": COLD_START_NOTE,
    }


# --------------------------------------------------------------------------- #
# ALG-02: Big Five inferred from behavioural description (not user numbers)
# --------------------------------------------------------------------------- #
def _infer_big_five_for_all(
    personas: list[Persona], req: SimulateRequest, opt_a: str, opt_b: str
) -> None:
    """Fill ``big_five`` + a per-trait rationale for every persona in place."""
    try:
        asyncio.run(_infer_big_five_async(personas, req, opt_a, opt_b))
    except RuntimeError:
        # Already inside a running loop (rare under to_thread): use heuristics.
        for p in personas:
            scores, rationale = _heuristic_big_five(p, req)
            _set_big_five(p, scores, rationale)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Big-Five inference failed (%s); using heuristics.", exc)
        for p in personas:
            scores, rationale = _heuristic_big_five(p, req)
            _set_big_five(p, scores, rationale)


async def _infer_big_five_async(
    personas: list[Persona], req: SimulateRequest, opt_a: str, opt_b: str
) -> None:
    results = await asyncio.gather(
        *(_infer_one(p, req, opt_a, opt_b) for p in personas)
    )
    for persona, (scores, rationale) in zip(personas, results):
        _set_big_five(persona, scores, rationale)


async def _infer_one(
    persona: Persona, req: SimulateRequest, opt_a: str, opt_b: str
) -> tuple[dict[str, float], dict[str, str]]:
    """Infer OCEAN for one persona from its *behavioural* description (ALG-02).

    Sends a Sonnet-tier prompt asking for 0..1 scores + a one-line rationale per
    trait. On any degrade/parse failure, returns a deterministic heuristic so
    the world always boots (`BE-12`).
    """
    description = _behavioural_blurb(persona, req)
    prompt = _BIG_FIVE_PROMPT.format(
        role=persona.role,
        decision=req.decision,
        option_a=opt_a,
        option_b=opt_b,
        description=description,
    )
    raw = await llm.call(
        [{"role": "user", "content": prompt}],
        tier="sonnet",
        system=_BIG_FIVE_SYSTEM,
        max_tokens=700,
        fallback=DEGRADED_DEFAULT,
    )
    parsed = _parse_big_five(raw)
    if parsed is None:
        return _heuristic_big_five(persona, req)
    return parsed


def _behavioural_blurb(persona: Persona, req: SimulateRequest) -> str:
    """A behavioural description string — explicitly NOT user-entered OCEAN
    numbers (ALG-02). Synthesised from role, stance, concerns and (for self)
    risk tolerance + decision style."""
    bits: list[str] = [f"Role relative to the decision-maker: {persona.role}."]
    if persona.stance_on_decision:
        bits.append(f"Stated stance on the decision: {persona.stance_on_decision}.")
    if persona.key_concerns:
        bits.append("Things they care about: " + ", ".join(persona.key_concerns) + ".")
    if persona.id == "self" and req.profile:
        prof = req.profile
        if prof.occupation:
            bits.append(f"Occupation: {prof.occupation}.")
        if prof.risk_tolerance is not None:
            bits.append(
                f"Behaviourally takes risks around {prof.risk_tolerance}/10 of the time."
            )
        if prof.decision_style:
            bits.append(f"Tends to decide in a {prof.decision_style} way.")
    if persona.cold_start:
        bits.append(
            "Little behavioural detail is known; infer cautiously from the role's "
            "population baseline (limited info)."
        )
    return " ".join(bits)


_BIG_FIVE_SYSTEM = (
    "You are a careful personality psychologist. You infer Big Five (OCEAN) "
    "trait *tendencies* purely from a behavioural description — never from any "
    "self-reported trait numbers. You always answer with strict JSON."
)

_BIG_FIVE_PROMPT = """Infer this person's Big Five personality tendencies from the BEHAVIOURAL description below.
Do NOT use any numeric self-ratings; reason only from observable behaviour and context.

Person role: {role}
Decision they (or someone close to them) face: {decision!r}
Option A: {option_a}
Option B: {option_b}
Behavioural description: {description}

Return STRICT JSON only, no prose, in exactly this shape (scores are 0.0–1.0):
{{
  "openness": {{"score": 0.0, "rationale": "one short sentence grounded in the behaviour"}},
  "conscientiousness": {{"score": 0.0, "rationale": "..."}},
  "extraversion": {{"score": 0.0, "rationale": "..."}},
  "agreeableness": {{"score": 0.0, "rationale": "..."}},
  "neuroticism": {{"score": 0.0, "rationale": "..."}}
}}"""


def _parse_big_five(
    raw: str,
) -> Optional[tuple[dict[str, float], dict[str, str]]]:
    """Parse the model's JSON into (scores, rationales); None on failure."""
    if not raw or raw.strip() == DEGRADED_DEFAULT.strip():
        return None
    blob = _extract_json(raw)
    if blob is None:
        return None
    try:
        data = json.loads(blob)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None

    scores: dict[str, float] = {}
    rationales: dict[str, str] = {}
    for trait in BIG_FIVE_TRAITS:
        entry = data.get(trait)
        if not isinstance(entry, dict):
            return None
        try:
            score = float(entry.get("score"))
        except (TypeError, ValueError):
            return None
        rationale = entry.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            return None
        scores[trait] = _clamp01(score)
        rationales[trait] = rationale.strip()
    return scores, rationales


def _extract_json(text: str) -> Optional[str]:
    """Pull the first balanced ``{...}`` block out of a model response."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


# --------------------------------------------------------------------------- #
# Deterministic heuristic fallback (no LLM) — still "from behaviour" (ALG-02)
# --------------------------------------------------------------------------- #
def _heuristic_big_five(
    persona: Persona, req: SimulateRequest
) -> tuple[dict[str, float], dict[str, str]]:
    """Derive OCEAN + rationale from behavioural signals without a model.

    Signals: risk tolerance, decision style, stated concerns, role and stance.
    Every trait still gets an explainable rationale string (ALG-02), and a
    cold-start persona is nudged toward neutral with a "limited info" rationale.
    """
    text = _behavioural_blurb(persona, req).lower()
    risk = None
    if persona.id == "self" and req.profile and req.profile.risk_tolerance is not None:
        risk = req.profile.risk_tolerance / 10.0

    def has(*words: str) -> bool:
        return any(w in text for w in words)

    # Openness: curiosity / novelty seeking / risk appetite.
    openness = 0.5
    o_reason = "Neutral by default; no strong novelty signal in the behaviour."
    if risk is not None:
        openness = _clamp01(0.35 + 0.5 * risk)
        o_reason = f"Risk-taking behaviour (~{int(risk*10)}/10) suggests openness to new experience."
    if has("growth", "explore", "creative", "learn", "startup", "abroad"):
        openness = _clamp01(openness + 0.15)
        o_reason += " Mentions growth/exploration, nudging openness up."

    # Conscientiousness: planning / analytic decision style.
    consc = 0.55
    c_reason = "Assumed moderately organised absent contrary signals."
    if has("analytic", "careful", "plan", "deliberat", "cautious"):
        consc = 0.78
        c_reason = "Deliberate, planning-oriented behaviour implies high conscientiousness."
    elif has("impulsive", "spontaneous", "gut"):
        consc = 0.35
        c_reason = "Spontaneous/gut-driven behaviour implies lower conscientiousness."

    # Extraversion: role sociability + influence.
    extra = 0.5
    e_reason = "Average sociability inferred from role."
    if persona.influence_weight >= 8:
        extra = 0.66
        e_reason = "High social influence suggests an outgoing, assertive style."
    if has("friend", "partner", "community", "team"):
        extra = _clamp01(extra + 0.1)
        e_reason += " Social-relationship focus nudges extraversion up."

    # Agreeableness: cooperative concerns / supportive roles.
    agree = 0.55
    a_reason = "Mildly cooperative by default."
    if has("family", "support", "care", "relationship", "partner", "mentor"):
        agree = 0.72
        a_reason = "Care/relationship-centred concerns imply higher agreeableness."
    if has("compet", "ambition", "win"):
        agree = _clamp01(agree - 0.2)
        a_reason += " Competitive signals temper agreeableness."

    # Neuroticism: inverse of risk tolerance + worry signals.
    neuro = 0.45
    n_reason = "Average emotional reactivity assumed."
    if risk is not None:
        neuro = _clamp01(0.75 - 0.5 * risk)
        n_reason = f"Lower risk appetite (~{int(risk*10)}/10) correlates with more caution/worry."
    if has("worry", "anxious", "stress", "uncertain", "fear"):
        neuro = _clamp01(neuro + 0.15)
        n_reason += " Worry/uncertainty language raises neuroticism."

    scores = {
        "openness": round(openness, 2),
        "conscientiousness": round(consc, 2),
        "extraversion": round(extra, 2),
        "agreeableness": round(agree, 2),
        "neuroticism": round(neuro, 2),
    }
    rationales = {
        "openness": o_reason,
        "conscientiousness": c_reason,
        "extraversion": e_reason,
        "agreeableness": a_reason,
        "neuroticism": n_reason,
    }

    if persona.cold_start:
        # Pull toward neutral and flag the limited evidence in every rationale.
        for t in BIG_FIVE_TRAITS:
            scores[t] = round(0.5 + (scores[t] - 0.5) * 0.4, 2)
            rationales[t] = f"{rationales[t]} ({COLD_START_NOTE})"

    return scores, rationales


# --------------------------------------------------------------------------- #
# Value-weight derivation (M-d) — reused from the contract's core-value map
# --------------------------------------------------------------------------- #
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


def _value_weights(req: SimulateRequest) -> ValueWeights:
    vw = ValueWeights()
    if req.profile and req.profile.core_values:
        for value in req.profile.core_values:
            dim = _VALUE_MAP.get(value.strip().lower())
            if dim:
                setattr(vw, dim, getattr(vw, dim) + 1.5)
    return vw


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def _attach(persona: Persona, **kwargs: Any) -> None:
    """Attach extra (non-wire) mind-model data as live attributes.

    Kept off the ``Persona`` schema so ``model_dump()`` / the ``world_ready``
    payload stay exactly per the api-contract, while BE-Sim can still read the
    richer belief model directly off the persona object.
    """
    for key, value in kwargs.items():
        object.__setattr__(persona, key, value)


def _set_big_five(
    persona: Persona, scores: dict[str, float], rationale: dict[str, str]
) -> None:
    persona.big_five = {t: float(scores[t]) for t in BIG_FIVE_TRAITS}
    _attach(persona, big_five_rationale=rationale)


def _profile_is_informative(profile: ProfileInput) -> bool:
    """True when the profile carries at least one substantive behavioural signal."""
    return any(
        [
            profile.occupation,
            profile.decision_style,
            profile.risk_tolerance is not None,
            bool(profile.core_values),
            profile.age is not None,
            profile.city,
        ]
    )


def _infer_options(decision: str) -> tuple[str, str]:
    """Infer a neutral status-quo vs. change option pair from the decision text.

    Deliberately generic: option detail is BE-Engine's job; here we only need
    two distinguishable labels so the world boots from a bare decision (ALG-01).
    """
    low = decision.lower()
    change_verbs = ("quit", "leave", "move", "switch", "start", "accept", "take", "join", "辞职", "搬家", "换", "接受")
    if any(v in low for v in change_verbs):
        return ("Keep things as they are", "Go ahead with the change")
    return ("Option A: don't change", "Option B: make the change")


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    return s or "x"


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


__all__ = ["build_world", "BIG_FIVE_TRAITS", "COLD_START_NOTE"]
