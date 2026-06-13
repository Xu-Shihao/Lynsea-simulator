"use client";

import { finalDeltas } from "../lib/simSelectors";
import { BRANCH_COLORS } from "../lib/theme";
import {
  METRIC_LABELS,
  type BranchPoint,
  type MetricKey,
  type MetricPoint,
} from "../lib/types";

export function BranchPoints({
  branchPoints,
  metrics,
  options,
}: {
  branchPoints: BranchPoint[];
  metrics: MetricPoint[];
  options: [string, string];
}) {
  const deltas = finalDeltas(metrics);

  if (!branchPoints.length && !deltas.length) return null;

  return (
    <section className="card p-5">
      <h2 className="text-lg font-semibold text-[var(--ink)] mb-1">
        Where the futures diverge
      </h2>
      <p className="text-xs text-[var(--muted)] mb-4">
        The moments and dimensions that drive the gap between the two paths.
      </p>

      {/* Final-month gap summary */}
      {deltas.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-5">
          {deltas.map((d) => (
            <GapTile key={d.key} metricKey={d.key} delta={d.delta} />
          ))}
        </div>
      )}

      {/* Branch point narratives */}
      <div className="space-y-3">
        {branchPoints
          .slice()
          .sort((a, b) => a.month - b.month)
          .map((bp, i) => (
            <div
              key={i}
              className="rounded-xl border border-[var(--border)] p-3.5"
            >
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <span className="inline-flex items-center gap-1 rounded-md bg-[var(--accent)]/10 px-2 py-0.5 text-[11px] font-medium text-[var(--accent)]">
                  Month {bp.month}
                </span>
                <span className="text-[11px] rounded-md bg-[var(--surface-2)] px-2 py-0.5 text-[var(--muted)]">
                  {METRIC_LABELS[bp.metric as MetricKey] ?? bp.metric}
                </span>
                <span className="text-[11px] text-[var(--muted)]">
                  ~{Math.round(bp.magnitude)}-point gap
                </span>
              </div>
              <p className="text-sm text-[var(--foreground)] leading-relaxed">
                {bp.description}
              </p>
              <div className="mt-2 flex items-start gap-1.5 text-xs text-[var(--muted)]">
                <span className="font-medium text-[var(--ink)]">
                  Cause chain:
                </span>
                <span>{bp.cause_chain}</span>
              </div>
            </div>
          ))}
      </div>

      <p className="mt-3 text-[11px] text-[var(--muted)]">
        A = {options[0]} · B = {options[1]}. Gaps show A minus B at the final
        modeled month.
      </p>
    </section>
  );
}

function GapTile({
  metricKey,
  delta,
}: {
  metricKey: MetricKey;
  delta: number;
}) {
  const rounded = Math.round(delta);
  const favorsA = rounded > 0;
  const neutral = rounded === 0;
  const color = neutral
    ? "var(--muted)"
    : favorsA
      ? BRANCH_COLORS.A
      : BRANCH_COLORS.B;
  return (
    <div className="rounded-lg border border-[var(--border)] p-2.5 text-center">
      <div className="text-[11px] text-[var(--muted)] mb-0.5">
        {METRIC_LABELS[metricKey]}
      </div>
      <div className="text-lg font-semibold tabular-nums" style={{ color }}>
        {rounded > 0 ? "+" : ""}
        {rounded}
      </div>
      <div className="text-[10px] font-medium" style={{ color }}>
        {neutral ? "even" : favorsA ? "favors A" : "favors B"}
      </div>
    </div>
  );
}
