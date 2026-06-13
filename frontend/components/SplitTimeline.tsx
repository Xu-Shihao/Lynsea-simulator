"use client";

import { allMonths, sharedEventIndex } from "../lib/simSelectors";
import { BRANCH_COLORS, MAGENTA } from "../lib/theme";
import type { Branch, BranchPoint, TimelineEvent } from "../lib/types";
import { Icon } from "./Brand";

const KIND_LABEL: Record<TimelineEvent["kind"], string> = {
  skeleton: "Milestone",
  perturbation: "Ripple",
  exogenous: "External",
};

/**
 * The central split timeline (the dashboard centerpiece).
 *  - Vertical center axis.
 *  - Branch A cards on the LEFT (cyan left-border + glow).
 *  - Branch B cards on the RIGHT (amber).
 *  - Aligned by month with Mn axis markers.
 *  - Shared exogenous events centered with a dashed border + "Shared Event" chip.
 *  - Fork / branch-point rendered as a centered magenta pill with the cause text.
 *  - Clicking any event opens the evidence detail.
 */
export function SplitTimeline({
  events,
  options,
  branchPoints,
  onSelect,
  selectedId,
}: {
  events: TimelineEvent[];
  options: [string, string];
  branchPoints: BranchPoint[];
  onSelect: (e: TimelineEvent) => void;
  selectedId: string | null;
}) {
  const months = allMonths(events, []);
  const sharedIdx = sharedEventIndex(events);
  const branchPointsByMonth = new Map<number, BranchPoint>();
  for (const bp of branchPoints) {
    // Keep the largest-magnitude branch point for a month.
    const existing = branchPointsByMonth.get(bp.month);
    if (!existing || bp.magnitude > existing.magnitude) {
      branchPointsByMonth.set(bp.month, bp);
    }
  }

  if (!events.length && !months.length) return null;

  return (
    <div className="flex-1 relative py-xl px-4 md:px-lg overflow-x-hidden">
      {/* Central timeline axis */}
      <div className="absolute left-1/2 top-0 bottom-0 w-[2px] bg-surface-variant -translate-x-1/2 z-0" />

      <div className="max-w-5xl mx-auto relative z-10">
        {months.map((month) => {
          const aEvents = events.filter(
            (e) => e.branch === "A" && e.month === month,
          );
          const bEvents = events.filter(
            (e) => e.branch === "B" && e.month === month,
          );
          // Shared exogenous events surface once, centered.
          const sharedEvents = [...aEvents, ...bEvents].filter(
            (e) => e.is_shared_exogenous,
          );
          const aBranchEvents = aEvents.filter((e) => !e.is_shared_exogenous);
          const bBranchEvents = bEvents.filter((e) => !e.is_shared_exogenous);
          const seenShared = new Set<string>();
          const uniqueShared = sharedEvents.filter((e) => {
            const key = e.shared_event_id ?? e.id;
            if (seenShared.has(key)) return false;
            seenShared.add(key);
            return true;
          });
          const fork = branchPointsByMonth.get(month);

          return (
            <div key={month} className="mb-12">
              {/* Month axis marker */}
              <div className="flex items-center justify-center mb-6 relative">
                <div className="bg-surface-container border border-outline-variant rounded px-3 py-1 font-data-numeric text-data-numeric text-on-surface-variant z-10">
                  M{month}
                </div>
              </div>

              {/* Fork / branch-point pill (magenta, centered) */}
              {fork && (
                <div className="w-full relative mb-8 py-md">
                  <div className="absolute top-1/2 left-1/4 right-1/4 h-[1px] bg-brand-magenta z-0 glow-magenta" />
                  <div className="flex justify-center relative z-10">
                    <div className="bg-surface-container-high border border-brand-magenta rounded-full px-5 py-2.5 flex items-center gap-sm glow-magenta max-w-[36rem] text-center">
                      <span
                        className="w-3 h-3 rounded-full bg-brand-magenta animate-pulse shrink-0"
                        aria-hidden
                      />
                      <span className="font-label text-sm text-brand-magenta">
                        Paths diverge most here — {fork.description}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Shared exogenous events: centered with dashed border. */}
              {uniqueShared.map((e) => (
                <div
                  key={e.id}
                  className="flex justify-center mb-8 relative w-full"
                >
                  <button
                    type="button"
                    onClick={() => onSelect(e)}
                    aria-pressed={selectedId === e.id}
                    className={`bg-surface-container border border-dashed rounded-lg p-md w-full max-w-[36rem] text-center relative z-10 shadow-[0_0_20px_rgba(0,0,0,0.5)] transition focus-ring ${
                      selectedId === e.id
                        ? "border-on-surface-variant ring-1 ring-on-surface-variant"
                        : "border-outline hover:border-on-surface-variant"
                    }`}
                  >
                    <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-surface-variant px-2 py-0.5 rounded text-[10px] font-label text-on-surface-variant uppercase flex items-center gap-1">
                      <Icon name="link" className="text-[12px]" /> Shared Event
                      {e.shared_event_id && sharedIdx[e.shared_event_id]
                        ? ` #${sharedIdx[e.shared_event_id]}`
                        : ""}
                    </span>
                    <h3 className="font-title text-title text-on-surface mb-xs mt-1">
                      {e.title}
                    </h3>
                    <p className="font-caption text-caption text-on-surface-variant">
                      {e.description}
                    </p>
                  </button>
                </div>
              ))}

              {/* Branch A (left) / Branch B (right), aligned at the axis. */}
              {(aBranchEvents.length > 0 || bBranchEvents.length > 0) && (
                <div className="flex w-full relative">
                  {/* Left column = Branch A */}
                  <div className="w-1/2 pr-lg flex flex-col items-end gap-3">
                    {aBranchEvents.map((e) => (
                      <BranchCard
                        key={e.id}
                        event={e}
                        branch="A"
                        selected={selectedId === e.id}
                        onSelect={onSelect}
                      />
                    ))}
                  </div>

                  {/* Axis node */}
                  <div
                    className="absolute left-1/2 top-6 w-4 h-4 rounded-full bg-surface-variant border-2 border-background -translate-x-1/2 z-10"
                    aria-hidden
                  />

                  {/* Right column = Branch B */}
                  <div className="w-1/2 pl-lg flex flex-col items-start gap-3">
                    {bBranchEvents.map((e) => (
                      <BranchCard
                        key={e.id}
                        event={e}
                        branch="B"
                        selected={selectedId === e.id}
                        onSelect={onSelect}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Caption */}
      <p className="max-w-5xl mx-auto mt-2 font-caption text-caption text-outline text-center">
        Both branches run on the same months. Shared external events (dashed,
        centered) hit both futures identically, so any gap is the decision&apos;s
        doing. <span style={{ color: MAGENTA }}>Magenta</span> marks where the
        paths diverge most.
      </p>
    </div>
  );
}

function BranchCard({
  event,
  branch,
  selected,
  onSelect,
}: {
  event: TimelineEvent;
  branch: Branch;
  selected: boolean;
  onSelect: (e: TimelineEvent) => void;
}) {
  const color = BRANCH_COLORS[branch];
  const glow = branch === "A" ? "glow-cyan" : "glow-amber";
  return (
    <button
      type="button"
      onClick={() => onSelect(event)}
      aria-pressed={selected}
      className={`bg-surface-container rounded-lg p-md w-full max-w-[24rem] relative text-left transition animate-in focus-ring ${glow} ${
        selected ? "ring-2" : "hover:brightness-110"
      }`}
      style={{
        borderLeft: `2px solid ${color}`,
        boxShadow: selected ? `0 0 0 2px ${color}` : undefined,
      }}
    >
      <div className="flex items-center gap-1.5 mb-1">
        <span
          className="text-[9px] font-semibold uppercase tracking-wide rounded px-1.5 py-0.5"
          style={{ background: `${color}22`, color }}
        >
          {KIND_LABEL[event.kind]}
        </span>
      </div>
      <h3 className="font-title text-title text-on-surface mb-xs leading-snug">
        {event.title}
      </h3>
      <p className="font-caption text-caption text-on-surface-variant line-clamp-3">
        {event.description}
      </p>
    </button>
  );
}
