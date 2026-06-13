"use client";

import { STANCE_STYLES } from "../lib/theme";
import type { Big5, Persona } from "../lib/types";
import { Icon } from "./Brand";

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
    <section className="bg-surface-container border border-surface-variant rounded-lg p-md">
      <h2 className="font-title text-title text-on-surface mb-1">
        Who shapes this decision
      </h2>
      <p className="text-xs text-on-surface-variant mb-4">
        Modeled stakeholders and their likely leanings. Some are inferred from
        limited information.
      </p>
      <div className="grid sm:grid-cols-2 gap-3">
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
    <div className="rounded-lg border border-surface-variant bg-surface-container-low p-3.5 animate-in">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-medium text-on-surface">{persona.name}</div>
          <div className="text-xs text-on-surface-variant">{persona.role}</div>
        </div>
        <span
          className="text-[10px] font-medium rounded-full px-2 py-0.5 border"
          style={{
            background: stance.bg,
            color: stance.fg,
            borderColor: stance.border,
          }}
        >
          {stance.label}
        </span>
      </div>

      {lowConfidence && (
        <div className="mt-2 inline-flex items-center gap-1 rounded-md bg-warn/10 px-2 py-0.5 text-[10px] font-medium text-warn">
          <Icon name="warning" className="text-[12px]" /> Inferred — directional
          only
        </div>
      )}

      <div className="mt-2.5 text-xs text-on-surface-variant">
        {persona.decision_style}
      </div>

      <div className="mt-3 space-y-1">
        {BIG5_LABELS.map(({ key, label }) => (
          <div key={key} className="flex items-center gap-2">
            <span className="w-[120px] text-[10px] text-on-surface-variant truncate">
              {label}
            </span>
            <div className="flex-1 h-1.5 rounded-full bg-surface-variant overflow-hidden">
              <div
                className="h-full rounded-full bg-primary/70"
                style={{ width: `${(persona.big5[key] / 10) * 100}%` }}
              />
            </div>
            <span className="w-5 text-right text-[10px] tabular-nums text-on-surface-variant">
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
              className="text-[10px] rounded-full bg-surface-variant px-2 py-0.5 text-on-surface-variant"
            >
              {c}
            </span>
          ))}
        </div>
      )}

      <div className="mt-3 flex justify-between text-[10px] text-on-surface-variant">
        <span>Risk tolerance {persona.risk_tolerance}/10</span>
        <span>Influence {persona.influence_weight}/10</span>
      </div>
    </div>
  );
}
