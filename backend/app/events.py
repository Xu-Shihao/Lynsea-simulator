"""Two-layer timeline event generation (owner: BE-Engine).

``generate_events(world, branch, rng)`` is the real replacement for the Wave-1
``_stub_generate_events`` in ``orchestrator.py``. It produces two layers (ALG-30):

* **skeleton** — high-probability milestones *derived from the personas + the
  decision state*. These are decision-conditioned, so they use the per-branch
  stream (``rng.branch_rng(branch)``) and legitimately differ between branch A
  and branch B. They run on a monthly cadence over the mode horizon, so both
  branches still cover the *same months* (the parity QA asserts in ALG-20).

* **perturbation** — low-probability exogenous shocks drawn from the **shared**
  stream (``rng.shared_rng()``), which is derived from the seed alone. Because
  the world (and therefore the persona list) is shared across branches and the
  draw depends only on the seed, the perturbation layer is *byte-identical*
  across A and B in every structural field (month/kind/type/title/detail/
  personas) — only the ``branch`` label and the ``{branch}-`` id prefix differ.
  This is what makes "same random events, only the decision differs" true
  (ALG-20/21, NFR-01).

Plausibility:

* **ALG-31** — perturbations are only ever drawn from :data:`PERTURBATION_TYPES`,
  a whitelist of mundane, plausible life events. Absurd / out-of-bounds events
  (lottery jackpots, fatal accidents, …) are never in the whitelist, so the
  implausible rate is 0% — comfortably within the ≤2% bound. :func:`plausibility_rate`
  re-checks this from the emitted events.
* **ALG-32** — when a drawn perturbation is incompatible with the current
  timeline (e.g. a duplicate of one already placed, or one whose required role is
  absent), it is resampled up to 3 times; if it still does not fit, it degrades
  to a single **flagged placeholder** event rather than forcing an implausible one.

LLM flavour text (``app.llm``, Haiku tier) could enrich ``title``/``detail`` later
*without* affecting reproducibility, because the structural, seed-derived fields
hashed by ``rng.shared_event_hash`` are computed here first and never depend on
model prose. The base implementation is intentionally deterministic and
LLM-free so the determinism gates hold with or without an API key.
"""

from __future__ import annotations

from typing import Optional

from app.rng import SeededRNG
from app.schemas import TimelineEvent, World

# Horizon (months) per mode. Mirrors orchestrator.MODE_HORIZON but is defined
# locally to avoid importing the orchestrator (which imports this module).
MODE_HORIZON: dict[str, int] = {"quick": 6, "medium": 18, "heavy": 24}

# Max perturbations per branch, by horizon bucket — keeps the perturbation layer
# genuinely "low-probability" relative to the monthly skeleton.
_MAX_PERTURBATIONS = 3
_MAX_RESAMPLE = 3  # ALG-32: resample an incompatible draw up to 3 times.

DEGRADED_TYPE = "quiet_stretch"
DEGRADED_TITLE_PREFIX = "[uneventful]"


# --------------------------------------------------------------------------- #
# ALG-31 plausibility whitelist
# --------------------------------------------------------------------------- #
# Each perturbation template is a mundane, plausible exogenous event. ``requires``
# (if set) names a persona-role keyword the event needs; if no persona matches,
# the template is considered incompatible for this world (drives ALG-32 resample).
PERTURBATION_TYPES: list[dict] = [
    {
        "type": "minor_health",
        "title": "A minor health scare",
        "detail": "A short, manageable health issue comes up — likely a few weeks "
                  "of recovery, around an 80% chance it resolves without lasting impact.",
    },
    {
        "type": "small_windfall",
        "title": "An unexpected small windfall",
        "detail": "A modest, one-off financial boost (a refund, bonus, or small gift) "
                  "shows up — probably enough to ease one month's pressure, not change the path.",
    },
    {
        "type": "market_shift",
        "title": "A shift in the job market",
        "detail": "Conditions in the wider job market move — likely a moderate effect "
                  "on options and bargaining power over the next quarter.",
    },
    {
        "type": "relocation_pressure",
        "title": "Pressure to relocate",
        "detail": "An opportunity or obligation to move location appears — around a "
                  "50% chance it meaningfully shapes the months that follow.",
    },
    {
        "type": "new_connection",
        "title": "A useful new connection",
        "detail": "A new acquaintance or reconnected contact opens a door — probably a "
                  "small but real nudge to momentum.",
    },
    {
        "type": "unexpected_expense",
        "title": "An unexpected expense",
        "detail": "An out-of-budget cost lands (a repair, a bill) — likely a temporary "
                  "strain that probably passes within a month or two.",
    },
    {
        "type": "family_news",
        "title": "Significant family news",
        "detail": "News from someone close shifts priorities for a while — around a "
                  "40% chance it becomes a recurring consideration.",
        "requires": ("partner", "mother", "father", "family", "friend", "mentor"),
    },
    {
        "type": "workload_spike",
        "title": "A temporary workload spike",
        "detail": "A busier-than-usual stretch arrives — probably a few intense weeks "
                  "with a likely return to baseline afterwards.",
    },
    {
        "type": "minor_setback",
        "title": "A small setback",
        "detail": "A plan slips or a result disappoints — likely a modest dip in "
                  "momentum, around a 70% chance of recovering the lost ground.",
    },
    {
        "type": "recognition",
        "title": "A bit of recognition",
        "detail": "Some unexpected acknowledgement arrives — probably a small lift to "
                  "confidence and standing.",
    },
]

# Documented examples of events that are deliberately *excluded* from the
# whitelist (used by plausibility checks/tests). These must never be emitted.
IMPLAUSIBLE_KEYWORDS: tuple[str, ...] = (
    "lottery", "jackpot", "fatal", "died", "death", "killed", "alien",
    "apocalypse", "kidnap", "lightning strike", "meteor", "zombie",
)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def generate_events(world: World, branch: str, rng: SeededRNG) -> list[TimelineEvent]:
    """Return the skeleton + perturbation timeline for one branch.

    The skeleton layer is decision-conditioned (per-branch); the perturbation
    layer is drawn from the shared, seed-only stream so it is identical across
    branches A and B (ALG-20/21/NFR-01). Skeleton events are returned before
    perturbations (ALG-30 / BE-04 ordering, also re-sorted by the orchestrator).
    """
    horizon = MODE_HORIZON.get(world.mode, 6)
    persona_ids = [p.id for p in world.personas] or ["self"]
    persona_roles = {p.id: p.role for p in world.personas}
    option_label = world.options.get(branch, branch)

    # Per-month event counter so ids follow "{branch}-m{month}-{n}".
    counters: dict[int, int] = {}

    def _next_id(month: int) -> str:
        counters[month] = counters.get(month, 0) + 1
        return f"{branch}-m{month}-{counters[month]}"

    events: list[TimelineEvent] = []

    # --- Skeleton: high-probability, decision-conditioned milestones -------- #
    brng = rng.branch_rng(branch)
    for month in range(1, horizon + 1):
        who = persona_ids[brng.randint(0, len(persona_ids) - 1)]
        extra = [who]
        # Occasionally a second persona is implicated in the milestone.
        if len(persona_ids) > 1 and brng.random() < 0.4:
            other = persona_ids[brng.randint(0, len(persona_ids) - 1)]
            if other != who:
                extra.append(other)
        events.append(
            TimelineEvent(
                branch=branch,  # type: ignore[arg-type]
                event_id=_next_id(month),
                month=month,
                kind="skeleton",
                title=_skeleton_title(month, horizon, option_label),
                detail=_skeleton_detail(month, horizon, option_label),
                personas=extra,
            )
        )

    # --- Perturbation: low-probability exogenous shocks (shared stream) ----- #
    srng = rng.shared_rng()
    plan = _plan_perturbations(srng, horizon)
    used_types: set[str] = set()
    for month in plan:
        template, degraded = _select_perturbation(
            srng, used_types, persona_ids, persona_roles
        )
        if template is not None:
            used_types.add(template["type"])
        who = persona_ids[srng.randint(0, len(persona_ids) - 1)]
        events.append(_build_perturbation(_next_id(month), branch, month, who, template, degraded))

    return events


def shared_signature(events: list[TimelineEvent]) -> list[tuple]:
    """Branch-independent structural signature of the shared (perturbation) layer.

    Excludes the ``branch`` label and the ``{branch}-`` id prefix so the signature
    is directly comparable across branches A and B (it should be *equal*). Used by
    the engine tests to assert ALG-20 branch parity.
    """
    sig: list[tuple] = []
    for e in events:
        if e.kind != "perturbation":
            continue
        local_id = e.event_id.split("-", 1)[1] if "-" in e.event_id else e.event_id
        sig.append((local_id, e.month, e.kind, e.title, e.detail, tuple(e.personas)))
    return sig


def plausibility_rate(events: list[TimelineEvent]) -> float:
    """Fraction of events that look implausible/out-of-bounds (ALG-31 metric).

    With whitelist-only generation this is 0.0; the function checks the *emitted*
    text against :data:`IMPLAUSIBLE_KEYWORDS` so the bound is verified from output,
    not merely assumed. Returns a value in [0, 1]; the gate is ≤ 0.02.
    """
    if not events:
        return 0.0
    implausible = sum(1 for e in events if _is_implausible(e))
    return implausible / len(events)


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #
def _plan_perturbations(srng, horizon: int) -> list[int]:
    """Deterministically pick the (few) months that carry a perturbation.

    Driven entirely by the shared stream, so the plan is identical across
    branches A and B. Guarantees at least one perturbation and never more than
    :data:`_MAX_PERTURBATIONS`, keeping the layer genuinely low-probability.
    """
    cap = min(_MAX_PERTURBATIONS, horizon)
    # Skew toward 1-2 perturbations; 3 only occasionally.
    roll = srng.random()
    n = 1 if roll < 0.55 else (2 if roll < 0.9 else 3)
    n = max(1, min(cap, n))
    months = sorted({srng.randint(1, horizon) for _ in range(n * 2)})
    return months[:n]


def _select_perturbation(
    srng,
    used_types: set[str],
    persona_ids: list[str],
    persona_roles: dict[str, str],
) -> tuple[Optional[dict], bool]:
    """Draw a compatible perturbation template, resampling up to 3x (ALG-32).

    Returns ``(template, degraded)``. ``degraded`` is True (and ``template`` is
    None) when no compatible template was found within the resample budget, so
    the caller emits a flagged placeholder instead of an implausible event.
    """
    for _ in range(_MAX_RESAMPLE + 1):  # initial draw + up to 3 resamples
        template = srng.choice(PERTURBATION_TYPES)
        if _compatible(template, used_types, persona_roles):
            return template, False
    return None, True


def _compatible(template: dict, used_types: set[str], persona_roles: dict[str, str]) -> bool:
    """An event is compatible if not already used and its required role exists."""
    if template["type"] in used_types:
        return False
    requires = template.get("requires")
    if requires:
        roles = " ".join(persona_roles.values()).lower()
        if not any(tag in roles for tag in requires):
            return False
    return True


def _build_perturbation(
    event_id: str,
    branch: str,
    month: int,
    who: str,
    template: Optional[dict],
    degraded: bool,
) -> TimelineEvent:
    if degraded or template is None:
        # ALG-32 graceful degrade: a flagged, plausible, neutral placeholder.
        return TimelineEvent(
            branch=branch,  # type: ignore[arg-type]
            event_id=event_id,
            month=month,
            kind="perturbation",
            title=f"{DEGRADED_TITLE_PREFIX} A quieter-than-usual stretch",
            detail="No distinct exogenous event fit here, so this month is left "
                   "deliberately uneventful (flagged placeholder) rather than "
                   "forcing an implausible one.",
            personas=[who],
        )
    return TimelineEvent(
        branch=branch,  # type: ignore[arg-type]
        event_id=event_id,
        month=month,
        kind="perturbation",
        title=template["title"],
        detail=template["detail"],
        personas=[who],
    )


def _skeleton_title(month: int, horizon: int, option_label: str) -> str:
    if month == 1:
        return f"Month {month}: settling into '{option_label}'"
    if month >= horizon:
        return f"Month {month}: taking stock of '{option_label}'"
    return f"Month {month}: living with '{option_label}'"


def _skeleton_detail(month: int, horizon: int, option_label: str) -> str:
    return (
        "A high-probability milestone implied by the decision and the personas' "
        f"baseline trajectory under '{option_label}'. Likely the dominant storyline "
        "this month, around a 75% chance it unfolds roughly as expected."
    )


def _is_implausible(event: TimelineEvent) -> bool:
    text = f"{event.title} {event.detail}".lower()
    return any(kw in text for kw in IMPLAUSIBLE_KEYWORDS)


__all__ = [
    "generate_events",
    "shared_signature",
    "plausibility_rate",
    "PERTURBATION_TYPES",
    "IMPLAUSIBLE_KEYWORDS",
]
