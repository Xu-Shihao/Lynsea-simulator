import {
  METRIC_KEYS,
  type Branch,
  type MetricKey,
  type MetricPoint,
  type TimelineEvent,
  type ValueWeights,
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

export interface ChartRow {
  month: number;
  A: number | null;
  B: number | null;
}

/** Build Recharts-friendly rows for a single metric dimension. */
export function chartRows(
  metrics: MetricPoint[],
  key: MetricKey,
): ChartRow[] {
  const months = [...new Set(metrics.map((m) => m.month))].sort(
    (a, b) => a - b,
  );
  return months.map((month) => {
    const a = metrics.find((m) => m.branch === "A" && m.month === month);
    const b = metrics.find((m) => m.branch === "B" && m.month === month);
    return {
      month,
      A: a ? a[key] : null,
      B: b ? b[key] : null,
    };
  });
}

/** Final-month A-vs-B delta for each metric (A minus B). */
export function finalDeltas(
  metrics: MetricPoint[],
): { key: MetricKey; a: number; b: number; delta: number }[] {
  const months = metrics.map((m) => m.month);
  if (!months.length) return [];
  const last = Math.max(...months);
  return METRIC_KEYS.map((key) => {
    const a = metrics.find((m) => m.branch === "A" && m.month === last);
    const b = metrics.find((m) => m.branch === "B" && m.month === last);
    const av = a ? a[key] : 0;
    const bv = b ? b[key] : 0;
    return { key, a: av, b: bv, delta: av - bv };
  });
}

/**
 * Composite 0–100 score per branch at the final modeled month, optionally
 * value-weighted. With no weights, the five dimensions are averaged equally.
 * The dominant (heaviest-weighted) dimension label is returned for the
 * "value-weighted based on X" note in the dashboard.
 */
export function compositeScores(
  metrics: MetricPoint[],
  weights?: ValueWeights | null,
): { A: number | null; B: number | null; topValue: MetricKey | null } {
  const months = metrics.map((m) => m.month);
  if (!months.length) return { A: null, B: null, topValue: null };
  const last = Math.max(...months);

  const w: Record<MetricKey, number> = {
    economic: weights?.economic ?? 1,
    career: weights?.career ?? 1,
    relationship: weights?.relationship ?? 1,
    mental: weights?.mental ?? 1,
    autonomy: weights?.autonomy ?? 1,
  };
  const total = METRIC_KEYS.reduce((s, k) => s + (w[k] || 0), 0) || 1;

  const score = (branch: Branch): number | null => {
    const pt = metrics.find((m) => m.branch === branch && m.month === last);
    if (!pt) return null;
    const sum = METRIC_KEYS.reduce((s, k) => s + pt[k] * (w[k] || 0), 0);
    return Math.round(sum / total);
  };

  let topValue: MetricKey | null = null;
  if (weights) {
    let best = -Infinity;
    for (const k of METRIC_KEYS) {
      if ((w[k] || 0) > best) {
        best = w[k] || 0;
        topValue = k;
      }
    }
  }

  return { A: score("A"), B: score("B"), topValue };
}

/**
 * Heuristic "high-risk" detection: any metric drops materially below a floor
 * in either branch, used to decide whether to show the prominent safety banner.
 */
export function isHighRisk(metrics: MetricPoint[]): boolean {
  const FLOOR = 40;
  return metrics.some((m) =>
    METRIC_KEYS.some((k) => m[k] <= FLOOR),
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
