/**
 * contract.ts — TypeScript types mirroring docs/api-contract.md (v0.1)
 *
 * This is the SINGLE SOURCE OF TRUTH for all frontend API types.
 * FE-Dashboard and FE-Insight components import ONLY from this file.
 * Do NOT redefine these types in other files.
 *
 * Field names MUST match docs/api-contract.md exactly.
 */

// ─── Request ─────────────────────────────────────────────────────────────────

export type SimulationMode = 'quick' | 'medium' | 'heavy';

export interface UserProfile {
  age: number;
  city: string;
  occupation: string;
  risk_tolerance: number; // 1–10
  core_values: string[];
  decision_style?: string;
}

export interface SocialCircleMember {
  role: string;
  influence_weight: number; // 1–10
  stance_on_decision: 'supportive' | 'neutral' | 'opposed';
  key_concerns?: string[];
}

export interface SimulateRequest {
  decision: string;
  mode: SimulationMode;
  options?: [string, string];      // [Branch A label, Branch B label]
  profile?: UserProfile;
  social_circle?: SocialCircleMember[];
  seed?: number;                    // optional; same seed → reproducible output (NFR-01)
}

// ─── Branch labels ────────────────────────────────────────────────────────────

/** Branches are exactly A and B for MVP. HARD RULE: A = cyan/left, B = amber/right. */
export type Branch = 'A' | 'B';

/** The 5 fixed metric dimensions (docs/api-contract.md §Base). */
export type MetricDim = 'economic' | 'career' | 'relationships' | 'mental_health' | 'autonomy';

// ─── SSE Event payloads ──────────────────────────────────────────────────────

/** run_started — Frontend creates 2 A/B columns. */
export interface RunStartedPayload {
  run_id: string;
  mode: SimulationMode;
  branches: Branch[];         // always ["A", "B"] for MVP
}

/** clarify (optional) — Backend wants clarification; MVP may skip. */
export interface ClarifyQuestion {
  id: string;
  text: string;
}

export interface ClarifyPayload {
  needs_answer: boolean;
  questions: ClarifyQuestion[];
}

/** world_ready — Digital twins + branch option labels ready. */
export interface PersonaInfo {
  id: string;
  role: string;
  influence_weight: number;
  confidence: 'high' | 'low';
}

export interface WorldReadyPayload {
  personas: PersonaInfo[];
  options: Record<Branch, string>;  // e.g. { A: "Stay at job", B: "Join startup" }
}

/** timeline_event — One life event per branch. */
export type TimelineEventKind = 'skeleton' | 'perturbation';

export interface TimelineEventPayload {
  branch: Branch;
  event_id: string;           // format: "{branch}-m{month}-{n}"
  month: number;              // 0 = decision point
  kind: TimelineEventKind;
  title: string;
  detail: string;
  personas: string[];         // list of persona role strings that are involved
}

/** metric — One data point for one dimension curve. */
export interface MetricPayload {
  branch: Branch;
  month: number;
  dim: MetricDim;
  score: number;              // 0–100
  evidence_event_ids: string[]; // must reference ≥1 event (ALG-40)
}

/** fork_point — Where the two branches diverge sharply. */
export interface ForkPointPayload {
  month: number;
  magnitude: number;         // 0–100
  title: string;
  explanation: string;
  dims: MetricDim[];
}

/** branch_score — Final per-branch value-weighted score. */
export interface BranchScorePayload {
  branch: Branch;
  total: number;             // 0–100
  breakdown: Record<MetricDim, number>;
  weighted: boolean;
}

/** credibility — Simulation credibility card (SYS-17, ALG-42). */
export interface CredibilityBreakdown {
  data_sufficiency: number;
  causal_confidence: number;
  event_plausibility: number;
}

export interface CredibilityPayload {
  overall: number;           // 0–100
  breakdown: CredibilityBreakdown;
  notes: string;
}

/** recommendation — Probabilistic leaning. MUST be probabilistic, never deterministic (SYS-15, FE-25). */
export interface RecommendationPayload {
  leaning: Branch | 'neither';
  rationale: string;         // must use "likely", "~N%", never "will/definitely"
  guardrail: string;         // shown for high-risk results
}

/** error — Something failed; frontend shows readable error, not white screen (FE-29). */
export interface ErrorPayload {
  message: string;
  recoverable: boolean;
}

/** done — Stream complete. */
export interface DonePayload {
  run_id: string;
}

// ─── Discriminated union of all SSE events ───────────────────────────────────

export type SSEEventType =
  | 'run_started'
  | 'clarify'
  | 'world_ready'
  | 'timeline_event'
  | 'metric'
  | 'fork_point'
  | 'branch_score'
  | 'credibility'
  | 'recommendation'
  | 'error'
  | 'done';

export type SSEEvent =
  | { type: 'run_started';    payload: RunStartedPayload }
  | { type: 'clarify';        payload: ClarifyPayload }
  | { type: 'world_ready';    payload: WorldReadyPayload }
  | { type: 'timeline_event'; payload: TimelineEventPayload }
  | { type: 'metric';         payload: MetricPayload }
  | { type: 'fork_point';     payload: ForkPointPayload }
  | { type: 'branch_score';   payload: BranchScorePayload }
  | { type: 'credibility';    payload: CredibilityPayload }
  | { type: 'recommendation'; payload: RecommendationPayload }
  | { type: 'error';          payload: ErrorPayload }
  | { type: 'done';           payload: DonePayload };

// ─── Simulation state (output of useSimulation hook) ────────────────────────

export type SimulationStatus = 'idle' | 'connecting' | 'streaming' | 'done' | 'error';

export interface SimulationState {
  /** Whether the stream has started / completed */
  status: SimulationStatus;

  /** From run_started */
  runStarted: RunStartedPayload | null;

  /** From world_ready */
  world: WorldReadyPayload | null;

  /** All timeline events, grouped by branch */
  eventsByBranch: Record<Branch, TimelineEventPayload[]>;

  /** All metric data points, grouped by branch */
  metricsByBranch: Record<Branch, MetricPayload[]>;

  /** All detected fork points */
  forks: ForkPointPayload[];

  /** Branch scores (value-weighted) */
  scores: Record<Branch, BranchScorePayload | null>;

  /** Credibility card */
  credibility: CredibilityPayload | null;

  /** Final recommendation */
  recommendation: RecommendationPayload | null;

  /** Error message if status === 'error' */
  error: string | null;

  /** Total SSE events received (for the streaming pill counter) */
  eventCount: number;
}

// ─── Seed-check response (GET /api/run/{run_id}/seed-check) ─────────────────

export interface SeedCheckResponse {
  shared_event_hash: string;
}

// ─── Health response (GET /api/health) ──────────────────────────────────────

export interface HealthResponse {
  status: 'ok';
  version: string;
}
