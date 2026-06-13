"""Per-branch decision-dependent event generation (ALG-30 / ALG-31 / ALG-32).

Two-layer generation per branch:
  1. Skeleton  — high-probability milestone consequences of the option.
  2. Perturbation — lower-probability secondary effects.
Then the shared exogenous backbone is merged in IDENTICALLY across branches.

A plausibility guard rejects out-of-bounds events (lottery wins, random deaths,
unrelated windfalls). Rejected events are resampled up to 3 times, then
downgraded to a flagged placeholder. The rejection rate feeds event_plausibility.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

from .. import config
from ..contracts import Persona, TimelineEvent
from .common import horizon_for_mode

# Keywords that signal implausible / out-of-bounds events (ALG-31).
_IMPLAUSIBLE_KEYWORDS = (
    "lottery", "jackpot", "lotto", "win the lottery", "wins the lottery",
    "sudden death", "dies suddenly", "random death", "killed", "murdered",
    "alien", "zombie", "apocalypse", "meteor", "magic", "miracle",
    "inherit a fortune", "unexpected fortune", "windfall", "wins a prize",
    "struck by lightning", "plane crash", "kidnapped", "superpower",
)

_SIM_SYSTEM = (
    "You forecast plausible, decision-dependent life events. Stay within ordinary "
    "human plausibility. No lottery wins, random deaths, or unrelated windfalls. "
    "Output STRICT JSON only."
)


def _is_implausible(title: str, description: str) -> bool:
    """Keyword/bounds plausibility check (ALG-31)."""
    blob = ("%s %s" % (title or "", description or "")).lower()
    return any(kw in blob for kw in _IMPLAUSIBLE_KEYWORDS)


def _branch_letter(index: int) -> str:
    return "A" if index == 0 else "B"


class _GenStats:
    """Tracks plausibility resampling for the credibility card."""

    def __init__(self) -> None:
        self.proposed = 0
        self.rejected = 0
        self.downgraded = 0

    @property
    def rejection_rate(self) -> float:
        if self.proposed <= 0:
            return 0.0
        return self.rejected / self.proposed


def _stub_events(
    branch: str,
    option_text: str,
    personas: List[Persona],
    horizon: int,
    rng: random.Random,
) -> List[Dict[str, object]]:
    """Deterministic, persona/option-aware fallback event generator.

    Produces both skeleton and perturbation layers without any LLM. Used whenever
    Claude is unavailable or returns unparseable JSON (BE-12).
    """
    persona_ids = [p.id for p in personas]
    user_id = persona_ids[0] if persona_ids else "p_user"
    others = persona_ids[1:]

    # Skeleton milestones: spread across early-to-mid horizon.
    skel_specs = [
        (max(1, horizon // 6),
         "Commit to: %s" % option_text,
         "You act on the choice and the first concrete consequences appear."),
        (max(2, horizon // 3),
         "Adjusting to the new routine",
         "Daily life reorganizes around the choice; early friction surfaces."),
        (max(3, (horizon * 2) // 3),
         "First tangible results",
         "The decision begins to show measurable effects on your situation."),
    ]
    # Perturbation: lower-probability secondary effects, persona-flavored.
    pert_specs = [
        (max(2, horizon // 2),
         "A second-order ripple",
         "An indirect effect of the choice changes a relationship or expense."),
        (max(4, (horizon * 3) // 4),
         "An unplanned tradeoff",
         "A minor setback tests your commitment to the path."),
    ]

    out: List[Dict[str, object]] = []
    for i, (month, title, desc) in enumerate(skel_specs):
        if month > horizon:
            month = horizon
        involved = [user_id]
        if others and i < len(others):
            involved.append(others[i % len(others)])
        out.append(
            {
                "month": month,
                "title": title,
                "description": desc,
                "kind": "skeleton",
                "involved_personas": involved,
            }
        )
    for i, (month, title, desc) in enumerate(pert_specs):
        if month > horizon:
            month = horizon
        involved = [user_id]
        if others:
            involved.append(others[(i + 1) % len(others)])
        out.append(
            {
                "month": month,
                "title": title,
                "description": desc,
                "kind": "perturbation",
                "involved_personas": involved,
            }
        )
    # Small deterministic jitter so the two branches are not identical in count.
    if rng.random() < 0.5:
        m = min(horizon, max(1, horizon - 1))
        out.append(
            {
                "month": m,
                "title": "Late consolidation",
                "description": "The path settles into a steady state near the horizon.",
                "kind": "perturbation",
                "involved_personas": [user_id],
            }
        )
    return out


def _llm_events(
    branch: str,
    option_text: str,
    decision: str,
    personas: List[Persona],
    horizon: int,
) -> Optional[List[Dict[str, object]]]:
    """Try to generate events via Claude. Returns None on any failure."""
    persona_blurb = "; ".join(
        "%s=%s(%s)" % (p.id, p.name, p.role) for p in personas
    )
    prompt = (
        "Decision: %s\n"
        "Chosen option (branch %s): %s\n"
        "Personas (id=name(role)): %s\n"
        "Horizon: %d months.\n\n"
        "Generate decision-dependent events in TWO layers:\n"
        '  - "skeleton": 2-4 high-probability milestone consequences.\n'
        '  - "perturbation": 1-3 lower-probability secondary effects.\n'
        "Stay plausible (no lottery/death/windfall). "
        "Return STRICT JSON: a list of objects "
        '{"month":1..%d,"title":str,"description":str,'
        '"kind":"skeleton|perturbation","involved_personas":[persona ids]}. '
        "JSON list only."
        % (decision, branch, option_text, persona_blurb, horizon, horizon)
    )
    try:
        raw = config.complete_json(
            prompt, system=_SIM_SYSTEM, max_tokens=1200, temperature=0.7
        )
    except Exception:
        return None
    if not isinstance(raw, list) or not raw:
        return None

    valid_ids = {p.id for p in personas}
    cleaned: List[Dict[str, object]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        desc = str(item.get("description", "")).strip()
        if not title:
            continue
        try:
            month = int(item.get("month", 1))
        except (TypeError, ValueError):
            month = 1
        month = max(1, min(horizon, month))
        kind = item.get("kind")
        if kind not in ("skeleton", "perturbation"):
            kind = "skeleton"
        involved_raw = item.get("involved_personas")
        involved: List[str] = []
        if isinstance(involved_raw, list):
            involved = [str(x) for x in involved_raw if str(x) in valid_ids]
        if not involved and personas:
            involved = [personas[0].id]
        cleaned.append(
            {
                "month": month,
                "title": title,
                "description": desc,
                "kind": kind,
                "involved_personas": involved,
            }
        )
    return cleaned or None


def _guard_and_finalize(
    proposals: List[Dict[str, object]],
    branch: str,
    personas: List[Persona],
    horizon: int,
    rng: random.Random,
    stats: _GenStats,
    id_prefix: str,
) -> List[TimelineEvent]:
    """Apply the plausibility guard (ALG-31/32) and build TimelineEvents.

    Implausible proposals are resampled (re-described) up to 3 times; if still
    implausible they are downgraded to a flagged placeholder event.
    """
    user_id = personas[0].id if personas else "p_user"
    events: List[TimelineEvent] = []
    counter = 0
    for prop in proposals:
        stats.proposed += 1
        title = str(prop.get("title", "")).strip() or "Event"
        desc = str(prop.get("description", "")).strip()
        kind = prop.get("kind", "skeleton")
        month = int(prop.get("month", 1))
        month = max(1, min(horizon, month))
        involved = prop.get("involved_personas") or [user_id]
        evidence: Optional[str] = None

        if _is_implausible(title, desc):
            stats.rejected += 1
            # Resample <= 3 times: synthesize a bounded replacement deterministically.
            replaced = False
            for _ in range(3):
                alt_title = "A grounded development"
                alt_desc = (
                    "A realistic, in-bounds consequence replaces an implausible "
                    "projection at this point in the timeline."
                )
                if not _is_implausible(alt_title, alt_desc):
                    title, desc = alt_title, alt_desc
                    replaced = True
                    break
            if not replaced:
                stats.downgraded += 1
                title = "Flagged projection"
                desc = "An implausible projection was removed."
                evidence = "[flagged: implausible, downgraded]"
            else:
                evidence = "[resampled: original projection was implausible]"

        ev_id = "%s_%02d" % (id_prefix, counter)
        counter += 1
        events.append(
            TimelineEvent(
                id=ev_id,
                branch=branch,
                month=month,
                title=title,
                description=desc,
                kind=str(kind),
                is_shared_exogenous=False,
                shared_event_id=None,
                involved_personas=list(involved),
                evidence=evidence,
            )
        )
    return events


def _backbone_events_for_branch(
    backbone: List[Dict[str, object]], branch: str, personas: List[Persona]
) -> List[TimelineEvent]:
    """Materialize the shared backbone identically into a branch (ALG-20)."""
    user_id = personas[0].id if personas else "p_user"
    out: List[TimelineEvent] = []
    for b in backbone:
        out.append(
            TimelineEvent(
                id="%s_%s" % (branch, b["shared_event_id"]),
                branch=branch,
                month=int(b["month"]),
                title=str(b["title"]),
                description=str(b["description"]),
                kind="exogenous",
                is_shared_exogenous=True,
                shared_event_id=str(b["shared_event_id"]),
                involved_personas=[user_id],
                evidence="shared exogenous backbone",
            )
        )
    return out


def generate_branch_events(
    branch: str,
    option_text: str,
    decision: str,
    personas: List[Persona],
    backbone: List[Dict[str, object]],
    seed: int,
    mode: str,
    stats: _GenStats,
    extra_proposals: Optional[List[Dict[str, object]]] = None,
) -> List[TimelineEvent]:
    """Generate the full event list for one branch.

    Skeleton + perturbation events (LLM or stub) pass through the plausibility
    guard, then the shared backbone is merged in. `extra_proposals` lets tests
    inject candidate events (e.g. an implausible one) into the guard.
    """
    horizon = horizon_for_mode(mode)
    rng = random.Random("%d:%s:%s" % (seed, branch, option_text))

    proposals = _llm_events(branch, option_text, decision, personas, horizon)
    if proposals is None:
        proposals = _stub_events(branch, option_text, personas, horizon, rng)
    if extra_proposals:
        proposals = proposals + list(extra_proposals)

    id_prefix = "ev_%s" % branch
    decision_events = _guard_and_finalize(
        proposals, branch, personas, horizon, rng, stats, id_prefix
    )
    backbone_events = _backbone_events_for_branch(backbone, branch, personas)

    all_events = decision_events + backbone_events
    # Order: skeleton first, then perturbation, then exogenous; stable by month.
    kind_rank = {"skeleton": 0, "perturbation": 1, "exogenous": 2}
    all_events.sort(key=lambda e: (kind_rank.get(e.kind, 3), e.month, e.id))
    return all_events


def make_stats() -> _GenStats:
    """Factory so callers (orchestrator) can own a shared stats object."""
    return _GenStats()
