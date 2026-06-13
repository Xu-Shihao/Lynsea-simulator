'use client';

import { useState } from 'react';
import type { RecommendationPayload, Branch } from '@/lib/contract';

const BRANCH_A_COLOR = '#22D3EE';
const BRANCH_B_COLOR = '#FBBF24';
const NEITHER_COLOR = '#8B7CF6';

function leaningColor(leaning: Branch | 'neither'): string {
  if (leaning === 'A') return BRANCH_A_COLOR;
  if (leaning === 'B') return BRANCH_B_COLOR;
  return NEITHER_COLOR;
}

function leaningLabel(leaning: Branch | 'neither'): string {
  if (leaning === 'A') return 'Leans Branch A';
  if (leaning === 'B') return 'Leans Branch B';
  return 'No strong leaning';
}

// High-risk guardrail: shown prominently for non-trivial guardrail messages
function GuardrailAlert({ text }: { text: string }) {
  return (
    <div className="mt-3 bg-[#FB7185]/10 border border-[#FB7185]/30 rounded-lg px-4 py-3">
      <div className="flex items-start gap-2">
        <span className="text-[#FB7185] text-base leading-none mt-px">⚠</span>
        <div>
          <p className="text-[11px] font-semibold text-[#FB7185] uppercase tracking-wide mb-0.5">
            High-risk indicator
          </p>
          <p className="text-[11px] text-[#98A2B8] leading-relaxed">{text}</p>
        </div>
      </div>
    </div>
  );
}

// "How to change this outcome" affordance (FE-25)
function HowToChangeAffordance() {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-[11px] text-[#8B7CF6] underline underline-offset-2 hover:text-[#a89cf8] transition-colors"
      >
        {open ? '▲' : '▼'} 如何改变这个结果 / How to change this outcome
      </button>
      {open && (
        <div className="mt-2 bg-[#1B2336] border border-[#2A3346] rounded-lg px-4 py-3 text-[11px] text-[#98A2B8] leading-relaxed space-y-1">
          <p>• Adjust your risk tolerance or core values in your profile and re-run.</p>
          <p>• Change the mode (Medium / Heavy) for deeper analysis.</p>
          <p>• Edit the social circle — add or remove key influencers.</p>
          <p>• Reframe the decision with more specific option labels.</p>
        </div>
      )}
    </div>
  );
}

export interface RecommendationStripProps {
  recommendation: RecommendationPayload;
}

export default function RecommendationStrip({ recommendation }: RecommendationStripProps) {
  const color = leaningColor(recommendation.leaning);
  const isHighRisk = Boolean(recommendation.guardrail && recommendation.guardrail.length > 0);

  return (
    <div
      className="sticky bottom-0 z-30 bg-[#141A29] border-t border-[#2A3346] px-6 py-4"
      style={{ boxShadow: '0 -4px 24px rgba(0,0,0,0.4)' }}
    >
      <div className="max-w-5xl mx-auto">
        {/* Leaning badge + rationale */}
        <div className="flex items-start gap-4">
          <div
            className="flex-shrink-0 px-3 py-1.5 rounded-full text-[11px] font-semibold border"
            style={{ color, borderColor: `${color}44`, backgroundColor: `${color}12` }}
          >
            {leaningLabel(recommendation.leaning)}
          </div>
          <p className="text-[12px] text-[#98A2B8] leading-relaxed flex-1 pt-1">
            {recommendation.rationale}
          </p>
        </div>

        {/* Guardrail alert for high-risk results */}
        {isHighRisk && <GuardrailAlert text={recommendation.guardrail} />}

        {/* "How to change" affordance always visible */}
        <HowToChangeAffordance />

        {/* Mandatory simulation disclaimer — SYS-16 */}
        <p className="mt-3 text-[10px] text-[#5F6B82] italic">
          这是模拟，不是预言 — This is a simulation, not a prophecy. Outcomes are probabilistic; no result is guaranteed.
        </p>
      </div>
    </div>
  );
}
