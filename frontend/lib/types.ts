// Lynsea shared types — must match the backend API contract exactly.

export type Branch = "A" | "B";

export interface Big5 {
  O: number; // openness, 0-10
  C: number; // conscientiousness, 0-10
  E: number; // extraversion, 0-10
  A: number; // agreeableness, 0-10
  N: number; // neuroticism, 0-10
}

export type Stance = "supportive" | "opposed" | "neutral" | "unknown";

export interface Persona {
  id: string;
  name: string;
  role: string;
  big5: Big5;
  decision_style: string;
  risk_tolerance: number;
  influence_weight: number;
  stance: Stance;
  key_concerns: string[];
  is_default_inferred: boolean;
}

export type Polarity = "higher_is_better" | "lower_is_better";

// A per-decision, dynamically generated dimension (4–8 per simulation). The
// fixed-5 model is gone; charts/scores key off `dimensions` + `scores[dim.id]`.
export interface Dimension {
  id: string;
  label: string;
  description: string;
  polarity: Polarity;
}

export type EventKind = "skeleton" | "perturbation" | "exogenous";

export interface TimelineEvent {
  id: string;
  branch: Branch;
  month: number;
  title: string;
  description: string;
  kind: EventKind;
  is_shared_exogenous: boolean;
  shared_event_id: string | null;
  involved_personas: string[];
  evidence: string | null;
}

// Per-month scores for one branch. `scores` is keyed by `Dimension.id`, each
// value 0–100. The number of keys is dynamic (matches `SimResult.dimensions`).
export interface MetricPoint {
  branch: Branch;
  month: number;
  scores: Record<string, number>;
  supporting_event_ids: string[];
}

export interface BranchPoint {
  month: number;
  dimension: string; // Dimension.id (was the fixed `metric` field)
  magnitude: number;
  description: string;
  cause_chain: string;
}

export interface CredibilityCard {
  overall: number;
  data_sufficiency: number;
  causal_confidence: number;
  event_plausibility: number;
  notes: string[];
  low_confidence_personas: string[];
}

export interface Recommendation {
  text: string;
  favored_branch: "A" | "B" | "tie";
}

export interface SimResult {
  sim_id: string;
  decision: string;
  options: [string, string];
  mode: string;
  seed: number;
  dimensions: Dimension[];
  personas: Persona[];
  events: TimelineEvent[];
  metrics: MetricPoint[];
  branch_points: BranchPoint[];
  credibility: CredibilityCard | null;
  recommendation: Recommendation | null;
  created_at: string;
}

// --- Clarification (POST /api/clarify) ---

export interface AffectedPersonHint {
  name: string;
  role: string;
  suggested_stance: string;
}

export interface ValuePrompt {
  dim_hint: string;
  question: string;
}

export interface ClarificationPlan {
  suggested_options: string[];
  affected_people: AffectedPersonHint[];
  key_factors: string[];
  value_prompts: ValuePrompt[];
  constraints: string[];
  followup_questions: string[];
}

export interface ClarifyRequest {
  decision: string;
  prior?: ClarificationPlan | null;
  note?: string | null;
}

// --- Request shape for POST /api/simulate ---

export type SimMode = "quick" | "medium" | "heavy";

// Value weights are keyed by `Dimension.id` (default neutral = 5), since the
// dimension set is generated per-decision and only known after the run starts.
export type ValueWeights = Record<string, number>;

export interface SimulateRequest {
  decision: string;
  options: [string, string];
  affected_people?: string[];
  mode?: SimMode;
  values?: ValueWeights;
  seed?: number;
}

// --- SSE stream phases ---

export type StreamPhase =
  | "clarify"
  | "personas"
  | "backbone"
  | "dimensions"
  | "branchA"
  | "branchB"
  | "scoring"
  | "done";

export interface StatusEvent {
  phase: StreamPhase;
  message: string;
  progress: number; // 0..1
}
