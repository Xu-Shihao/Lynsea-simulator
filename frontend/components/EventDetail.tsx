"use client";

import { useEffect } from "react";
import { BRANCH_COLORS, SHARED_COLOR } from "../lib/theme";
import {
  METRIC_KEYS,
  METRIC_LABELS,
  type MetricKey,
  type MetricPoint,
  type Persona,
  type TimelineEvent,
} from "../lib/types";

export function EventDetail({
  event,
  personas,
  metrics,
  options,
  onClose,
}: {
  event: TimelineEvent | null;
  personas: Persona[];
  metrics: MetricPoint[];
  options: [string, string];
  onClose: () => void;
}) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    if (event) window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [event, onClose]);

  if (!event) return null;

  const accent = event.is_shared_exogenous
    ? SHARED_COLOR
    : BRANCH_COLORS[event.branch];
  const branchLabel = event.branch === "A" ? options[0] : options[1];

  const involved = personas.filter((p) =>
    event.involved_personas.includes(p.id),
  );
  const involvedFallback = event.involved_personas.filter(
    (id) => !personas.some((p) => p.id === id),
  );

  // Which metrics list this event as a supporting cause?
  const supportedMetrics: { key: MetricKey; month: number; value: number }[] =
    [];
  for (const m of metrics) {
    if (m.supporting_event_ids.includes(event.id)) {
      for (const k of METRIC_KEYS) {
        supportedMetrics.push({ key: k, month: m.month, value: m[k] });
      }
      break;
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end"
      role="dialog"
      aria-modal="true"
      aria-label={event.title}
    >
      <button
        type="button"
        aria-label="Close detail"
        onClick={onClose}
        className="absolute inset-0 bg-black/30 backdrop-blur-[2px]"
      />
      <aside className="relative h-full w-full max-w-md bg-[var(--surface)] shadow-2xl overflow-y-auto animate-in">
        <div className="sticky top-0 bg-[var(--surface)] border-b border-[var(--border)] px-5 py-3 flex items-start gap-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span
                className="inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold text-white"
                style={{ background: BRANCH_COLORS[event.branch] }}
              >
                {event.branch}
              </span>
              <span className="text-xs text-[var(--muted)]">
                Month {event.month} · {branchLabel}
              </span>
              {event.is_shared_exogenous && (
                <span
                  className="text-[10px] font-semibold rounded px-1.5 py-0.5"
                  style={{ background: "#f3e8ff", color: SHARED_COLOR }}
                >
                  ⟂ Shared external event
                </span>
              )}
            </div>
            <h3 className="text-base font-semibold text-[var(--ink)] leading-snug">
              {event.title}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-[var(--muted)] hover:text-[var(--ink)] text-xl leading-none focus-ring rounded px-1"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="px-5 py-4 space-y-5">
          <Section title="What happens">
            <p className="text-sm text-[var(--foreground)] leading-relaxed">
              {event.description}
            </p>
          </Section>

          <Section title="Why we think so (evidence)">
            {event.evidence ? (
              <p
                className="text-sm leading-relaxed rounded-lg border-l-2 pl-3 py-1 text-[var(--foreground)]"
                style={{ borderColor: accent }}
              >
                {event.evidence}
              </p>
            ) : (
              <p className="text-sm text-[var(--muted)] italic">
                No specific supporting detail — treat this as a plausible,
                directional beat rather than a strong claim.
              </p>
            )}
          </Section>

          <Section title="People involved">
            {involved.length || involvedFallback.length ? (
              <div className="flex flex-wrap gap-1.5">
                {involved.map((p) => (
                  <span key={p.id} className="chip">
                    {p.name}
                    <span className="text-[var(--muted)]">· {p.role}</span>
                  </span>
                ))}
                {involvedFallback.map((id) => (
                  <span key={id} className="chip text-[var(--muted)]">
                    {id}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[var(--muted)]">Just you.</p>
            )}
          </Section>

          {supportedMetrics.length > 0 && (
            <Section title="Dimensions it influences (this month)">
              <div className="grid grid-cols-2 gap-2">
                {supportedMetrics.map((m) => (
                  <div
                    key={m.key}
                    className="rounded-lg border border-[var(--border)] px-2.5 py-1.5"
                  >
                    <div className="text-[11px] text-[var(--muted)]">
                      {METRIC_LABELS[m.key]}
                    </div>
                    <div className="text-sm font-medium tabular-nums text-[var(--ink)]">
                      ~{Math.round(m.value)}
                      <span className="text-[var(--muted)] text-xs">/100</span>
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          )}
        </div>
      </aside>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)] mb-1.5">
        {title}
      </h4>
      {children}
    </div>
  );
}
