"use client";

import type { StatusEvent, StreamPhase } from "../lib/types";

const PHASES: { id: StreamPhase; label: string }[] = [
  { id: "clarify", label: "Clarify" },
  { id: "personas", label: "Personas" },
  { id: "backbone", label: "Backbone" },
  { id: "dimensions", label: "Dimensions" },
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
    <div className="bg-surface-container border border-surface-variant rounded-lg p-md">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-primary pulse-dot" />
          <span className="font-label text-sm text-on-surface">
            {status?.message ?? "Connecting to the simulator…"}
          </span>
        </div>
        <span className="text-xs tabular-nums text-on-surface-variant">
          {progress}%
        </span>
      </div>

      <div className="h-2 rounded-full bg-surface-container-high overflow-hidden">
        <div
          className="h-full rounded-full bg-primary transition-all duration-500"
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
                  ? "border-primary bg-primary/10 text-primary font-medium"
                  : state === "done"
                    ? "border-good/40 bg-good/10 text-good"
                    : "border-surface-variant text-on-surface-variant"
              }`}
            >
              {state === "done" ? "✓ " : ""}
              {p.label}
            </span>
          );
        })}
      </div>
      <p className="mt-2 text-[11px] text-on-surface-variant">
        Results stream in as they&apos;re generated — milestones first, then the
        details that fill in each future.
      </p>
    </div>
  );
}
