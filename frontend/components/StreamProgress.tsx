"use client";

import type { StatusEvent, StreamPhase } from "../lib/types";

const PHASES: { id: StreamPhase; label: string }[] = [
  { id: "clarify", label: "Clarify" },
  { id: "personas", label: "Personas" },
  { id: "backbone", label: "Backbone" },
  { id: "branchA", label: "Future A" },
  { id: "branchB", label: "Future B" },
  { id: "scoring", label: "Scoring" },
  { id: "done", label: "Done" },
];

export function StreamProgress({
  status,
  done,
}: {
  status: StatusEvent | null;
  done: boolean;
}) {
  if (done && status?.phase === "done") return null;

  const progress = status ? Math.round(status.progress * 100) : 4;
  const activeIndex = status
    ? PHASES.findIndex((p) => p.id === status.phase)
    : 0;

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--accent)]/50" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-[var(--accent)]" />
          </span>
          <span className="text-sm font-medium text-[var(--ink)]">
            {status?.message ?? "Connecting to the simulator…"}
          </span>
        </div>
        <span className="text-xs tabular-nums text-[var(--muted)]">
          {progress}%
        </span>
      </div>

      <div className="h-2 rounded-full bg-[var(--surface-2)] overflow-hidden">
        <div
          className="h-full rounded-full bg-[var(--accent)] transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {PHASES.map((p, i) => {
          const state =
            i < activeIndex ? "done" : i === activeIndex ? "active" : "todo";
          return (
            <span
              key={p.id}
              className={`text-[10px] rounded-full px-2 py-0.5 border ${
                state === "active"
                  ? "border-[var(--accent)] bg-[var(--accent)]/10 text-[var(--accent)] font-medium"
                  : state === "done"
                    ? "border-[var(--good)]/30 bg-[var(--good)]/10 text-[var(--good)]"
                    : "border-[var(--border)] text-[var(--muted)]"
              }`}
            >
              {state === "done" ? "✓ " : ""}
              {p.label}
            </span>
          );
        })}
      </div>
      <p className="mt-2 text-[11px] text-[var(--muted)]">
        Results stream in as they&apos;re generated — milestones first, then the
        details that fill in each future.
      </p>
    </div>
  );
}
