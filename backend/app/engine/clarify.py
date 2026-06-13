"""LLM-generated, iterative "Refine your world" clarification (Phase 5).

`generate_clarification(decision, prior, note)` returns a `ClarificationPlan`
(suggested options, candidate affected people with inferred stance, key factors,
value-priority prompts, constraints, follow-up questions). It is reached only
through `config.complete_json`; on the stub path (no key / invalid payload) it
falls back to a deterministic keyword-based builder so tests pass with no key.

Refine rounds: when a `prior` plan and a free-text `note` are supplied, the note
is folded into the plan's constraints (stub) so the user can iterate.
"""
from __future__ import annotations

from typing import Any, List, Optional

from .. import config
from ..contracts import (
    AffectedPersonHint,
    ClarificationPlan,
    ValuePrompt,
)

_CLARIFY_SYSTEM = (
    "You help a person frame a personal decision before simulating it. Given the "
    "raw decision, propose the two clearest options, the people likely affected "
    "(with an inferred stance), the key factors, value-priority prompts, "
    "constraints, and follow-up questions. Output STRICT JSON only."
)

# Person keywords -> role label (mirrors personas._infer_role, kept local so the
# stub is self-contained).
_ROLE_KEYWORDS = (
    ("partner", "partner"), ("spouse", "partner"), ("wife", "partner"),
    ("husband", "partner"), ("girlfriend", "partner"), ("boyfriend", "partner"),
    ("mom", "parent"), ("mother", "parent"), ("dad", "parent"),
    ("father", "parent"), ("parent", "parent"), ("family", "family"),
    ("kid", "child"), ("son", "child"), ("daughter", "child"), ("child", "child"),
    ("boss", "manager"), ("manager", "manager"), ("team", "colleague"),
    ("friend", "friend"), ("colleague", "colleague"), ("coworker", "colleague"),
)

# Decision keyword -> (factor, (value dim hint, prompt)).
_KEYWORD_FACTORS = {
    "quit": ("Income stability while between roles", ("economic", "How much does financial security matter right now?")),
    "startup": ("Runway and personal financial risk", ("economic", "How much short-term financial risk can you absorb?")),
    "job": ("Career trajectory and day-to-day workload", ("career", "How important is career growth versus stability?")),
    "school": ("Time and money invested versus future payoff", ("career", "How much do long-term prospects outweigh short-term cost?")),
    "study": ("Time and money invested versus future payoff", ("career", "How much do long-term prospects outweigh short-term cost?")),
    "relocate": ("Distance from your current support network", ("relationship", "How much do nearby relationships matter to you?")),
    "move": ("Distance from your current support network", ("relationship", "How much do nearby relationships matter to you?")),
    "abroad": ("Adapting to a new country and culture", ("autonomy", "How much do you value independence and a fresh start?")),
    "marry": ("Long-term commitment and shared plans", ("relationship", "How central is this relationship to your future?")),
    "breakup": ("Emotional impact and independence", ("mental", "How much weight do you give your own wellbeing here?")),
    "partner": ("Alignment with your partner's plans", ("relationship", "How much should your partner's preference weigh?")),
    "stress": ("Sustainable workload and burnout risk", ("mental", "How much does day-to-day wellbeing matter?")),
    "invest": ("Risk tolerance and time horizon", ("economic", "How comfortable are you with financial volatility?")),
    "travel": ("Time away versus routine and savings", ("mental", "How much do you value new experiences?")),
}


def _stub_options(decision: str) -> List[str]:
    """Two distinct, decision-flavored options."""
    low = (decision or "").lower()
    for kw, (yes, no) in (
        ("quit", ("Quit and move on", "Stay in the current role")),
        ("relocate", ("Relocate", "Stay where you are")),
        ("move", ("Make the move", "Stay put")),
        ("abroad", ("Move abroad", "Stay home")),
        ("school", ("Go back to school", "Keep working")),
        ("startup", ("Start the venture", "Keep the steady path")),
        ("marry", ("Commit", "Wait")),
        ("breakup", ("End the relationship", "Stay together")),
        ("job", ("Take the new job", "Keep the current one")),
        ("invest", ("Make the investment", "Hold off")),
    ):
        if kw in low:
            return [yes, no]
    return ["Go ahead with it", "Hold off for now"]


def _stub_affected(decision: str) -> List[AffectedPersonHint]:
    low = (decision or "").lower()
    hints: List[AffectedPersonHint] = []
    seen: set = set()
    for kw, role in _ROLE_KEYWORDS:
        if kw in low and role not in seen:
            seen.add(role)
            hints.append(AffectedPersonHint(name=kw, role=role, suggested_stance="unknown"))
    return hints


def _stub_plan(decision: str) -> ClarificationPlan:
    """Deterministic keyword-derived plan (no LLM)."""
    low = (decision or "").lower()
    factors: List[str] = []
    prompts: List[ValuePrompt] = []
    seen_dims: set = set()
    for kw, (factor, (dim_hint, question)) in _KEYWORD_FACTORS.items():
        if kw in low:
            if factor not in factors:
                factors.append(factor)
            if dim_hint not in seen_dims:
                seen_dims.add(dim_hint)
                prompts.append(ValuePrompt(dim_hint=dim_hint, question=question))
    if not factors:
        factors = ["The main tradeoff driving this decision"]
    if not prompts:
        prompts = [
            ValuePrompt(dim_hint="mental", question="How much does your own wellbeing matter here?"),
        ]
    followups = [
        "What outcome would make you regret NOT acting?",
        "Who, if anyone, needs to weigh in before you decide?",
    ]
    return ClarificationPlan(
        suggested_options=_stub_options(decision),
        affected_people=_stub_affected(decision),
        key_factors=factors[:5],
        value_prompts=prompts[:5],
        constraints=[],
        followup_questions=followups,
    )


def _from_llm(raw: Any) -> Optional[ClarificationPlan]:
    """Validate an LLM payload into a ClarificationPlan, or None if unusable."""
    if not isinstance(raw, dict):
        return None
    try:
        options = [str(o).strip() for o in (raw.get("suggested_options") or []) if str(o).strip()]
        if len(options) < 2:
            return None

        people: List[AffectedPersonHint] = []
        for p in raw.get("affected_people") or []:
            if isinstance(p, dict) and str(p.get("name") or "").strip():
                people.append(
                    AffectedPersonHint(
                        name=str(p["name"]).strip(),
                        role=str(p.get("role") or "person").strip() or "person",
                        suggested_stance=str(p.get("suggested_stance") or "unknown"),
                    )
                )

        factors = [str(f).strip() for f in (raw.get("key_factors") or []) if str(f).strip()]

        prompts: List[ValuePrompt] = []
        for vp in raw.get("value_prompts") or []:
            if isinstance(vp, dict) and str(vp.get("question") or "").strip():
                prompts.append(
                    ValuePrompt(
                        dim_hint=str(vp.get("dim_hint") or "").strip(),
                        question=str(vp["question"]).strip(),
                    )
                )

        constraints = [str(c).strip() for c in (raw.get("constraints") or []) if str(c).strip()]
        followups = [str(q).strip() for q in (raw.get("followup_questions") or []) if str(q).strip()]

        if not factors or not prompts:
            return None
        return ClarificationPlan(
            suggested_options=options,
            affected_people=people,
            key_factors=factors,
            value_prompts=prompts,
            constraints=constraints,
            followup_questions=followups,
        )
    except Exception:
        return None


def generate_clarification(
    decision: str,
    prior: Optional[ClarificationPlan] = None,
    note: Optional[str] = None,
) -> ClarificationPlan:
    """Generate (or refine) a ClarificationPlan for a raw decision.

    LLM via config.complete_json with a deterministic keyword stub fallback. On a
    refine round (`prior` + `note`), the note is folded into constraints and the
    prior's suggested options/people are carried forward when the LLM is absent.
    """
    refine_hint = ""
    if prior is not None and note:
        refine_hint = (
            "\nThe user refined with this note; incorporate it: %s\n"
            "Prior options were: %s" % (note, prior.suggested_options)
        )

    prompt = (
        "Decision: %s%s\n\n"
        "Return STRICT JSON with keys: "
        '{"suggested_options":[2 short strings],'
        '"affected_people":[{"name":str,"role":str,"suggested_stance":"supportive|opposed|neutral|unknown"}],'
        '"key_factors":[short strings],'
        '"value_prompts":[{"dim_hint":str,"question":str}],'
        '"constraints":[short strings],'
        '"followup_questions":[short strings]}. '
        "JSON only." % (decision or "", refine_hint)
    )
    raw: Optional[Any] = None
    try:
        raw = config.complete_json(prompt, system=_CLARIFY_SYSTEM, max_tokens=800, temperature=0.5)
    except Exception:
        raw = None

    plan = _from_llm(raw)
    if plan is None:
        plan = _stub_plan(decision)
        # On the stub path, carry the prior's confirmed options forward so a
        # refine round does not discard the user's earlier framing.
        if prior is not None and prior.suggested_options:
            plan.suggested_options = list(prior.suggested_options)
            if prior.affected_people:
                plan.affected_people = list(prior.affected_people)

    # Fold the refine note into constraints regardless of LLM/stub origin so the
    # iteration is always visible to the caller.
    if note:
        note_text = note.strip()
        if note_text and note_text not in plan.constraints:
            plan.constraints.append(note_text)

    return plan
