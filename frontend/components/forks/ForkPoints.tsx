'use client';

import type { ForkPointPayload, MetricDim } from '@/lib/contract';

const DIM_LABELS: Record<MetricDim, string> = {
  economic: 'Economic',
  career: 'Career',
  relationships: 'Relationships',
  mental_health: 'Mental Health',
  autonomy: 'Autonomy',
};

// Color band between A (cyan) and B (amber) at the divergence point
function DivergenceBand({ magnitude }: { magnitude: number }) {
  const height = Math.max(4, Math.round(magnitude * 0.6));
  return (
    <div
      className="rounded-full w-full"
      style={{
        height: `${height}px`,
        background: 'linear-gradient(90deg, rgba(34,211,238,0.35) 0%, rgba(244,114,182,0.55) 50%, rgba(251,191,36,0.35) 100%)',
        boxShadow: '0 0 12px rgba(244,114,182,0.25)',
      }}
    />
  );
}

interface ForkPointCardProps {
  fork: ForkPointPayload;
  index: number;
}

function ForkPointCard({ fork, index }: ForkPointCardProps) {
  return (
    <div
      className="relative bg-[#141A29] border border-[#F472B6]/30 rounded-xl p-5 mb-4"
      style={{ boxShadow: '0 0 16px rgba(244,114,182,0.12)' }}
    >
      {/* Pulsing node + header */}
      <div className="flex items-start gap-3 mb-3">
        <div className="flex-shrink-0 mt-0.5">
          <span
            className="flex w-4 h-4 rounded-full animate-pulse"
            style={{ backgroundColor: '#F472B6', boxShadow: '0 0 8px rgba(244,114,182,0.6)' }}
          />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-[11px] text-[#F472B6] bg-[#F472B6]/10 px-2 py-0.5 rounded-full border border-[#F472B6]/20">
              Month {fork.month}
            </span>
            <span className="font-semibold text-sm text-[#E6EAF2]">{fork.title}</span>
            <span className="ml-auto font-mono text-xs text-[#5F6B82]">
              divergence {fork.magnitude}/100
            </span>
          </div>
        </div>
      </div>

      {/* Diff color band */}
      <div className="mb-3 px-7">
        <DivergenceBand magnitude={fork.magnitude} />
        <div className="flex justify-between mt-1">
          <span className="text-[10px] text-[#22D3EE] font-mono">A</span>
          <span className="text-[10px] text-[#F472B6] font-mono">fork</span>
          <span className="text-[10px] text-[#FBBF24] font-mono">B</span>
        </div>
      </div>

      {/* Explanation */}
      <p className="text-[12px] text-[#98A2B8] leading-relaxed pl-7">{fork.explanation}</p>

      {/* Affected dimensions */}
      {fork.dims.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3 pl-7">
          {fork.dims.map((dim) => (
            <span
              key={dim}
              className="text-[10px] text-[#8B7CF6] bg-[#8B7CF6]/10 px-2 py-0.5 rounded-full border border-[#8B7CF6]/20"
            >
              {DIM_LABELS[dim] ?? dim}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export interface ForkPointsProps {
  forks: ForkPointPayload[];
}

export default function ForkPoints({ forks }: ForkPointsProps) {
  if (!forks || forks.length === 0) return null;

  return (
    <section className="mt-8">
      <div className="flex items-center gap-2 mb-4">
        <span
          className="w-2 h-2 rounded-full animate-pulse"
          style={{ backgroundColor: '#F472B6' }}
        />
        <h2 className="text-[11px] font-semibold uppercase tracking-widest text-[#F472B6]">
          Fork Points
        </h2>
        <span className="text-[10px] text-[#5F6B82]">
          — where paths diverge
        </span>
      </div>
      {forks.map((fork, i) => (
        <ForkPointCard key={`${fork.month}-${i}`} fork={fork} index={i} />
      ))}
    </section>
  );
}
