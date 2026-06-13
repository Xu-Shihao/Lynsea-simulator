"use client";

import { allMonths, sharedEventIndex } from "../lib/simSelectors";
import { BRANCH_COLORS, BRANCH_SOFT, SHARED_COLOR } from "../lib/theme";
import type { Branch, BranchPoint, TimelineEvent } from "../lib/types";

const KIND_LABEL: Record<TimelineEvent["kind"], string> = {
  skeleton: "Milestone",
  perturbation: "Ripple",
  exogenous: "External",
};

export function SmallMultiples({
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
  const branchPointMonths = new Set(branchPoints.map((b) => b.month));

  if (!events.length && !months.length) return null;

  return (
    <section className="card p-5">
      <div className="mb-1 flex items-baseline justify-between flex-wrap gap-2">
        <h2 className="text-lg font-semibold text-[var(--ink)]">
          Two futures, one shared timeline
        </h2>
        <div className="flex items-center gap-2 text-xs text-[var(--muted)]">
          <span
            className="inline-flex items-center gap-1 chip"
            style={{ borderColor: `${SHARED_COLOR}55`, color: SHARED_COLOR }}
          >
            ⟂ Shared external event
          </span>
        </div>
      </div>
      <p className="text-xs text-[var(--muted)] mb-4">
        Both columns run on the same months. Only the decision differs — shared
        external events (linked in violet) hit both futures identically, so any
        gap you see is the decision&apos;s doing.
      </p>

      {/* Column headers */}
      <div className="grid grid-cols-[2.5rem_1fr_1fr] gap-3 mb-2">
        <div />
        <ColumnHeader branch="A" label={options[0]} />
        <ColumnHeader branch="B" label={options[1]} />
      </div>

      {/* Rows by month */}
      <div className="space-y-2">
        {months.map((month) => {
          const aEvents = events.filter(
            (e) => e.branch === "A" && e.month === month,
          );
          const bEvents = events.filter(
            (e) => e.branch === "B" && e.month === month,
          );
          const isBranchPoint = branchPointMonths.has(month);
          return (
            <div
              key={month}
              className={`grid grid-cols-[2.5rem_1fr_1fr] gap-3 rounded-xl p-1.5 ${
                isBranchPoint
                  ? "bg-[var(--accent)]/[0.04] ring-1 ring-[var(--accent)]/25"
                  : ""
              }`}
            >
              <div className="flex flex-col items-center justify-start pt-1.5">
                <div className="text-xs font-semibold tabular-nums text-[var(--ink)]">
                  M{month}
                </div>
                {isBranchPoint && (
                  <div
                    className="mt-1 text-[9px] font-medium text-[var(--accent)] text-center leading-tight"
                    title="Branch point: the futures diverge here"
                  >
                    diverge
                  </div>
                )}
              </div>
              <ColumnCell
                events={aEvents}
                branch="A"
                sharedIdx={sharedIdx}
                onSelect={onSelect}
                selectedId={selectedId}
              />
              <ColumnCell
                events={bEvents}
                branch="B"
                sharedIdx={sharedIdx}
                onSelect={onSelect}
                selectedId={selectedId}
              />
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ColumnHeader({ branch, label }: { branch: Branch; label: string }) {
  const color = BRANCH_COLORS[branch];
  return (
    <div
      className="rounded-lg px-3 py-2 border"
      style={{ borderColor: `${color}55`, background: `${color}0d` }}
    >
      <div className="flex items-center gap-2">
        <span
          className="inline-flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-bold text-white"
          style={{ background: color }}
        >
          {branch}
        </span>
        <span className="text-sm font-medium" style={{ color }}>
          {label}
        </span>
      </div>
    </div>
  );
}

function ColumnCell({
  events,
  branch,
  sharedIdx,
  onSelect,
  selectedId,
}: {
  events: TimelineEvent[];
  branch: Branch;
  sharedIdx: Record<string, number>;
  onSelect: (e: TimelineEvent) => void;
  selectedId: string | null;
}) {
  if (!events.length) {
    return (
      <div className="rounded-lg border border-dashed border-[var(--border)] min-h-[3rem]" />
    );
  }
  return (
    <div className="space-y-1.5">
      {events.map((e) => (
        <EventCard
          key={e.id}
          event={e}
          branch={branch}
          sharedNumber={
            e.shared_event_id ? sharedIdx[e.shared_event_id] : undefined
          }
          onSelect={onSelect}
          selected={selectedId === e.id}
        />
      ))}
    </div>
  );
}

function EventCard({
  event,
  branch,
  sharedNumber,
  onSelect,
  selected,
}: {
  event: TimelineEvent;
  branch: Branch;
  sharedNumber?: number;
  onSelect: (e: TimelineEvent) => void;
  selected: boolean;
}) {
  const shared = event.is_shared_exogenous;
  const accent = shared ? SHARED_COLOR : BRANCH_COLORS[branch];
  const soft = shared ? "#f3e8ff" : BRANCH_SOFT[branch];

  return (
    <button
      type="button"
      onClick={() => onSelect(event)}
      className={`w-full text-left rounded-lg border p-2.5 transition animate-in focus-ring ${
        selected ? "ring-2" : "hover:shadow-sm"
      }`}
      style={{
        borderColor: `${accent}66`,
        background: selected ? soft : "var(--surface)",
        boxShadow: selected ? `0 0 0 2px ${accent}55` : undefined,
      }}
      aria-pressed={selected}
    >
      <div className="flex items-center gap-1.5 mb-0.5">
        <span
          className="text-[9px] font-semibold uppercase tracking-wide rounded px-1 py-0.5"
          style={{ background: soft, color: accent }}
        >
          {KIND_LABEL[event.kind]}
        </span>
        {shared && sharedNumber != null && (
          <span
            className="text-[9px] font-semibold rounded px-1 py-0.5"
            style={{ background: "#f3e8ff", color: SHARED_COLOR }}
            title="Same external event in both futures"
          >
            ⟂ Shared #{sharedNumber}
          </span>
        )}
      </div>
      <div className="text-[13px] font-medium leading-snug text-[var(--ink)]">
        {event.title}
      </div>
      <div className="text-[11px] text-[var(--muted)] line-clamp-2 mt-0.5">
        {event.description}
      </div>
    </button>
  );
}
