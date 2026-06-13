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

// The 5 fixed metric dimensions, each 0-100.
export interface MetricPoint {
  branch: Branch;
  month: number;
  economic: number;
  career: number;
  relationship: number;
  mental: number;
  autonomy: number;
  supporting_event_ids: string[];
}

export interface BranchPoint {
  month: number;
  metric: string;
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
  personas: Persona[];
  events: TimelineEvent[];
  metrics: MetricPoint[];
  branch_points: BranchPoint[];
  credibility: CredibilityCard | null;
  recommendation: Recommendation | null;
  created_at: string;
}

// --- Request shape for POST /api/simulate ---

export type SimMode = "quick" | "medium" | "heavy";

export interface ValueWeights {
  economic: number;
  career: number;
  relationship: number;
  mental: number;
  autonomy: number;
}

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
  | "branchA"
  | "branchB"
  | "scoring"
  | "done";

export interface StatusEvent {
  phase: StreamPhase;
  message: string;
  progress: number; // 0..1
}

// The 5 fixed metric dimension keys.
export const METRIC_KEYS = [
  "economic",
  "career",
  "relationship",
  "mental",
  "autonomy",
] as const;

export type MetricKey = (typeof METRIC_KEYS)[number];

export const METRIC_LABELS: Record<MetricKey, string> = {
  economic: "Economic",
  career: "Career",
  relationship: "Relationship",
  mental: "Mental",
  autonomy: "Autonomy",
};
