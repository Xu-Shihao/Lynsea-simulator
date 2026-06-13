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
import type { BranchPoint, Dimension, MetricPoint } from "../lib/types";

/**
 * One Recharts 0–100 A-vs-B line chart per generated dimension (not a fixed 5),
 * styled to match the Stitch "Dimensional Trajectories" sidebar slot. Branch
 * points are drawn as magenta reference lines, keyed by `dimension`.
 */
export function MetricCharts({
  metrics,
  dimensions,
  branchPoints,
}: {
  metrics: MetricPoint[];
  dimensions: Dimension[];
  branchPoints: BranchPoint[];
}) {
  if (!metrics.length || !dimensions.length) return null;

  return (
    <div className="flex flex-col gap-md">
      <h4 className="font-label text-on-surface-variant uppercase tracking-wider text-xs">
        Dimensional Trajectories
      </h4>
      {dimensions.map((dim) => (
        <MetricChart
          key={dim.id}
          dim={dim}
          metrics={metrics}
          branchPoints={branchPoints}
        />
      ))}
    </div>
  );
}

function MetricChart({
  dim,
  metrics,
  branchPoints,
}: {
  dim: Dimension;
  metrics: MetricPoint[];
  branchPoints: BranchPoint[];
}) {
  const rows = chartRows(metrics, dim.id);
  const relevantPoints = branchPoints.filter((bp) => bp.dimension === dim.id);
  const lowerIsBetter = dim.polarity === "lower_is_better";

  // Final-month A vs B comparator for the corner indicator. For a
  // lower_is_better dimension the smaller raw value is the better outcome.
  const last = rows.length ? rows[rows.length - 1] : null;
  let lead: "A" | "B" | "tie" | null = null;
  if (last && last.A != null && last.B != null) {
    const a = Math.round(last.A);
    const b = Math.round(last.B);
    if (a === b) lead = "tie";
    else if (lowerIsBetter) lead = a < b ? "A" : "B";
    else lead = a > b ? "A" : "B";
  }

  return (
    <div className="bg-surface-container rounded p-sm border border-outline-variant/30">
      <div className="flex justify-between items-center mb-2 gap-2">
        <span
          className="font-caption text-caption text-on-surface truncate"
          title={dim.description}
        >
          {dim.label}
          {lowerIsBetter && (
            <span className="text-outline ml-1 text-[10px]">(lower is better)</span>
          )}
        </span>
        {lead && lead !== "tie" && (
          <span
            className="text-[10px] font-semibold shrink-0"
            style={{ color: BRANCH_COLORS[lead] }}
          >
            {lead === "A" ? "A ahead" : "B ahead"}
          </span>
        )}
        {lead === "tie" && (
          <span className="text-[10px] text-on-surface-variant shrink-0">
            A ≈ B
          </span>
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
