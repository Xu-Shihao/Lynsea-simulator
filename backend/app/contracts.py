"""Authoritative data models for Lynsea (integration contract).

This module is the SINGLE SOURCE OF TRUTH for the API/data shapes shared by the
backend engine, the API layer, and (via JSON) the frontend. See BUILD_PLAN.md
section 3. Do not change field names without updating BUILD_PLAN.md.

Branch "A" == options[0], branch "B" == options[1].
"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# --- Literal-ish enums kept as plain str for forward-compat with the frontend ---
Branch = str        # "A" | "B"
Stance = str         # "supportive" | "opposed" | "neutral" | "unknown"
EventKind = str      # "skeleton" | "perturbation" | "exogenous"
Mode = str           # "quick" | "medium" | "heavy"
Polarity = str       # "higher_is_better" | "lower_is_better"

# Canonical default dimension ids (the original fixed five). Dimensions are now
# generated per-decision (4-8); this set is the deterministic stub fallback.
METRIC_DIMS = ["economic", "career", "relationship", "mental", "autonomy"]

# Default value-importance weights (0-10), used for the M-d recommendation.
DEFAULT_VALUES: Dict[str, float] = {d: 5.0 for d in METRIC_DIMS}


class Dimension(BaseModel):
    """A single per-decision outcome axis, scored 0-100.

    `polarity` orients the score: higher_is_better => more is good (e.g. career),
    lower_is_better => less is good (e.g. stress). The score itself is always
    0-100; polarity is applied only when aggregating the value-weighted
    recommendation.
    """

    id: str
    label: str
    description: str = ""
    polarity: Polarity = "higher_is_better"

    @field_validator("polarity")
    @classmethod
    def _valid_polarity(cls, v: str) -> str:
        if v not in ("higher_is_better", "lower_is_better"):
            return "higher_is_better"
        return v


# The original five dimensions, used as the deterministic stub fallback so the
# engine never lacks a dimension set when the LLM is unavailable (Phase 1/2).
DEFAULT_DIMENSIONS: List["Dimension"] = [
    Dimension(id="economic", label="Economic", description="Money, income, and financial security.", polarity="higher_is_better"),
    Dimension(id="career", label="Career", description="Professional growth and trajectory.", polarity="higher_is_better"),
    Dimension(id="relationship", label="Relationship", description="Closeness and quality of key relationships.", polarity="higher_is_better"),
    Dimension(id="mental", label="Mental well-being", description="Emotional health, stress, and life satisfaction.", polarity="higher_is_better"),
    Dimension(id="autonomy", label="Autonomy", description="Independence and control over your own path.", polarity="higher_is_better"),
]


class Big5(BaseModel):
    O: float = Field(ge=0, le=10)
    C: float = Field(ge=0, le=10)
    E: float = Field(ge=0, le=10)
    A: float = Field(ge=0, le=10)
    N: float = Field(ge=0, le=10)


class Persona(BaseModel):
    id: str
    name: str
    role: str
    big5: Big5
    decision_style: str
    risk_tolerance: float = Field(ge=0, le=10)
    influence_weight: float = Field(ge=0, le=10)
    stance: Stance = "unknown"
    key_concerns: List[str] = Field(default_factory=list)
    # ALG-04 cold-start flag: True => persona built from population defaults.
    is_default_inferred: bool = False
    # Optional agent-simulation enrichment (multi-agent slice). Beliefs are
    # first-person convictions; theory_of_mind maps other persona ids -> what
    # this persona assumes about them.
    beliefs: List[str] = Field(default_factory=list)
    theory_of_mind: Dict[str, str] = Field(default_factory=dict)


class TimelineEvent(BaseModel):
    id: str
    branch: Branch
    month: int
    title: str
    description: str
    kind: EventKind  # skeleton | perturbation | exogenous
    is_shared_exogenous: bool = False
    shared_event_id: Optional[str] = None
    involved_personas: List[str] = Field(default_factory=list)
    evidence: Optional[str] = None


class MetricPoint(BaseModel):
    branch: Branch
    month: int
    # Dynamic per-decision dimension scores: dim_id -> 0-100. Keyed by every
    # generated Dimension.id for the simulation.
    scores: Dict[str, float] = Field(default_factory=dict)
    # ALG-40: every score links to >= 1 supporting event.
    supporting_event_ids: List[str] = Field(default_factory=list)

    @field_validator("scores")
    @classmethod
    def _scores_in_range(cls, v: Dict[str, float]) -> Dict[str, float]:
        for key, val in (v or {}).items():
            if not (0.0 <= float(val) <= 100.0):
                raise ValueError("score for %r must be within [0, 100]" % key)
        return v


class BranchPoint(BaseModel):
    month: int
    dimension: str  # dim_id (was the fixed `metric`)
    magnitude: float
    description: str
    cause_chain: str


class CredibilityCard(BaseModel):
    overall: float = Field(ge=0, le=100)
    data_sufficiency: float = Field(ge=0, le=100)
    causal_confidence: float = Field(ge=0, le=100)
    event_plausibility: float = Field(ge=0, le=100)
    notes: List[str] = Field(default_factory=list)
    low_confidence_personas: List[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    text: str
    favored_branch: str  # "A" | "B" | "tie"


# --- Clarification ("Refine your world") models ---------------------------
class AffectedPersonHint(BaseModel):
    """A candidate affected person the clarifier inferred from the decision."""

    name: str
    role: str = "person"
    suggested_stance: Stance = "unknown"


class ValuePrompt(BaseModel):
    """A prompt nudging the user to weigh a value/dimension hint."""

    dim_hint: str
    question: str


class ClarificationPlan(BaseModel):
    """LLM-generated (or stubbed) refinement scaffold for a raw decision."""

    suggested_options: List[str] = Field(default_factory=list)
    affected_people: List[AffectedPersonHint] = Field(default_factory=list)
    key_factors: List[str] = Field(default_factory=list)
    value_prompts: List[ValuePrompt] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    followup_questions: List[str] = Field(default_factory=list)


class ClarifyRequest(BaseModel):
    decision: str
    prior: Optional[ClarificationPlan] = None
    note: Optional[str] = None


class SimRequest(BaseModel):
    decision: str
    options: List[str]
    affected_people: List[str] = Field(default_factory=list)
    mode: Mode = "quick"
    values: Optional[Dict[str, float]] = None
    seed: Optional[int] = None

    @field_validator("options")
    @classmethod
    def _exactly_two_options(cls, v: List[str]) -> List[str]:
        if len(v) != 2:
            raise ValueError("MVP requires exactly 2 options")
        if any(not (o or "").strip() for o in v):
            raise ValueError("options must be non-empty strings")
        return v


class SimResult(BaseModel):
    sim_id: str
    decision: str
    options: List[str]
    mode: Mode
    seed: int
    dimensions: List[Dimension] = Field(default_factory=list)
    personas: List[Persona] = Field(default_factory=list)
    events: List[TimelineEvent] = Field(default_factory=list)
    metrics: List[MetricPoint] = Field(default_factory=list)
    branch_points: List[BranchPoint] = Field(default_factory=list)
    credibility: Optional[CredibilityCard] = None
    recommendation: Optional[Recommendation] = None
    created_at: str
