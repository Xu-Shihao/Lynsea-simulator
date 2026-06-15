"""Pydantic v2 models for the Lynsea API contract.

Field names here are the **authoritative wire shape** and match
``docs/api-contract.md`` exactly. Two groups live in this file:

1. **Request models** — what `POST /api/simulate` accepts.
2. **Event payloads** — the ``data:`` JSON for every SSE ``event:`` type.
3. **Domain models** — `World`, `Persona`, `TimelineEvent`, `Metric`,
   `ForkPoint`, `BranchScore`, `Credibility`, `Recommendation`, `SimResult`,
   `ValueWeights` — the objects the §5 interfaces pass between modules.

Several event payloads reuse the domain models directly (e.g. `timeline_event`'s
data *is* a `TimelineEvent`). Where the event exposes only a subset (e.g.
`world_ready` exposes a reduced persona view), a dedicated payload model is
defined.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

# Fixed 5 metric dimensions (api-contract: "Metric dimensions (fixed, 5)").
Dimension = Literal["economic", "career", "relationships", "mental_health", "autonomy"]
DIMENSIONS: tuple[Dimension, ...] = (
    "economic",
    "career",
    "relationships",
    "mental_health",
    "autonomy",
)

Branch = Literal["A", "B", "C"]
Mode = Literal["quick", "medium", "heavy"]
Confidence = Literal["high", "low"]
EventKind = Literal["skeleton", "perturbation"]
Leaning = Literal["A", "B", "neither"]


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #
class ProfileInput(BaseModel):
    """Optional decision-maker profile (api-contract `profile`)."""

    age: Optional[int] = None
    city: Optional[str] = None
    occupation: Optional[str] = None
    risk_tolerance: Optional[int] = Field(default=None, ge=0, le=10)
    core_values: list[str] = Field(default_factory=list)
    decision_style: Optional[str] = None


class SocialCircleMember(BaseModel):
    """Optional social-circle entry (api-contract `social_circle[]`)."""

    role: str
    influence_weight: int = Field(default=5, ge=0, le=10)
    stance_on_decision: Optional[str] = None
    key_concerns: list[str] = Field(default_factory=list)


class SimulateRequest(BaseModel):
    """Body of ``POST /api/simulate``.

    Only ``decision`` is required. ``options`` is inferred from the decision
    when omitted; sparse ``profile``/``social_circle`` fall back to defaults
    (and affected personas are flagged low-confidence — `ALG-04`).
    ``seed`` makes the run reproducible (`NFR-01` / `ALG-20`).
    """

    decision: str = Field(min_length=1)
    mode: Mode = "quick"
    options: Optional[list[str]] = None
    profile: Optional[ProfileInput] = None
    social_circle: list[SocialCircleMember] = Field(default_factory=list)
    seed: Optional[int] = None


class WhatIfRequest(BaseModel):
    """Body of ``POST /api/whatif`` (P1)."""

    run_id: str
    from_month: int = Field(ge=0)
    branch: Branch
    change: str


class ValueWeights(BaseModel):
    """Per-dimension importance weights for value-weighted scoring (`M-d`).

    Defaults to equal weighting. ``normalized()`` returns weights summing to 1.
    """

    economic: float = 1.0
    career: float = 1.0
    relationships: float = 1.0
    mental_health: float = 1.0
    autonomy: float = 1.0

    def as_dict(self) -> dict[str, float]:
        return {dim: getattr(self, dim) for dim in DIMENSIONS}

    def normalized(self) -> dict[str, float]:
        raw = self.as_dict()
        total = sum(raw.values()) or 1.0
        return {dim: w / total for dim, w in raw.items()}


# --------------------------------------------------------------------------- #
# Domain models (passed between §5 interfaces)
# --------------------------------------------------------------------------- #
class Persona(BaseModel):
    """A digital twin in the simulated world.

    The ``world_ready`` event exposes only ``id/role/influence_weight/
    confidence`` (see :class:`PersonaPublic`); the rest is internal state the
    simulation/scoring modules consume.
    """

    id: str
    role: str
    influence_weight: int = Field(default=5, ge=0, le=10)
    confidence: Confidence = "low"
    stance_on_decision: Optional[str] = None
    key_concerns: list[str] = Field(default_factory=list)
    # Big-Five inferred from behaviour (ALG-02); 0..1 each. Optional in Wave 1.
    big_five: dict[str, float] = Field(default_factory=dict)
    # True when built from population defaults (cold start) -> must be flagged
    # "信息有限" in the UI (ALG-04).
    cold_start: bool = False

    def public(self) -> "PersonaPublic":
        # ALG-04 / FE-23: surface the bilingual cold-start note in world_ready so
        # the UI/QA can flag "信息有限 / limited info" personas. personas.py
        # attaches the note as a live attribute (``cold_start_note``); fall back
        # to the canonical bilingual string if it isn't present.
        note: Optional[str] = None
        if self.cold_start:
            note = getattr(self, "cold_start_note", None) or (
                "信息有限，仅供参考 / limited info — built from group defaults"
            )
        return PersonaPublic(
            id=self.id,
            role=self.role,
            influence_weight=self.influence_weight,
            confidence=self.confidence,
            cold_start=self.cold_start,
            note=note,
        )


class World(BaseModel):
    """Seeded world state produced by `build_world` (`S2`/`S3`)."""

    run_id: str
    decision: str
    mode: Mode
    seed: int
    options: dict[str, str]  # {"A": "...", "B": "..."}
    personas: list[Persona] = Field(default_factory=list)
    values: ValueWeights = Field(default_factory=ValueWeights)


class TimelineEvent(BaseModel):
    """One life event on a branch timeline. Wire shape == `timeline_event` data."""

    branch: Branch
    event_id: str  # convention: "{branch}-m{month}-{n}"
    month: int
    kind: EventKind
    title: str
    detail: str
    personas: list[str] = Field(default_factory=list)


class Metric(BaseModel):
    """One datapoint for one dimension curve. Wire shape == `metric` data.

    Must reference >= 1 evidence event (`ALG-40`).
    """

    branch: Branch
    month: int
    dim: Dimension
    score: float = Field(ge=0, le=100)
    evidence_event_ids: list[str] = Field(default_factory=list)


class SimResult(BaseModel):
    """Output of `run_simulation` for a single branch (internal aggregate)."""

    branch: Branch
    events: list[TimelineEvent] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)


class ForkPoint(BaseModel):
    """Where two branches diverge sharply. Wire shape == `fork_point` data."""

    month: int
    magnitude: float = Field(ge=0, le=100)
    title: str
    explanation: str
    dims: list[Dimension] = Field(default_factory=list)


class BranchScore(BaseModel):
    """Final per-branch score. Wire shape == `branch_score` data."""

    branch: Branch
    total: float = Field(ge=0, le=100)
    breakdown: dict[str, float]  # dim -> 0..100
    weighted: bool = True


class CredibilityBreakdown(BaseModel):
    data_sufficiency: int = Field(ge=0, le=100)
    causal_confidence: int = Field(ge=0, le=100)
    event_plausibility: int = Field(ge=0, le=100)


class Credibility(BaseModel):
    """Credibility card. Wire shape == `credibility` data (`SYS-17`, `ALG-42`)."""

    overall: int = Field(ge=0, le=100)
    breakdown: CredibilityBreakdown
    notes: str


class Recommendation(BaseModel):
    """Probabilistic recommendation. Wire shape == `recommendation` data.

    Copy MUST be probabilistic, never deterministic (`SYS-15`).
    """

    leaning: Leaning
    rationale: str
    guardrail: str


# --------------------------------------------------------------------------- #
# Event payloads that are NOT a bare domain model
# --------------------------------------------------------------------------- #
class RunStartedData(BaseModel):
    run_id: str
    mode: Mode
    branches: list[str]


class ClarifyQuestion(BaseModel):
    id: str
    text: str


class ClarifyData(BaseModel):
    needs_answer: bool
    questions: list[ClarifyQuestion] = Field(default_factory=list)


class PersonaPublic(BaseModel):
    """Reduced persona view emitted in ``world_ready``."""

    id: str
    role: str
    influence_weight: int
    confidence: Confidence
    # ALG-04 / FE-23: cold-start personas built from group defaults are flagged
    # here with a bilingual "信息有限 / limited info" note. Optional + defaulted
    # so non-cold-start personas and existing contract tests are unaffected.
    cold_start: bool = False
    note: Optional[str] = None


class OptionsData(BaseModel):
    A: str
    B: str


class WorldReadyData(BaseModel):
    personas: list[PersonaPublic]
    options: OptionsData
    # ALG-04 / FE-23: top-level bilingual annotation surfaced whenever the world
    # contains any cold-start persona, so the "信息有限 / limited info" note is a
    # direct, machine-discoverable string in the world_ready payload (not buried
    # inside each persona). Auto-derived from the personas; orchestrator does not
    # need to set it. Stays None (omitted is fine for back-compat) otherwise.
    note: Optional[str] = None

    @model_validator(mode="after")
    def _surface_cold_start_note(self) -> "WorldReadyData":
        if self.note is None and any(p.cold_start for p in self.personas):
            self.note = next(
                (p.note for p in self.personas if p.cold_start and p.note),
                "信息有限，仅供参考 / limited info — built from group defaults",
            )
        return self


class ErrorData(BaseModel):
    message: str
    recoverable: bool = True


class DoneData(BaseModel):
    run_id: str
