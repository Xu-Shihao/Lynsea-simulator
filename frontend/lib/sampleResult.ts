import type {
  BranchPoint,
  CredibilityCard,
  Dimension,
  MetricPoint,
  Persona,
  Recommendation,
  SimResult,
  TimelineEvent,
} from "./types";

// A rich, valid fixture for the canonical demo case:
// "Should I take the higher-paying but higher-stress job?"
// Branch A = "Take the new job", Branch B = "Stay at my current job".
// 6 months, both branches, dynamic per-decision dimensions (6, mixed polarity),
// branch points keyed by dimension id, a credibility card, a recommendation,
// and an inferred persona. Matches the dynamic-dimension backend contract so
// `?demo=1` renders N curves with no backend.

// Six generated dimensions for this decision (mixed polarity: `stress_load`
// is lower_is_better, exercising the polarity-aware composite).
const dimensions: Dimension[] = [
  {
    id: "economic",
    label: "Economic Security",
    description: "Income, savings runway, and financial stability.",
    polarity: "higher_is_better",
  },
  {
    id: "career",
    label: "Career Trajectory",
    description: "Growth, skills, and advancement opportunity.",
    polarity: "higher_is_better",
  },
  {
    id: "relationship",
    label: "Relationship Health",
    description: "Quality of time and connection with your partner.",
    polarity: "higher_is_better",
  },
  {
    id: "mental",
    label: "Mental Wellbeing",
    description: "Energy, mood, and overall psychological health.",
    polarity: "higher_is_better",
  },
  {
    id: "stress_load",
    label: "Stress Load",
    description: "Sustained pressure and overwork (lower is healthier).",
    polarity: "lower_is_better",
  },
  {
    id: "autonomy",
    label: "Autonomy",
    description: "Control over your time and how you work.",
    polarity: "higher_is_better",
  },
];

const personas: Persona[] = [
  {
    id: "p_self",
    name: "You",
    role: "The decision-maker",
    big5: { O: 7, C: 8, E: 5, A: 6, N: 6 },
    decision_style: "Analytical, weighs long-term tradeoffs",
    risk_tolerance: 6,
    influence_weight: 10,
    stance: "neutral",
    key_concerns: ["Financial security", "Burnout", "Long-term growth"],
    is_default_inferred: false,
  },
  {
    id: "p_partner",
    name: "Maya",
    role: "Your partner",
    big5: { O: 6, C: 7, E: 6, A: 8, N: 4 },
    decision_style: "Collaborative, values stability",
    risk_tolerance: 4,
    influence_weight: 8,
    stance: "neutral",
    key_concerns: ["Time together", "Your stress levels", "Shared finances"],
    is_default_inferred: false,
  },
  {
    id: "p_mother",
    name: "Your mother",
    role: "Close family",
    big5: { O: 4, C: 7, E: 5, A: 7, N: 5 },
    decision_style: "Cautious, security-oriented",
    risk_tolerance: 3,
    influence_weight: 5,
    stance: "supportive",
    key_concerns: ["Your wellbeing", "Job security"],
    // Limited info provided — defaults inferred. Surfaced as "directional only".
    is_default_inferred: true,
  },
];

// Shared exogenous event that appears in BOTH branches (same shared_event_id).
const SHARED_MARKET = "exo_market_downturn";

const events: TimelineEvent[] = [
  // ---- Branch A: Take the new job ----
  {
    id: "a_m0_start",
    branch: "A",
    month: 0,
    title: "Sign the offer & onboard",
    description:
      "You accept the new role. The compensation bump is real, but so is the steeper ramp — new domain, new team, higher expectations from day one.",
    kind: "skeleton",
    is_shared_exogenous: false,
    shared_event_id: null,
    involved_personas: ["p_self"],
    evidence:
      "Offer letter indicates a ~28% base increase plus equity; onboarding plan references an aggressive 90-day delivery target.",
  },
  {
    id: "a_m1_ramp",
    branch: "A",
    month: 1,
    title: "Intense ramp-up",
    description:
      "Long hours as you absorb the codebase and politics. Energy is high but evenings are mostly work. Maya notices the shift.",
    kind: "perturbation",
    is_shared_exogenous: false,
    shared_event_id: null,
    involved_personas: ["p_self", "p_partner"],
    evidence:
      "Comparable senior transitions report 6-10 weeks before reaching baseline productivity in a new stack.",
  },
  {
    id: "a_m2_first_win",
    branch: "A",
    month: 2,
    title: "First visible win",
    description:
      "You ship a project that gets leadership attention. Confidence and standing rise, though the pace is unrelenting.",
    kind: "perturbation",
    is_shared_exogenous: false,
    shared_event_id: null,
    involved_personas: ["p_self"],
    evidence: null,
  },
  {
    id: "a_m3_market",
    branch: "A",
    month: 3,
    title: "Industry hiring slowdown",
    description:
      "A broad market downturn hits the sector. In the new role you are recent but high-visibility — a mixed position during cuts.",
    kind: "exogenous",
    is_shared_exogenous: true,
    shared_event_id: SHARED_MARKET,
    involved_personas: ["p_self"],
    evidence:
      "Same macro event modeled in both futures so the comparison isolates the decision, not luck.",
  },
  {
    id: "a_m4_strain",
    branch: "A",
    month: 4,
    title: "Relationship strain peaks",
    description:
      "Sustained stress spills into home life. A hard conversation with Maya forces you to set boundaries on working hours.",
    kind: "perturbation",
    is_shared_exogenous: false,
    shared_event_id: null,
    involved_personas: ["p_self", "p_partner"],
    evidence:
      "Maya's stated concern about 'time together' is the most likely pressure point given the hours involved.",
  },
  {
    id: "a_m5_promotion_track",
    branch: "A",
    month: 5,
    title: "Put on a promotion track",
    description:
      "Your manager signals a path to the next level within a year. Career trajectory looks strong; the question is whether the pace is sustainable.",
    kind: "skeleton",
    is_shared_exogenous: false,
    shared_event_id: null,
    involved_personas: ["p_self"],
    evidence: null,
  },

  // ---- Branch B: Stay at current job ----
  {
    id: "b_m0_stay",
    branch: "B",
    month: 0,
    title: "Decline the offer, stay put",
    description:
      "You stay in a familiar role. Comfortable and predictable, but you privately wonder about the ceiling.",
    kind: "skeleton",
    is_shared_exogenous: false,
    shared_event_id: null,
    involved_personas: ["p_self"],
    evidence: null,
  },
  {
    id: "b_m1_steady",
    branch: "B",
    month: 1,
    title: "Steady rhythm",
    description:
      "Work stays manageable. Evenings are free; you and Maya have time together. Little changes financially.",
    kind: "perturbation",
    is_shared_exogenous: false,
    shared_event_id: null,
    involved_personas: ["p_self", "p_partner"],
    evidence: null,
  },
  {
    id: "b_m2_restless",
    branch: "B",
    month: 2,
    title: "Restlessness sets in",
    description:
      "A few months in, the lack of new challenge starts to weigh on you. Motivation dips slightly.",
    kind: "perturbation",
    is_shared_exogenous: false,
    shared_event_id: null,
    involved_personas: ["p_self"],
    evidence:
      "Your profile (high openness, high conscientiousness) is associated with sensitivity to stagnation.",
  },
  {
    id: "b_m3_market",
    branch: "B",
    month: 3,
    title: "Industry hiring slowdown",
    description:
      "The same market downturn hits. In your established role with tenure, you are relatively insulated from cuts.",
    kind: "exogenous",
    is_shared_exogenous: true,
    shared_event_id: SHARED_MARKET,
    involved_personas: ["p_self"],
    evidence:
      "Same macro event modeled in both futures so the comparison isolates the decision, not luck.",
  },
  {
    id: "b_m4_side_project",
    branch: "B",
    month: 4,
    title: "You start a side project",
    description:
      "With free evenings, you channel the restlessness into a side project that partly scratches the growth itch.",
    kind: "perturbation",
    is_shared_exogenous: false,
    shared_event_id: null,
    involved_personas: ["p_self"],
    evidence: null,
  },
  {
    id: "b_m5_plateau",
    branch: "B",
    month: 5,
    title: "Career plateau acknowledged",
    description:
      "A routine review confirms no near-term advancement. Stable and low-stress, but the growth question is now explicit.",
    kind: "skeleton",
    is_shared_exogenous: false,
    shared_event_id: null,
    involved_personas: ["p_self"],
    evidence: null,
  },
];

// Per-month metrics for each branch. `scores` is keyed by dimension id, 0–100.
// `stress_load` is lower_is_better, so higher values in Branch A read as worse.
const metricsA: MetricPoint[] = [
  {
    branch: "A",
    month: 0,
    scores: { economic: 62, career: 58, relationship: 60, mental: 55, stress_load: 45, autonomy: 50 },
    supporting_event_ids: ["a_m0_start"],
  },
  {
    branch: "A",
    month: 1,
    scores: { economic: 70, career: 63, relationship: 52, mental: 46, stress_load: 64, autonomy: 45 },
    supporting_event_ids: ["a_m1_ramp"],
  },
  {
    branch: "A",
    month: 2,
    scores: { economic: 74, career: 72, relationship: 50, mental: 48, stress_load: 66, autonomy: 47 },
    supporting_event_ids: ["a_m2_first_win"],
  },
  {
    branch: "A",
    month: 3,
    scores: { economic: 73, career: 70, relationship: 47, mental: 43, stress_load: 70, autonomy: 44 },
    supporting_event_ids: ["a_m3_market"],
  },
  {
    branch: "A",
    month: 4,
    scores: { economic: 76, career: 74, relationship: 44, mental: 45, stress_load: 68, autonomy: 50 },
    supporting_event_ids: ["a_m4_strain"],
  },
  {
    branch: "A",
    month: 5,
    scores: { economic: 80, career: 82, relationship: 52, mental: 53, stress_load: 58, autonomy: 55 },
    supporting_event_ids: ["a_m5_promotion_track"],
  },
];

const metricsB: MetricPoint[] = [
  {
    branch: "B",
    month: 0,
    scores: { economic: 60, career: 56, relationship: 62, mental: 62, stress_load: 38, autonomy: 58 },
    supporting_event_ids: ["b_m0_stay"],
  },
  {
    branch: "B",
    month: 1,
    scores: { economic: 60, career: 55, relationship: 68, mental: 66, stress_load: 32, autonomy: 60 },
    supporting_event_ids: ["b_m1_steady"],
  },
  {
    branch: "B",
    month: 2,
    scores: { economic: 60, career: 52, relationship: 67, mental: 63, stress_load: 35, autonomy: 60 },
    supporting_event_ids: ["b_m2_restless"],
  },
  {
    branch: "B",
    month: 3,
    scores: { economic: 61, career: 51, relationship: 66, mental: 62, stress_load: 36, autonomy: 61 },
    supporting_event_ids: ["b_m3_market"],
  },
  {
    branch: "B",
    month: 4,
    scores: { economic: 61, career: 56, relationship: 67, mental: 66, stress_load: 33, autonomy: 68 },
    supporting_event_ids: ["b_m4_side_project"],
  },
  {
    branch: "B",
    month: 5,
    scores: { economic: 61, career: 50, relationship: 67, mental: 64, stress_load: 34, autonomy: 66 },
    supporting_event_ids: ["b_m5_plateau"],
  },
];

const branch_points: BranchPoint[] = [
  {
    month: 1,
    dimension: "stress_load",
    magnitude: 32,
    description:
      "Stress load diverges early: the new job's ramp-up likely drives sustained pressure ~32 points higher than the steady status quo.",
    cause_chain:
      "Higher role expectations -> longer hours -> reduced recovery time -> elevated stress load in Branch A.",
  },
  {
    month: 1,
    dimension: "mental",
    magnitude: 20,
    description:
      "Mental wellbeing diverges early: the ramp-up likely costs ~20 points versus staying put.",
    cause_chain:
      "Sustained overwork -> poorer sleep and recovery -> lower mental wellbeing in Branch A.",
  },
  {
    month: 5,
    dimension: "career",
    magnitude: 32,
    description:
      "Career trajectory diverges sharply by month 6: the promotion track in Branch A likely pulls ahead by ~32 points.",
    cause_chain:
      "Visible early win -> leadership trust -> promotion-track placement in Branch A, while Branch B plateaus.",
  },
];

const credibility: CredibilityCard = {
  overall: 0.68,
  data_sufficiency: 0.55,
  causal_confidence: 0.72,
  event_plausibility: 0.78,
  notes: [
    "Compensation figures are anchored in the offer details you provided.",
    "Relationship dynamics are directional — limited information about your partner's preferences.",
    "The market downturn is modeled identically in both futures, so the comparison isolates your decision.",
  ],
  low_confidence_personas: ["p_mother"],
};

const recommendation: Recommendation = {
  text:
    "On balance, taking the new job looks slightly favorable IF you can protect your evenings. It likely trades roughly 4-6 months of lower mental wellbeing and relationship strain for a materially stronger career and economic trajectory (~+30 career points by month 6). Staying is the safer path for wellbeing and your relationship, at the likely cost of a visible plateau. This is a probability, not a prophecy — the single biggest lever you control is setting firm working-hour boundaries early.",
  favored_branch: "A",
};

export const sampleResult: SimResult = {
  sim_id: "demo-0001",
  decision:
    "Should I take the higher-paying but higher-stress job, or stay where I am?",
  options: ["Take the new job", "Stay at my current job"],
  mode: "quick",
  seed: 12345,
  dimensions,
  personas,
  events,
  metrics: [...metricsA, ...metricsB],
  branch_points,
  credibility,
  recommendation,
  created_at: new Date("2026-06-13T12:00:00Z").toISOString(),
};
