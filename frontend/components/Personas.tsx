"use client";

import { STANCE_STYLES } from "../lib/theme";
import type { Big5, Persona } from "../lib/types";

const BIG5_LABELS: { key: keyof Big5; label: string }[] = [
  { key: "O", label: "Openness" },
  { key: "C", label: "Conscientiousness" },
  { key: "E", label: "Extraversion" },
  { key: "A", label: "Agreeableness" },
  { key: "N", label: "Neuroticism" },
];

export function Personas({
  personas,
  lowConfidenceIds,
}: {
  personas: Persona[];
  lowConfidenceIds: string[];
}) {
  if (!personas.length) return null;
  const lowSet = new Set(lowConfidenceIds);

  return (
    <section className="card p-5">
      <h2 className="text-lg font-semibold text-[var(--ink)] mb-1">
        Who shapes this decision
      </h2>
      <p className="text-xs text-[var(--muted)] mb-4">
        Modeled stakeholders and their likely leanings. Some are inferred from
        limited information.
      </p>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {personas.map((p) => (
          <PersonaCard
            key={p.id}
            persona={p}
            lowConfidence={p.is_default_inferred || lowSet.has(p.id)}
          />
        ))}
      </div>
    </section>
  );
}

function PersonaCard({
  persona,
  lowConfidence,
}: {
  persona: Persona;
  lowConfidence: boolean;
}) {
  const stance = STANCE_STYLES[persona.stance];
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3.5 animate-in">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-medium text-[var(--ink)]">{persona.name}</div>
          <div className="text-xs text-[var(--muted)]">{persona.role}</div>
        </div>
        <span
          className="text-[10px] font-medium rounded-full px-2 py-0.5"
          style={{ background: stance.bg, color: stance.fg }}
        >
          {stance.label}
        </span>
      </div>

      {lowConfidence && (
        <div className="mt-2 inline-flex items-center gap-1 rounded-md bg-[var(--warn)]/10 px-2 py-0.5 text-[10px] font-medium text-[var(--warn)]">
          ⚠ Limited info — directional only
        </div>
      )}

      <div className="mt-2.5 text-xs text-[var(--muted)]">
        {persona.decision_style}
      </div>

      {/* Big Five mini-bars */}
      <div className="mt-3 space-y-1">
        {BIG5_LABELS.map(({ key, label }) => (
          <div key={key} className="flex items-center gap-2">
            <span className="w-[120px] text-[10px] text-[var(--muted)] truncate">
              {label}
            </span>
            <div className="flex-1 h-1.5 rounded-full bg-[var(--surface-2)] overflow-hidden">
              <div
                className="h-full rounded-full bg-[var(--accent)]/70"
                style={{ width: `${(persona.big5[key] / 10) * 100}%` }}
              />
            </div>
            <span className="w-5 text-right text-[10px] tabular-nums text-[var(--muted)]">
              {persona.big5[key]}
            </span>
          </div>
        ))}
      </div>

      {persona.key_concerns.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {persona.key_concerns.map((c) => (
            <span
              key={c}
              className="text-[10px] rounded-full bg-[var(--surface-2)] px-2 py-0.5 text-[var(--muted)]"
            >
              {c}
            </span>
          ))}
        </div>
      )}

      <div className="mt-3 flex justify-between text-[10px] text-[var(--muted)]">
        <span>Risk tolerance {persona.risk_tolerance}/10</span>
        <span>Influence {persona.influence_weight}/10</span>
      </div>
    </div>
  );
}
