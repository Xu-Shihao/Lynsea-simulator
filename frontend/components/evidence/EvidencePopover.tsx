'use client';

import { useState, useRef, useEffect } from 'react';
import type { TimelineEventPayload } from '@/lib/contract';

// Evidence item for display — causal chain / belief / event details
interface EvidenceItem {
  kind: 'event' | 'belief' | 'causal';
  label: string;
  detail: string;
}

function buildEvidence(event: TimelineEventPayload): EvidenceItem[] {
  const items: EvidenceItem[] = [];

  // Primary event detail
  items.push({ kind: 'event', label: event.title, detail: event.detail });

  // Personas involved → belief traces
  if (event.personas.length > 0) {
    items.push({
      kind: 'belief',
      label: `Influenced by: ${event.personas.join(', ')}`,
      detail: 'These personas\' stances and influence weights shaped the probability of this event.',
    });
  }

  // Month position → causal chain note
  items.push({
    kind: 'causal',
    label: `Causal position: Month ${event.month}`,
    detail: event.month === 0
      ? 'This is the decision point — all branches originate here.'
      : `This event emerges ~${event.month} month${event.month === 1 ? '' : 's'} after the decision point. Earlier branch events increase or decrease its likelihood.`,
  });

  return items;
}

const KIND_ICON: Record<EvidenceItem['kind'], string> = {
  event: '◆',
  belief: '◉',
  causal: '→',
};

const KIND_COLOR: Record<EvidenceItem['kind'], string> = {
  event: '#8B7CF6',
  belief: '#22D3EE',
  causal: '#FBBF24',
};

interface EvidencePanelProps {
  event: TimelineEventPayload;
  onClose: () => void;
}

function EvidencePanel({ event, onClose }: EvidencePanelProps) {
  const items = buildEvidence(event);

  return (
    <div
      className="absolute z-50 w-72 bg-[#1B2336] border border-[#2A3346] rounded-xl shadow-2xl p-4"
      style={{ boxShadow: '0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(139,124,246,0.15)' }}
    >
      <div className="flex items-start justify-between mb-3">
        <span className="text-[11px] font-semibold text-[#8B7CF6] uppercase tracking-widest">
          Evidence
        </span>
        <button
          onClick={onClose}
          className="text-[#5F6B82] hover:text-[#98A2B8] text-sm leading-none transition-colors"
          aria-label="Close evidence"
        >
          ✕
        </button>
      </div>

      <div className="space-y-3">
        {items.map((item, i) => (
          <div key={i} className="flex gap-2">
            <span
              className="flex-shrink-0 mt-0.5 text-[13px] leading-none"
              style={{ color: KIND_COLOR[item.kind] }}
            >
              {KIND_ICON[item.kind]}
            </span>
            <div>
              <p className="text-[11px] font-semibold text-[#E6EAF2] mb-0.5">{item.label}</p>
              <p className="text-[10px] text-[#5F6B82] leading-relaxed">{item.detail}</p>
            </div>
          </div>
        ))}
      </div>

      {/* event_id ref */}
      <p className="mt-3 pt-2 border-t border-[#1F2738] text-[9px] text-[#5F6B82] font-mono">
        id: {event.event_id}
      </p>
    </div>
  );
}

export interface EvidencePopoverProps {
  event: TimelineEventPayload;
  /** The trigger element — wraps children and intercepts click */
  children: React.ReactNode;
  placement?: 'top' | 'bottom';
}

export default function EvidencePopover({ event, children, placement = 'bottom' }: EvidencePopoverProps) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function handler(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div ref={wrapRef} className="relative inline-block">
      {/* Wrap children; clicking opens the popover */}
      <div
        onClick={(e) => { e.stopPropagation(); setOpen((v) => !v); }}
        className="cursor-pointer group"
        title="View evidence"
      >
        {children}
        {/* Small indicator dot */}
        <span
          className="absolute -top-1 -right-1 w-2 h-2 rounded-full border border-[#1B2336]"
          style={{ backgroundColor: '#8B7CF6', boxShadow: '0 0 4px rgba(139,124,246,0.6)' }}
        />
      </div>

      {open && (
        <div
          className={`absolute ${placement === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'} left-0`}
        >
          <EvidencePanel event={event} onClose={() => setOpen(false)} />
        </div>
      )}
    </div>
  );
}
