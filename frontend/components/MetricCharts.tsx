"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { chartRows } from "../lib/simSelectors";
import { BRANCH_COLORS } from "../lib/theme";
import {
  METRIC_KEYS,
  METRIC_LABELS,
  type BranchPoint,
  type MetricKey,
  type MetricPoint,
} from "../lib/types";

/**
 * The five REAL metric charts (0–100 A-vs-B line charts), styled to match the
 * Stitch "Dimensional Trajectories" sidebar slot. Uses Recharts (not the static
 * SVG placeholders from the Stitch HTML). Wires ALL five dimensions.
 */
export function MetricCharts({
  metrics,
  branchPoints,
}: {
  metrics: MetricPoint[];
  branchPoints: BranchPoint[];
}) {
  if (!metrics.length) return null;

  return (
    <div className="flex flex-col gap-md">
      <h4 className="font-label text-on-surface-variant uppercase tracking-wider text-xs">
        Dimensional Trajectories
      </h4>
      {METRIC_KEYS.map((key) => (
        <MetricChart
          key={key}
          metricKey={key}
          metrics={metrics}
          branchPoints={branchPoints}
        />
      ))}
    </div>
  );
}

function MetricChart({
  metricKey,
  metrics,
  branchPoints,
}: {
  metricKey: MetricKey;
  metrics: MetricPoint[];
  branchPoints: BranchPoint[];
}) {
  const rows = chartRows(metrics, metricKey);
  const relevantPoints = branchPoints.filter((bp) => bp.metric === metricKey);

  // Final-month A vs B comparator for the corner indicator.
  const last = rows.length ? rows[rows.length - 1] : null;
  let lead: "A" | "B" | "tie" | null = null;
  if (last && last.A != null && last.B != null) {
    if (Math.round(last.A) > Math.round(last.B)) lead = "A";
    else if (Math.round(last.B) > Math.round(last.A)) lead = "B";
    else lead = "tie";
  }

  return (
    <div className="bg-surface-container rounded p-sm border border-outline-variant/30">
      <div className="flex justify-between items-center mb-2">
        <span className="font-caption text-caption text-on-surface">
          {METRIC_LABELS[metricKey]}
        </span>
        {lead && lead !== "tie" && (
          <span
            className="text-[10px] font-semibold"
            style={{ color: BRANCH_COLORS[lead] }}
          >
            {lead === "A" ? "A > B" : "B > A"}
          </span>
        )}
        {lead === "tie" && (
          <span className="text-[10px] text-on-surface-variant">A ≈ B</span>
        )}
      </div>
      <div className="h-20 bg-surface-variant/20 rounded border border-surface-variant overflow-hidden">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={rows}
            margin={{ top: 6, right: 6, bottom: 0, left: -28 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#1d253a" />
            <XAxis
              dataKey="month"
              tickFormatter={(m) => `M${m}`}
              tick={{ fontSize: 9, fill: "#6d758e" }}
              stroke="#1d253a"
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 9, fill: "#6d758e" }}
              stroke="#1d253a"
              width={30}
            />
            <Tooltip content={<MetricTooltip />} />
            {relevantPoints.map((bp, i) => (
              <ReferenceLine
                key={i}
                x={bp.month}
                stroke="#F472B6"
                strokeDasharray="4 3"
                strokeOpacity={0.7}
              />
            ))}
            <Line
              type="monotone"
              dataKey="A"
              stroke={BRANCH_COLORS.A}
              strokeWidth={2}
              dot={{ r: 2 }}
              connectNulls
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="B"
              stroke={BRANCH_COLORS.B}
              strokeWidth={2}
              dot={{ r: 2 }}
              connectNulls
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

interface TooltipPayloadItem {
  dataKey?: string | number;
  value?: number | string;
}

function MetricTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: number | string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-surface-variant bg-surface-container-high px-2.5 py-1.5 text-xs shadow-md">
      <div className="font-medium text-on-surface mb-0.5">Month {label}</div>
      {payload.map((p) => (
        <div
          key={String(p.dataKey)}
          className="flex items-center gap-1.5"
          style={{ color: BRANCH_COLORS[p.dataKey as "A" | "B"] }}
        >
          <span className="font-semibold">{String(p.dataKey)}</span>
          <span className="tabular-nums">
            ~{typeof p.value === "number" ? Math.round(p.value) : p.value}
          </span>
        </div>
      ))}
    </div>
  );
}
