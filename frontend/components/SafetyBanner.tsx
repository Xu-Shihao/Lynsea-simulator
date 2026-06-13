"use client";

export function SafetyBanner({ highRisk }: { highRisk: boolean }) {
  if (!highRisk) {
    // Always-present, low-key reminder.
    return (
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-2)] px-4 py-2.5 text-xs text-[var(--muted)]">
        These are simulated probabilities, not predictions. Phrasing like
        &ldquo;likely&rdquo; and &ldquo;~60%&rdquo; is intentional — the future
        stays yours to write.
      </div>
    );
  }

  return (
    <div className="rounded-xl border-2 border-[var(--warn)]/40 bg-[var(--warn)]/[0.06] px-4 py-3.5">
      <div className="flex items-start gap-3">
        <span
          className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--warn)]/15 text-[var(--warn)]"
          aria-hidden
        >
          ⚠
        </span>
        <div>
          <div className="font-semibold text-[var(--ink)]">
            This is a simulation, not a prophecy.
          </div>
          <p className="mt-1 text-sm text-[var(--foreground)] leading-relaxed">
            One or more paths show a sharp dip in a life dimension. Treat this
            as a &ldquo;what could happen&rdquo; warning, not a verdict. The
            biggest levers are usually yours.
          </p>
          <div className="mt-2 rounded-lg bg-[var(--surface)] border border-[var(--border)] px-3 py-2 text-xs text-[var(--muted)]">
            <span className="font-medium text-[var(--ink)]">
              How to change this outcome:
            </span>{" "}
            look at the divergence months below — small early choices
            (boundaries, conversations, timing) tend to bend these curves the
            most.
          </div>
        </div>
      </div>
    </div>
  );
}
