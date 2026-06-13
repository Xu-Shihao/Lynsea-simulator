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

export function MetricCharts({
  metrics,
  options,
  branchPoints,
}: {
  metrics: MetricPoint[];
  options: [string, string];
  branchPoints: BranchPoint[];
}) {
  if (!metrics.length) return null;

  return (
    <section className="card p-5">
      <div className="flex items-baseline justify-between mb-4 flex-wrap gap-2">
        <h2 className="text-lg font-semibold text-[var(--ink)]">
          Five life dimensions, over time
        </h2>
        <Legend options={options} />
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {METRIC_KEYS.map((key) => (
          <MetricChart
            key={key}
            metricKey={key}
            metrics={metrics}
            branchPoints={branchPoints}
          />
        ))}
      </div>
      <p className="mt-3 text-xs text-[var(--muted)]">
        Each line is a likely trajectory (0–100), not a guarantee. Vertical
        markers flag months where the two futures diverge most.
      </p>
    </section>
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

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3">
      <div className="text-sm font-medium text-[var(--ink)] mb-2">
        {METRIC_LABELS[metricKey]}
      </div>
      <ResponsiveContainer width="100%" height={150}>
        <LineChart
          data={rows}
          margin={{ top: 4, right: 8, bottom: 0, left: -22 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis
            dataKey="month"
            tickFormatter={(m) => `M${m}`}
            tick={{ fontSize: 10, fill: "var(--muted)" }}
            stroke="var(--border)"
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 10, fill: "var(--muted)" }}
            stroke="var(--border)"
            width={32}
          />
          <Tooltip content={<MetricTooltip />} />
          {relevantPoints.map((bp, i) => (
            <ReferenceLine
              key={i}
              x={bp.month}
              stroke="var(--accent)"
              strokeDasharray="4 3"
              strokeOpacity={0.6}
            />
          ))}
          <Line
            type="monotone"
            dataKey="A"
            stroke={BRANCH_COLORS.A}
            strokeWidth={2.4}
            dot={{ r: 2.5 }}
            connectNulls
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="B"
            stroke={BRANCH_COLORS.B}
            strokeWidth={2.4}
            dot={{ r: 2.5 }}
            connectNulls
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
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
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5 text-xs shadow-md">
      <div className="font-medium text-[var(--ink)] mb-0.5">Month {label}</div>
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

function Legend({ options }: { options: [string, string] }) {
  return (
    <div className="flex items-center gap-4 text-xs">
      <span className="flex items-center gap-1.5">
        <span
          className="inline-block h-2.5 w-5 rounded-full"
          style={{ background: BRANCH_COLORS.A }}
        />
        <span className="branch-a-text font-medium">A</span>
        <span className="text-[var(--muted)] max-w-[140px] truncate">
          {options[0]}
        </span>
      </span>
      <span className="flex items-center gap-1.5">
        <span
          className="inline-block h-2.5 w-5 rounded-full"
          style={{ background: BRANCH_COLORS.B }}
        />
        <span className="branch-b-text font-medium">B</span>
        <span className="text-[var(--muted)] max-w-[140px] truncate">
          {options[1]}
        </span>
      </span>
    </div>
  );
}
