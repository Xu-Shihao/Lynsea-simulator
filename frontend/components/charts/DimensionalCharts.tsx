'use client';

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { Branch, MetricDim, MetricPayload } from '@/lib/contract';

const BRANCH_A_COLOR = '#22D3EE';
const BRANCH_B_COLOR = '#FBBF24';

const DIMS: { key: MetricDim; label: string }[] = [
  { key: 'economic',      label: 'Economic' },
  { key: 'career',        label: 'Career' },
  { key: 'relationships', label: 'Relationships' },
  { key: 'mental_health', label: 'Mental Health' },
  { key: 'autonomy',      label: 'Autonomy' },
];

interface ChartDataPoint {
  month: number;
  A?: number;
  B?: number;
}

function buildChartData(
  metricsA: MetricPayload[],
  metricsB: MetricPayload[],
  dim: MetricDim
): ChartDataPoint[] {
  const dimA = metricsA.filter(m => m.dim === dim);
  const dimB = metricsB.filter(m => m.dim === dim);
  const allMonths = new Set([...dimA.map(m => m.month), ...dimB.map(m => m.month)]);
  return Array.from(allMonths).sort((a, b) => a - b).map(month => ({
    month,
    A: dimA.find(m => m.month === month)?.score,
    B: dimB.find(m => m.month === month)?.score,
  }));
}

function DimChart({ label, data }: { label: string; data: ChartDataPoint[] }) {
  if (data.length === 0) {
    return (
      <div className="bg-[#131929] border border-[#2A3346] rounded-lg p-3 h-[148px] flex flex-col justify-between animate-pulse">
        <p className="font-caption text-[11px] text-[#5F6B82] uppercase tracking-wider">{label}</p>
        <div className="flex-1 flex items-center justify-center">
          <div className="h-1 bg-[#1d253a] rounded w-3/4" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#131929] border border-[#2A3346] rounded-lg p-3">
      <p className="font-caption text-[11px] text-[#98A2B8] uppercase tracking-wider mb-2">{label}</p>
      <ResponsiveContainer width="100%" height={108}>
        <LineChart data={data} margin={{ top: 2, right: 4, left: -28, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1F2738" />
          <XAxis
            dataKey="month"
            tick={{ fontSize: 9, fill: '#5F6B82' }}
            tickFormatter={v => `M${v}`}
            axisLine={{ stroke: '#2A3346' }}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 9, fill: '#5F6B82' }}
            axisLine={{ stroke: '#2A3346' }}
            tickLine={false}
            tickCount={3}
          />
          <Tooltip
            contentStyle={{
              background: '#141A29',
              border: '1px solid #2A3346',
              borderRadius: 6,
              fontSize: 11,
              color: '#E6EAF2',
              padding: '4px 8px',
            }}
            formatter={(value: number, name: string) => [value, `Branch ${name}`]}
            labelFormatter={v => `Month ${v}`}
          />
          <Line
            type="monotone"
            dataKey="A"
            stroke={BRANCH_A_COLOR}
            strokeWidth={2}
            dot={false}
            connectNulls
            activeDot={{ r: 3, fill: BRANCH_A_COLOR }}
          />
          <Line
            type="monotone"
            dataKey="B"
            stroke={BRANCH_B_COLOR}
            strokeWidth={2}
            dot={false}
            connectNulls
            activeDot={{ r: 3, fill: BRANCH_B_COLOR }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

interface DimensionalChartsProps {
  metricsByBranch: Record<Branch, MetricPayload[]>;
}

export function DimensionalCharts({ metricsByBranch }: DimensionalChartsProps) {
  return (
    <div className="mt-8">
      <div className="flex items-center justify-between mb-3">
        <p className="font-caption text-[11px] text-[#98A2B8] uppercase tracking-wider">
          Dimensional Trajectories
        </p>
        <div className="flex gap-4">
          <span className="flex items-center gap-1.5 font-caption text-[10px] text-[#98A2B8]">
            <span className="inline-block w-5 h-0.5 rounded" style={{ backgroundColor: BRANCH_A_COLOR }} />
            Branch A
          </span>
          <span className="flex items-center gap-1.5 font-caption text-[10px] text-[#98A2B8]">
            <span className="inline-block w-5 h-0.5 rounded" style={{ backgroundColor: BRANCH_B_COLOR }} />
            Branch B
          </span>
        </div>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {DIMS.map(({ key, label }) => (
          <DimChart
            key={key}
            label={label}
            data={buildChartData(metricsByBranch.A, metricsByBranch.B, key)}
          />
        ))}
      </div>
    </div>
  );
}
