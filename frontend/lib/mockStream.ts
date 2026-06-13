/**
 * mockStream.ts — Local mock SSE stream
 *
 * Emits the FULL event sequence from docs/api-contract.md so the UI works
 * with ?mock=1 before the backend lands. Faithful mock: all event types,
 * 2 branches A/B, skeleton-then-perturbation events, 5 metric dims,
 * ≥1 fork point, scores (value-weighted), credibility, recommendation.
 *
 * Usage:
 *   const cleanup = createMockStream(req, (eventType, data) => { ... });
 *   // cleanup() stops the stream
 *
 * All natural-language text is PROBABILISTIC (uses "likely", "~60%", never "will/definitely").
 * Branch A is ALWAYS cyan/left (Option A), Branch B ALWAYS amber/right (Option B).
 */

import type {
  BranchScorePayload,
  Branch,
  CredibilityPayload,
  ForkPointPayload,
  MetricDim,
  MetricPayload,
  PersonaInfo,
  RecommendationPayload,
  RunStartedPayload,
  SimulateRequest,
  TimelineEventPayload,
  WorldReadyPayload,
} from './contract';

type EventCallback = (eventType: string, data: unknown) => void;

// ─── Mock data helpers ───────────────────────────────────────────────────────

function uuid(): string {
  return Math.random().toString(36).slice(2, 10) + '-' + Date.now().toString(36);
}

const DIMS: MetricDim[] = ['economic', 'career', 'relationships', 'mental_health', 'autonomy'];

// Seeded pseudo-random for reproducibility in mock
function seededRng(seed: number) {
  let s = seed;
  return () => {
    s = (s * 1664525 + 1013904223) & 0xffffffff;
    return (s >>> 0) / 4294967296;
  };
}

// ─── Main factory ────────────────────────────────────────────────────────────

/**
 * @param req     The SimulateRequest that triggered the simulation
 * @param onEvent Callback invoked for every SSE event
 * @returns cleanup function that stops all pending timers
 */
export function createMockStream(req: SimulateRequest, onEvent: EventCallback): () => void {
  const timers: ReturnType<typeof setTimeout>[] = [];
  const runId = uuid();
  const rng = seededRng(req.seed ?? 42);
  let cancelled = false;

  function after(ms: number, fn: () => void) {
    if (cancelled) return;
    timers.push(setTimeout(() => { if (!cancelled) fn(); }, ms));
  }

  function emit(eventType: string, data: unknown, atMs: number) {
    after(atMs, () => onEvent(eventType, data));
  }

  // ── Derive option labels from request ────────────────────────────────────
  const optionA = req.options?.[0] ?? 'Stay with current path';
  const optionB = req.options?.[1] ?? 'Take the new direction';

  // ── run_started (t=0) ────────────────────────────────────────────────────
  const runStarted: RunStartedPayload = {
    run_id: runId,
    mode: req.mode,
    branches: ['A', 'B'],
  };
  emit('run_started', runStarted, 0);

  // ── world_ready (t=400) ─────────────────────────────────────────────────
  const personas: PersonaInfo[] = [
    { id: 'self', role: 'self', influence_weight: 10, confidence: 'high' },
    ...(req.social_circle?.slice(0, 4).map((m, i) => ({
      id: `social-${i}`,
      role: m.role,
      influence_weight: m.influence_weight,
      confidence: m.influence_weight >= 7 ? ('high' as const) : ('low' as const),
    })) ?? [
      { id: 'partner-1', role: 'partner', influence_weight: 8, confidence: 'high' as const },
      { id: 'mentor-1', role: 'mentor', influence_weight: 6, confidence: 'low' as const },
    ]),
  ];

  const world: WorldReadyPayload = {
    personas,
    options: { A: optionA, B: optionB },
  };
  emit('world_ready', world, 400);

  // ── Timeline events — skeleton wave (branches A and B, months 1–6) ───────
  const MONTHS = [1, 2, 3, 4, 5, 6];

  // Branch A skeleton events
  const skeletonA: { month: number; title: string; detail: string; personas: string[] }[] = [
    { month: 1, title: 'Steady state continues', detail: 'Day-to-day routine holds. Predictable schedule, familiar challenges.', personas: ['self'] },
    { month: 2, title: 'Performance review cycle', detail: 'Likely positive feedback; around a 65% chance of a modest raise.', personas: ['self', 'mentor'] },
    { month: 3, title: 'Team restructure rumour', detail: 'Org change signals possible role shift — likely minor, but uncertainty exists.', personas: ['self'] },
    { month: 4, title: 'Side project gains traction', detail: 'Personal initiative draws informal recognition; roughly a 40% chance it opens new doors.', personas: ['self', 'mentor'] },
    { month: 5, title: 'Network deepens', detail: 'Consistent presence builds trust with key colleagues.', personas: ['self'] },
    { month: 6, title: 'Six-month checkpoint', detail: 'Position is stable. Trajectory is likely upward, though pace may feel slow.', personas: ['self', 'partner'] },
  ];

  // Branch B skeleton events
  const skeletonB: { month: number; title: string; detail: string; personas: string[] }[] = [
    { month: 1, title: 'Onboarding begins', detail: 'New environment, new team. Steep learning curve — around a 70% chance of initial stress spike.', personas: ['self'] },
    { month: 2, title: 'First real responsibility', detail: 'Assigned ownership of a core module. High-visibility, high-pressure — likely a defining early moment.', personas: ['self'] },
    { month: 3, title: 'Equity grant confirmed', detail: 'Vesting schedule formalised. Long-term upside roughly 3–5× base if startup reaches Series B.', personas: ['self'] },
    { month: 4, title: 'Runway milestone cleared', detail: 'Company hits a funding target; leadership signals next 12 months are funded.', personas: ['self', 'mentor'] },
    { month: 5, title: 'Work–life tension rises', detail: 'Partner expresses concern; around a 50% chance this triggers a meaningful conversation about priorities.', personas: ['self', 'partner'] },
    { month: 6, title: 'Six-month checkpoint', detail: 'Growth trajectory looks steep. Likely more career capital gained, but at a personal cost that is still tallying.', personas: ['self', 'partner'] },
  ];

  let t = 600;
  MONTHS.forEach(month => {
    const evA = skeletonA[month - 1];
    const evB = skeletonB[month - 1];

    const tlA: TimelineEventPayload = {
      branch: 'A',
      event_id: `A-m${month}-1`,
      month,
      kind: 'skeleton',
      title: evA.title,
      detail: evA.detail,
      personas: evA.personas,
    };
    emit('timeline_event', tlA, t);

    const tlB: TimelineEventPayload = {
      branch: 'B',
      event_id: `B-m${month}-1`,
      month,
      kind: 'skeleton',
      title: evB.title,
      detail: evB.detail,
      personas: evB.personas,
    };
    emit('timeline_event', tlB, t + 80);

    t += 350;
  });

  // ── Shared perturbation event at month 3 ────────────────────────────────
  const perturbAt = t;
  const perturbA: TimelineEventPayload = {
    branch: 'A',
    event_id: 'A-m3-2',
    month: 3,
    kind: 'perturbation',
    title: 'Partner receives job offer (shared)',
    detail: 'External opportunity for partner requires relocation discussion regardless of your path — a shared life event across both branches.',
    personas: ['self', 'partner'],
  };
  const perturbB: TimelineEventPayload = {
    branch: 'B',
    event_id: 'B-m3-2',
    month: 3,
    kind: 'perturbation',
    title: 'Partner receives job offer (shared)',
    detail: 'External opportunity for partner requires relocation discussion regardless of your path — a shared life event across both branches.',
    personas: ['self', 'partner'],
  };
  emit('timeline_event', perturbA, perturbAt);
  emit('timeline_event', perturbB, perturbAt + 60);
  t = perturbAt + 400;

  // ── Metric events (all 5 dims × 6 months × 2 branches) ──────────────────
  // Base score profiles — A is more stable, B has higher variance
  const baseA: Record<MetricDim, number> = {
    economic: 62, career: 52, relationships: 68, mental_health: 65, autonomy: 48,
  };
  const baseB: Record<MetricDim, number> = {
    economic: 45, career: 72, relationships: 52, mental_health: 42, autonomy: 78,
  };
  const trendA: Record<MetricDim, number> = {
    economic: 2, career: 1.5, relationships: -0.5, mental_health: 0.5, autonomy: 1,
  };
  const trendB: Record<MetricDim, number> = {
    economic: -1, career: 4, relationships: -2.5, mental_health: -3, autonomy: 3,
  };

  DIMS.forEach(dim => {
    MONTHS.forEach(month => {
      const noise = (rng() - 0.5) * 6;
      const scoreA = Math.min(100, Math.max(0, Math.round(baseA[dim] + trendA[dim] * month + noise)));
      const scoreB = Math.min(100, Math.max(0, Math.round(baseB[dim] + trendB[dim] * month + noise * 1.5)));

      const metricA: MetricPayload = {
        branch: 'A',
        month,
        dim,
        score: scoreA,
        evidence_event_ids: [`A-m${month}-1`],
      };
      const metricB: MetricPayload = {
        branch: 'B',
        month,
        dim,
        score: scoreB,
        evidence_event_ids: [`B-m${month}-1`],
      };

      emit('metric', metricA, t);
      emit('metric', metricB, t + 50);
      t += 120;
    });
  });

  // ── Fork point at month 3 (largest divergence) ───────────────────────────
  const fork: ForkPointPayload = {
    month: 3,
    magnitude: 72,
    title: 'Income stability vs. career growth',
    explanation: 'Branch A maintains predictable income with modest career progression. Branch B likely accelerates career capital but with a roughly 60% chance of income instability in months 3–5.',
    dims: ['economic', 'career', 'mental_health'],
  };
  emit('fork_point', fork, t);
  t += 300;

  // ── Branch scores ────────────────────────────────────────────────────────
  const scoreA: BranchScorePayload = {
    branch: 'A',
    total: 61,
    breakdown: { economic: 72, career: 56, relationships: 65, mental_health: 68, autonomy: 52 },
    weighted: true,
  };
  const scoreB: BranchScorePayload = {
    branch: 'B',
    total: 67,
    breakdown: { economic: 44, career: 84, relationships: 48, mental_health: 38, autonomy: 88 },
    weighted: true,
  };
  emit('branch_score', scoreA, t);
  emit('branch_score', scoreB, t + 100);
  t += 400;

  // ── Credibility card ────────────────────────────────────────────────────
  const credibility: CredibilityPayload = {
    overall: 62,
    breakdown: {
      data_sufficiency: 55,
      causal_confidence: 64,
      event_plausibility: 68,
    },
    notes: 'Directional estimate only. Personas built from limited profile input; providing more context likely improves accuracy by around 20–30%.',
  };
  emit('credibility', credibility, t);
  t += 300;

  // ── Recommendation ───────────────────────────────────────────────────────
  const rec: RecommendationPayload = {
    leaning: 'B',
    rationale: 'Given the stated core values of growth and autonomy, Branch B (joining the new path) is likely to score higher for you — around a 60% probability of greater long-term satisfaction. Short-term economic and relationship stress is probable in months 1–4.',
    guardrail: 'High uncertainty: the simulation has limited relationship and financial data. Re-run with fuller profile details before treating this as a strong signal.',
  };
  emit('recommendation', rec, t);
  t += 300;

  // ── Done ────────────────────────────────────────────────────────────────
  emit('done', { run_id: runId }, t);

  // Return cleanup function
  return () => {
    cancelled = true;
    timers.forEach(clearTimeout);
  };
}
