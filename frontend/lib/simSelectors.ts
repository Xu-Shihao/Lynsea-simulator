import type {
  Branch,
  Dimension,
  MetricPoint,
  TimelineEvent,
  ValueWeights,
} from "./types";

/** Sorted, de-duplicated list of all months present across both branches. */
export function allMonths(
  events: TimelineEvent[],
  metrics: MetricPoint[],
): number[] {
  const set = new Set<number>();
  for (const e of events) set.add(e.month);
  for (const m of metrics) set.add(m.month);
  return [...set].sort((a, b) => a - b);
}

export function eventsForBranch(
  events: TimelineEvent[],
  branch: Branch,
): TimelineEvent[] {
  return events
    .filter((e) => e.branch === branch)
    .sort((a, b) => a.month - b.month);
}

export function metricsForBranch(
  metrics: MetricPoint[],
  branch: Branch,
): MetricPoint[] {
  return metrics
    .filter((m) => m.branch === branch)
    .sort((a, b) => a.month - b.month);
}

/** Read one dimension's score from a metric point (0 if missing). */
export function scoreOf(point: MetricPoint, dimId: string): number {
  return point.scores?.[dimId] ?? 0;
}

export interface ChartRow {
  month: number;
  A: number | null;
  B: number | null;
}

/** Build Recharts-friendly rows for a single (dynamic) dimension. */
export function chartRows(metrics: MetricPoint[], dimId: string): ChartRow[] {
  const months = [...new Set(metrics.map((m) => m.month))].sort(
    (a, b) => a - b,
  );
  return months.map((month) => {
    const a = metrics.find((m) => m.branch === "A" && m.month === month);
    const b = metrics.find((m) => m.branch === "B" && m.month === month);
    return {
      month,
      A: a ? scoreOf(a, dimId) : null,
      B: b ? scoreOf(b, dimId) : null,
    };
  });
}

/** Final-month A-vs-B delta for each dimension (A minus B). */
export function finalDeltas(
  metrics: MetricPoint[],
  dimensions: Dimension[],
): { dim: Dimension; a: number; b: number; delta: number }[] {
  const months = metrics.map((m) => m.month);
  if (!months.length || !dimensions.length) return [];
  const last = Math.max(...months);
  const a = metrics.find((m) => m.branch === "A" && m.month === last);
  const b = metrics.find((m) => m.branch === "B" && m.month === last);
  return dimensions.map((dim) => {
    const av = a ? scoreOf(a, dim.id) : 0;
    const bv = b ? scoreOf(b, dim.id) : 0;
    return { dim, a: av, b: bv, delta: av - bv };
  });
}

/**
 * Orient a raw 0–100 score so that "higher is always better" for aggregation.
 * For a `lower_is_better` dimension a high raw value is bad, so we invert it.
 */
export function orientedScore(value: number, polarity: Dimension["polarity"]): number {
  return polarity === "lower_is_better" ? 100 - value : value;
}

/**
 * Composite 0–100 score per branch at the final modeled month, value-weighted
 * and polarity-aware. With no weights every dimension is weighted neutrally
 * (equal). `lower_is_better` dimensions are inverted before averaging so the
 * composite always reads "higher is better". `topValue` is the heaviest-
 * weighted dimension (for the sidebar note), null when weights are absent.
 */
export function compositeScores(
  metrics: MetricPoint[],
  dimensions: Dimension[],
  weights?: ValueWeights | null,
): { A: number | null; B: number | null; topValue: Dimension | null } {
  const months = metrics.map((m) => m.month);
  if (!months.length || !dimensions.length)
    return { A: null, B: null, topValue: null };
  const last = Math.max(...months);

  const weightFor = (dimId: string): number => {
    const w = weights?.[dimId];
    return w == null ? 1 : w;
  };
  const total = dimensions.reduce((s, d) => s + weightFor(d.id), 0) || 1;

  const score = (branch: Branch): number | null => {
    const pt = metrics.find((m) => m.branch === branch && m.month === last);
    if (!pt) return null;
    const sum = dimensions.reduce(
      (s, d) =>
        s + orientedScore(scoreOf(pt, d.id), d.polarity) * weightFor(d.id),
      0,
    );
    return Math.round(sum / total);
  };

  let topValue: Dimension | null = null;
  if (weights) {
    let best = -Infinity;
    for (const d of dimensions) {
      const w = weightFor(d.id);
      if (w > best) {
        best = w;
        topValue = d;
      }
    }
  }

  return { A: score("A"), B: score("B"), topValue };
}

/**
 * Recommendation favored branch + magnitude, derived client-side from the
 * value-weighted composite so the results-page sliders can live-recompute it.
 */
export function favoredFromComposite(
  metrics: MetricPoint[],
  dimensions: Dimension[],
  weights?: ValueWeights | null,
): { favored: "A" | "B" | "tie"; a: number | null; b: number | null; gap: number } {
  const { A, B } = compositeScores(metrics, dimensions, weights);
  if (A == null || B == null) return { favored: "tie", a: A, b: B, gap: 0 };
  const gap = A - B;
  const favored = Math.abs(gap) < 2 ? "tie" : gap > 0 ? "A" : "B";
  return { favored, a: A, b: B, gap: Math.abs(Math.round(gap)) };
}

/**
 * Heuristic "high-risk" detection: a `higher_is_better` dimension drops below a
 * floor, or a `lower_is_better` dimension climbs above its ceiling, in either
 * branch. Used to decide whether to show the prominent safety banner.
 */
export function isHighRisk(
  metrics: MetricPoint[],
  dimensions: Dimension[],
): boolean {
  const FLOOR = 40;
  if (!dimensions.length) {
    // Fallback before dimensions arrive: any raw score at/below the floor.
    return metrics.some((m) =>
      Object.values(m.scores ?? {}).some((v) => v <= FLOOR),
    );
  }
  return metrics.some((m) =>
    dimensions.some((d) => orientedScore(scoreOf(m, d.id), d.polarity) <= FLOOR),
  );
}

/** Map shared_event_id -> sequential index for stable shared-event labels. */
export function sharedEventIndex(
  events: TimelineEvent[],
): Record<string, number> {
  const ids = [
    ...new Set(
      events
        .filter((e) => e.is_shared_exogenous && e.shared_event_id)
        .map((e) => e.shared_event_id as string),
    ),
  ];
  const map: Record<string, number> = {};
  ids.forEach((id, i) => {
    map[id] = i + 1;
  });
  return map;
}
