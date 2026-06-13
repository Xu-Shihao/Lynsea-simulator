"use client";

import Link from "next/link";
import { useState } from "react";
import { BRANCH_COLORS } from "../lib/theme";
import type { Persona } from "../lib/types";
import { Icon } from "./Brand";

/**
 * FE-02: After the `clarify` phase, show a structured summary of what Lynsea
 * understood — the decision, the two options (branches), the affected people,
 * and any key constraints/assumptions — so the user can confirm it is correct
 * (or start over to modify it) before reading the two futures.
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
  constraints?: string[];
}) {
  const [confirmed, setConfirmed] = useState(false);

  if (!decision && !options[0] && !options[1]) return null;

  return (
    <section
      className="bg-surface-container border border-surface-variant rounded-lg p-md border-l-2 border-l-primary"
      aria-label="What Lynsea understood"
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <h2 className="font-title text-title text-on-surface">
            What Lynsea understood
          </h2>
          <p className="text-xs text-on-surface-variant mt-0.5">
            Confirm this matches your situation. If anything is off, start a new
            simulation to adjust it.
          </p>
        </div>
        {confirmed && (
          <span className="inline-flex items-center gap-1 rounded-full bg-good/10 px-2.5 py-1 text-[11px] font-medium text-good">
            <Icon name="check_circle" className="text-[14px]" /> Confirmed
          </span>
        )}
      </div>

      {decision && (
        <div className="mb-4">
          <div className="text-[11px] font-medium uppercase tracking-wide text-outline mb-1">
            Decision
          </div>
          <p className="text-sm text-on-surface leading-relaxed">{decision}</p>
        </div>
      )}

      <div className="mb-4">
        <div className="text-[11px] font-medium uppercase tracking-wide text-outline mb-1.5">
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
                className="flex items-center gap-2 rounded-lg border bg-surface-container-low px-3 py-2"
                style={{ borderColor: `${color}55` }}
              >
                <span
                  className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-surface"
                  style={{ background: color }}
                >
                  {branch}
                </span>
                <span className="text-sm text-on-surface">{text}</span>
              </div>
            );
          })}
        </div>
      </div>

      {personas.length > 0 && (
        <div className="mb-4">
          <div className="text-[11px] font-medium uppercase tracking-wide text-outline mb-1.5">
            People affected
          </div>
          <div className="flex flex-wrap gap-1.5">
            {personas.map((p) => (
              <span
                key={p.id}
                className="inline-flex items-center gap-1 rounded-full bg-surface-container-high px-2.5 py-1 text-xs text-on-surface"
              >
                {p.name}
                <span className="text-on-surface-variant">· {p.role}</span>
                {p.is_default_inferred && (
                  <span
                    className="ml-0.5 text-warn"
                    title="Inferred from limited information"
                    aria-label="Inferred from limited information"
                  >
                    <Icon name="warning" className="text-[12px]" />
                  </span>
                )}
              </span>
            ))}
          </div>
        </div>
      )}

      {constraints && constraints.length > 0 && (
        <div className="mb-4">
          <div className="text-[11px] font-medium uppercase tracking-wide text-outline mb-1.5">
            Key constraints &amp; assumptions
          </div>
          <ul className="space-y-1">
            {constraints.map((c, i) => (
              <li
                key={i}
                className="flex gap-2 text-xs text-on-surface-variant leading-relaxed"
              >
                <span className="text-primary" aria-hidden>
                  •
                </span>
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!confirmed && (
        <div className="flex flex-col sm:flex-row gap-2 pt-1">
          <button
            type="button"
            onClick={() => setConfirmed(true)}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary-fixed hover:bg-primary-dim focus-ring"
          >
            Looks right — continue
          </button>
          <Link
            href="/"
            className="rounded-lg border border-surface-variant px-4 py-2 text-center text-sm font-medium text-on-surface hover:bg-surface-container-high focus-ring"
          >
            Something&apos;s off — adjust
          </Link>
        </div>
      )}
    </section>
  );
}
