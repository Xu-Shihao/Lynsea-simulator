"""Digital-twin persona construction (ALG-02 / ALG-04 / NFR-01).

Builds the user ("You", role self) plus one persona per affected person from the
minimal free-text input. Big5 + behavioral traits are INFERRED from the
description via Claude (never asked as numbers). If the LLM is unavailable or a
field is missing, we fall back to deterministic population defaults derived from
random.Random(seed) and flag the persona with is_default_inferred=True.

Persona ids are deterministic and stable for the same decision+seed.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional

from .. import config
from ..contracts import Big5, Persona
from .common import slugify

_PERSONA_SYSTEM = (
    "You are a behavioral modeler. Infer a concise psychological twin from a short "
    "description. Output STRICT JSON only, no prose. Never ask the user for numbers."
)

_STANCES = ("supportive", "opposed", "neutral", "unknown")
_STYLES = ("analytical", "intuitive", "cautious", "spontaneous", "consensus-seeking")


def _coerce_float(value: object, default: float, lo: float = 0.0, hi: float = 10.0) -> float:
    """Coerce a possibly-bad LLM value into a float within [lo, hi]."""
    try:
        f = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    if f < lo:
        return lo
    if f > hi:
        return hi
    return f


def _default_big5(rng: random.Random) -> Big5:
    """Population-average-ish Big5 with mild deterministic jitter."""
    base = 5.0
    return Big5(
        O=round(base + rng.uniform(-1.5, 1.5), 1),
        C=round(base + rng.uniform(-1.5, 1.5), 1),
        E=round(base + rng.uniform(-1.5, 1.5), 1),
        A=round(base + rng.uniform(-1.5, 1.5), 1),
        N=round(base + rng.uniform(-1.5, 1.5), 1),
    )


def _default_persona(pid: str, name: str, role: str, rng: random.Random) -> Persona:
    """Deterministic cold-start persona (ALG-04)."""
    return Persona(
        id=pid,
        name=name,
        role=role,
        big5=_default_big5(rng),
        decision_style=_STYLES[rng.randrange(len(_STYLES))],
        risk_tolerance=round(5.0 + rng.uniform(-2.0, 2.0), 1),
        influence_weight=round(5.0 + rng.uniform(-2.0, 2.0), 1) if role != "self" else 8.0,
        stance="unknown",
        key_concerns=[],
        is_default_inferred=True,
    )


def _persona_from_llm(
    raw: object, pid: str, name: str, role: str, rng: random.Random
) -> Persona:
    """Validate an LLM dict into a Persona, filling defaults for missing fields.

    If the LLM payload is unusable, returns a deterministic default persona.
    """
    if not isinstance(raw, dict):
        return _default_persona(pid, name, role, rng)

    big5_raw = raw.get("big5") or {}
    defaults = _default_big5(rng)
    missing = False

    def _b5(key: str, fallback: float) -> float:
        nonlocal missing
        if not isinstance(big5_raw, dict) or key not in big5_raw:
            missing = True
            return fallback
        return _coerce_float(big5_raw.get(key), fallback)

    big5 = Big5(
        O=_b5("O", defaults.O),
        C=_b5("C", defaults.C),
        E=_b5("E", defaults.E),
        A=_b5("A", defaults.A),
        N=_b5("N", defaults.N),
    )

    style = raw.get("decision_style")
    if not isinstance(style, str) or not style.strip():
        style = _STYLES[rng.randrange(len(_STYLES))]
        missing = True

    stance = raw.get("stance")
    if stance not in _STANCES:
        stance = "unknown"

    concerns_raw = raw.get("key_concerns")
    concerns: List[str] = []
    if isinstance(concerns_raw, list):
        concerns = [str(c).strip() for c in concerns_raw if str(c).strip()][:4]

    risk = raw.get("risk_tolerance")
    if risk is None:
        missing = True
    influence = raw.get("influence_weight")
    if influence is None:
        missing = True

    return Persona(
        id=pid,
        name=name,
        role=role,
        big5=big5,
        decision_style=style.strip(),
        risk_tolerance=_coerce_float(risk, 5.0),
        influence_weight=_coerce_float(influence, 8.0 if role == "self" else 5.0),
        stance=stance,
        key_concerns=concerns,
        # If core numeric fields were absent, treat as partially defaulted.
        is_default_inferred=missing,
    )


def _persona_id(role: str, name: str, used: Dict[str, int]) -> str:
    """Stable, unique persona id. user -> p_user; others -> p_<slug>[_n]."""
    if role == "self":
        return "p_user"
    base = "p_" + slugify(name, "person")
    if base not in used:
        used[base] = 0
        return base
    used[base] += 1
    return "%s_%d" % (base, used[base])


def build_personas(
    decision: str,
    options: List[str],
    affected_people: List[str],
    seed: int,
    mode: str = "quick",
) -> List[Persona]:
    """Build the user + social-circle twins (built ONCE, shared by both branches).

    Quick mode caps the circle so total personas stay in the 3-5 range.
    """
    rng = random.Random(seed)
    used: Dict[str, int] = {}

    # Cap affected people for quick mode so total personas land in 3-5.
    people = [p for p in (affected_people or []) if (p or "").strip()]
    if (mode or "quick").lower() == "quick":
        people = people[:4]

    specs = [("You", "self", "")]
    for person in people:
        # Treat the free-text entry as both the display name and the description.
        name = person.strip()
        specs.append((name, _infer_role(name), name))

    personas: List[Persona] = []
    for name, role, descr in specs:
        pid = _persona_id(role, name, used)
        # Per-persona deterministic RNG so default-fallback is stable & isolated.
        prng = random.Random("%d:%s" % (seed, pid))
        persona = _build_one(decision, options, name, role, descr, pid, prng)
        personas.append(persona)
    return personas


def _infer_role(name: str) -> str:
    """Heuristic role label from the person description text."""
    low = name.lower()
    for key, role in (
        ("partner", "partner"), ("spouse", "partner"), ("wife", "partner"),
        ("husband", "partner"), ("girlfriend", "partner"), ("boyfriend", "partner"),
        ("mom", "parent"), ("mother", "parent"), ("dad", "parent"),
        ("father", "parent"), ("parent", "parent"),
        ("kid", "child"), ("son", "child"), ("daughter", "child"), ("child", "child"),
        ("boss", "manager"), ("manager", "manager"),
        ("friend", "friend"), ("colleague", "colleague"), ("coworker", "colleague"),
    ):
        if key in low:
            return role
    return "person"


def _build_one(
    decision: str,
    options: List[str],
    name: str,
    role: str,
    descr: str,
    pid: str,
    rng: random.Random,
) -> Persona:
    """Build a single persona, preferring LLM inference, else deterministic default."""
    subject = "the user making this decision" if role == "self" else descr or name
    prompt = (
        "Decision: %s\n"
        "Option A: %s\nOption B: %s\n"
        "Person to model: %s (role: %s)\n\n"
        "Infer this person's psychological twin. Return STRICT JSON with keys: "
        '{"big5":{"O":0-10,"C":0-10,"E":0-10,"A":0-10,"N":0-10},'
        '"decision_style":string,"risk_tolerance":0-10,"influence_weight":0-10,'
        '"stance":"supportive|opposed|neutral|unknown","key_concerns":[up to 4 short strings]}. '
        "stance/influence are relative to the user's decision. JSON only."
        % (decision, options[0], options[1], subject, role)
    )
    raw: Optional[object] = None
    try:
        raw = config.complete_json(
            prompt, system=_PERSONA_SYSTEM, max_tokens=400, temperature=0.4
        )
    except Exception:
        raw = None

    if raw is None:
        return _default_persona(pid, name, role, rng)
    return _persona_from_llm(raw, pid, name, role, rng)
