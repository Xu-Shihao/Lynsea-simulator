'use client';

import type { Branch, SimulationStatus, TimelineEventPayload } from '@/lib/contract';

interface TimelineColumnProps {
  branch: Branch;
  events: TimelineEventPayload[];
  status: SimulationStatus;
}

function SkeletonCard() {
  return (
    <div className="bg-[#131929] border border-[#2A3346] rounded-lg p-4 mb-3 animate-pulse">
      <div className="h-3 bg-[#1d253a] rounded w-3/4 mb-2" />
      <div className="h-2 bg-[#1d253a] rounded w-full mb-1" />
      <div className="h-2 bg-[#1d253a] rounded w-2/3" />
    </div>
  );
}

function EventCard({ event, branch }: { event: TimelineEventPayload; branch: Branch }) {
  const isShared = event.kind === 'perturbation';
  const cardClass = isShared
    ? 'shared-event-card'
    : branch === 'A'
    ? 'branch-a-card'
    : 'branch-b-card';

  return (
    <div className={`rounded-lg p-3 mb-3 relative bg-[#131929] ${cardClass}`}>
      {isShared && (
        <div className="absolute -top-2.5 left-3 bg-[#1d253a] px-1.5 py-0.5 rounded font-caption text-[10px] text-[#94A3B8] uppercase tracking-wide flex items-center gap-1">
          ≡ Shared Event
        </div>
      )}
      <p className="font-title text-sm text-[#E6EAF2] mb-1 mt-1">{event.title}</p>
      <p className="font-caption text-[11px] text-[#98A2B8] leading-relaxed">{event.detail}</p>
      <div className="flex gap-1 mt-2 flex-wrap items-center">
        <span className="font-caption text-[10px] text-[#5F6B82]">M{event.month}</span>
        {event.personas.slice(0, 3).map(p => (
          <span
            key={p}
            className="px-1.5 py-0.5 rounded bg-[#1d253a] font-caption text-[10px] text-[#98A2B8]"
          >
            {p}
          </span>
        ))}
      </div>
    </div>
  );
}

export function TimelineColumn({ branch, events, status }: TimelineColumnProps) {
  const isLoading = events.length === 0 && (status === 'connecting' || status === 'streaming');

  return (
    <div>
      {isLoading && <SkeletonCard />}
      {events.map(ev => (
        <EventCard key={ev.event_id} event={ev} branch={branch} />
      ))}
    </div>
  );
}
