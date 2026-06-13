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

# Fixed five metric dimensions (0-100).
METRIC_DIMS = ["economic", "career", "relationship", "mental", "autonomy"]

# Default value-importance weights (0-10), used for the M-d recommendation.
DEFAULT_VALUES: Dict[str, float] = {d: 5.0 for d in METRIC_DIMS}


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
    economic: float = Field(ge=0, le=100)
    career: float = Field(ge=0, le=100)
    relationship: float = Field(ge=0, le=100)
    mental: float = Field(ge=0, le=100)
    autonomy: float = Field(ge=0, le=100)
    # ALG-40: every score links to >= 1 supporting event.
    supporting_event_ids: List[str] = Field(default_factory=list)


class BranchPoint(BaseModel):
    month: int
    metric: str
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
    personas: List[Persona] = Field(default_factory=list)
    events: List[TimelineEvent] = Field(default_factory=list)
    metrics: List[MetricPoint] = Field(default_factory=list)
    branch_points: List[BranchPoint] = Field(default_factory=list)
    credibility: Optional[CredibilityCard] = None
    recommendation: Optional[Recommendation] = None
    created_at: str
