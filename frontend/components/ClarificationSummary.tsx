"use client";

import Link from "next/link";
import { useState } from "react";
import { BRANCH_COLORS } from "../lib/theme";
import type { Persona } from "../lib/types";

/**
 * FE-02: After the `clarify` phase, show a structured summary of what Lynsea
 * understood — the decision, the two options (branches), the affected people,
 * and any key constraints/assumptions — so the user can confirm it is correct
 * (or start over to modify it) before reading the two futures.
 *
 * The data is sourced entirely from the existing contract:
 *   - options      -> the two branch options (request echo / stream)
 *   - people/roles -> personas built from affected_people (persona stream)
 *   - constraints  -> credibility notes (the assumptions Lynsea is working under)
 * No new backend payload is required.
 */
export function ClarificationSummary({
  decision,
  options,
  personas,
  constraints,
}: {
  decision: string;
  options: [string, string];
  personas: Persona[];
  /** Optional assumptions/constraints Lynsea is working under. */
  constraints?: string[];
}) {
  const [confirmed, setConfirmed] = useState(false);

  // Nothing meaningful to confirm yet.
  if (!decision && !options[0] && !options[1]) return null;

  return (
    <section
      className="card p-5 border-l-4 border-l-[var(--accent)]"
      aria-label="What Lynsea understood"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <h2 className="text-lg font-semibold text-[var(--ink)]">
            What Lynsea understood
          </h2>
          <p className="text-xs text-[var(--muted)] mt-0.5">
            Confirm this matches your situation. If anything is off, start a new
            simulation to adjust it.
          </p>
        </div>
        {confirmed && (
          <span className="inline-flex items-center gap-1 rounded-full bg-[var(--good)]/10 px-2.5 py-1 text-[11px] font-medium text-[var(--good)]">
            ✓ Confirmed
          </span>
        )}
      </div>

      {/* Decision */}
      {decision && (
        <div className="mb-4">
          <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--muted)] mb-1">
            Decision
          </div>
          <p className="text-sm text-[var(--ink)] leading-relaxed">
            {decision}
          </p>
        </div>
      )}

      {/* Options / branches */}
      <div className="mb-4">
        <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--muted)] mb-1.5">
          Options compared
        </div>
        <div className="grid sm:grid-cols-2 gap-2">
          {(["A", "B"] as const).map((branch, i) => {
            const text = options[i];
            if (!text) return null;
            const color = BRANCH_COLORS[branch];
            return (
              <div
                key={branch}
                className="flex items-center gap-2 rounded-lg border bg-[var(--surface)] px-3 py-2"
                style={{ borderColor: `${color}55` }}
              >
                <span
                  className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-white"
                  style={{ background: color }}
                >
                  {branch}
                </span>
                <span className="text-sm text-[var(--ink)]">{text}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Affected people */}
      {personas.length > 0 && (
        <div className="mb-4">
          <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--muted)] mb-1.5">
            People affected
          </div>
          <div className="flex flex-wrap gap-1.5">
            {personas.map((p) => (
              <span
                key={p.id}
                className="inline-flex items-center gap-1 rounded-full bg-[var(--surface-2)] px-2.5 py-1 text-xs text-[var(--ink)]"
              >
                {p.name}
                <span className="text-[var(--muted)]">· {p.role}</span>
                {p.is_default_inferred && (
                  <span
                    className="ml-0.5 text-[var(--warn)]"
                    title="Inferred from limited information"
                    aria-label="Inferred from limited information"
                  >
                    ⚠
                  </span>
                )}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Key constraints / assumptions */}
      {constraints && constraints.length > 0 && (
        <div className="mb-4">
          <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--muted)] mb-1.5">
            Key constraints &amp; assumptions
          </div>
          <ul className="space-y-1">
            {constraints.map((c, i) => (
              <li
                key={i}
                className="flex gap-2 text-xs text-[var(--muted)] leading-relaxed"
              >
                <span className="text-[var(--accent)]" aria-hidden>
                  •
                </span>
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Confirm / modify */}
      {!confirmed && (
        <div className="flex flex-col sm:flex-row gap-2 pt-1">
          <button
            type="button"
            onClick={() => setConfirmed(true)}
            className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white hover:brightness-105 focus-ring"
          >
            Looks right — continue
          </button>
          <Link
            href="/"
            className="rounded-lg border border-[var(--border)] px-4 py-2 text-center text-sm font-medium hover:bg-[var(--surface-2)] focus-ring"
          >
            Something&apos;s off — adjust
          </Link>
        </div>
      )}
    </section>
  );
}
