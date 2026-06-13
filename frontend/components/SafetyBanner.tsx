"use client";

import { Icon } from "./Brand";

export function SafetyBanner({ highRisk }: { highRisk: boolean }) {
  if (!highRisk) {
    // Always-present, low-key reminder.
    return (
      <div className="rounded-lg border border-surface-variant bg-surface-container px-4 py-2.5 text-xs text-on-surface-variant">
        These are simulated probabilities, not predictions. Phrasing like
        “likely” and “~60%” is intentional — the future stays yours to write.
      </div>
    );
  }

  return (
    <div className="rounded-lg border-2 border-warn/40 bg-warn/[0.06] px-4 py-3.5">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-warn/15 text-warn">
          <Icon name="warning" className="text-[18px]" fill />
        </span>
        <div>
          <div className="font-title text-on-surface font-semibold">
            This is a simulation, not a prophecy.
          </div>
          <p className="mt-1 text-sm text-on-surface leading-relaxed">
            One or more paths show a sharp dip in a life dimension. Treat this as
            a “what could happen” warning, not a verdict. The biggest levers are
            usually yours.
          </p>
          <div className="mt-2 rounded-lg bg-surface-container border border-surface-variant px-3 py-2 text-xs text-on-surface-variant">
            <span className="font-medium text-on-surface">
              How to change this outcome:
            </span>{" "}
            look at the divergence months in the timeline — small early choices
            (boundaries, conversations, timing) tend to bend these curves the
            most.
          </div>
        </div>
      </div>
    </div>
  );
}
