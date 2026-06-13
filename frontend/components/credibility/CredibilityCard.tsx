'use client';

import type { CredibilityPayload } from '@/lib/contract';

// SVG circular gauge — pure math, no deps
function CircularGauge({ value, size = 96 }: { value: number; size?: number }) {
  const radius = (size - 12) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const circumference = 2 * Math.PI * radius;
  const filled = (value / 100) * circumference;
  const gap = circumference - filled;

  // Color interpolation: low (#FB7185) → mid (#FBBF24) → high (#34D399)
  const hue = value < 50
    ? `hsl(${Math.round(351 + (value / 50) * (45 - 351 + 360))} 95% 65%)`
    : `hsl(${Math.round(45 + ((value - 50) / 50) * (152 - 45))} 80% 58%)`;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {/* Track */}
      <circle
        cx={cx}
        cy={cy}
        r={radius}
        fill="none"
        stroke="#1F2738"
        strokeWidth={8}
      />
      {/* Arc */}
      <circle
        cx={cx}
        cy={cy}
        r={radius}
        fill="none"
        stroke={hue}
        strokeWidth={8}
        strokeLinecap="round"
        strokeDasharray={`${filled} ${gap}`}
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{ filter: `drop-shadow(0 0 6px ${hue}66)` }}
      />
      {/* Center text */}
      <text
        x={cx}
        y={cy + 1}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="#E6EAF2"
        fontSize={size * 0.2}
        fontFamily="Inter, sans-serif"
        fontWeight="600"
      >
        {value}
      </text>
      <text
        x={cx}
        y={cy + size * 0.18}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="#5F6B82"
        fontSize={size * 0.11}
        fontFamily="Inter, sans-serif"
      >
        / 100
      </text>
    </svg>
  );
}

const SUB_BAR_LABELS: Record<string, string> = {
  data_sufficiency: 'Data Sufficiency',
  causal_confidence: 'Causal Confidence',
  event_plausibility: 'Event Plausibility',
};

const SUB_BAR_ORDER = ['data_sufficiency', 'causal_confidence', 'event_plausibility'] as const;

function SubBar({ label, value }: { label: string; value: number }) {
  const pct = Math.min(100, Math.max(0, value));
  const color = pct >= 70 ? '#34D399' : pct >= 40 ? '#FBBF24' : '#FB7185';

  return (
    <div className="mb-3 last:mb-0">
      <div className="flex justify-between mb-1">
        <span className="text-[11px] text-[#98A2B8]">{label}</span>
        <span className="text-[11px] font-mono text-[#E6EAF2]">{pct}</span>
      </div>
      <div className="h-1.5 bg-[#1F2738] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, backgroundColor: color, boxShadow: `0 0 6px ${color}66` }}
        />
      </div>
    </div>
  );
}

export interface CredibilityCardProps {
  credibility: CredibilityPayload;
}

export default function CredibilityCard({ credibility }: CredibilityCardProps) {
  return (
    <div className="mt-6 bg-[#141A29] border border-[#2A3346] rounded-xl p-5">
      <p className="text-[11px] font-semibold uppercase tracking-widest text-[#98A2B8] mb-4">
        Simulation Credibility
      </p>

      <div className="flex gap-5 items-center">
        {/* Circular gauge */}
        <div className="flex-shrink-0 flex flex-col items-center gap-1">
          <CircularGauge value={credibility.overall} size={88} />
          <span className="text-[10px] text-[#5F6B82]">Overall</span>
        </div>

        {/* Sub-bars */}
        <div className="flex-1 min-w-0">
          {SUB_BAR_ORDER.map((key) => (
            <SubBar
              key={key}
              label={SUB_BAR_LABELS[key] ?? key}
              value={credibility.breakdown[key] ?? 0}
            />
          ))}
        </div>
      </div>

      {/* Notes */}
      {credibility.notes && (
        <p className="mt-4 text-[10px] text-[#5F6B82] italic border-t border-[#1F2738] pt-3 leading-relaxed">
          {credibility.notes}
        </p>
      )}
    </div>
  );
}
