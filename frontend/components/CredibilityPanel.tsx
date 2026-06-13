"use client";

import { credibilityBand } from "../lib/theme";
import type { CredibilityCard } from "../lib/types";
import { Icon } from "./Brand";

/**
 * Simulation Credibility card (FE-23 uncertainty). Matches the Stitch sidebar
 * card: overall score, the three sub-scores as bars (data_sufficiency,
 * causal_confidence, event_plausibility), the notes, and the
 * "directional only; personas built from limited input" caveat.
 */
export function CredibilityPanel({ card }: { card: CredibilityCard }) {
  const overall = Math.round(card.overall * 100);
  const band = credibilityBand(card.overall);

  return (
    <div className="bg-surface-container rounded-lg p-md border border-surface-variant">
      <div className="flex items-center gap-sm mb-sm">
        <Icon name="fact_check" className="text-outline" />
        <h4 className="font-label text-on-surface">Simulation Credibility</h4>
        <span className="ml-auto font-data-numeric text-data-numeric text-on-surface">
          {overall}/100
        </span>
      </div>

      <div className="space-y-2 mb-sm">
        <ScoreBar label="Data sufficiency" value={card.data_sufficiency} />
        <ScoreBar label="Causal confidence" value={card.causal_confidence} />
        <ScoreBar label="Event plausibility" value={card.event_plausibility} />
      </div>

      <div
        className="text-[11px] font-medium mb-2"
        style={{ color: band.color }}
      >
        {band.label}
      </div>

      {card.notes.length > 0 && (
        <ul className="space-y-1 mb-2">
          {card.notes.map((n, i) => (
            <li
              key={i}
              className="flex gap-1.5 text-[10px] text-on-surface-variant leading-relaxed"
            >
              <span className="text-primary" aria-hidden>
                •
              </span>
              <span>{n}</span>
            </li>
          ))}
        </ul>
      )}

      <p className="text-[10px] text-outline italic">
        Directional only; personas built from limited input.
      </p>
    </div>
  );
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div>
      <div className="flex justify-between text-[10px] text-on-surface-variant mb-1">
        <span>{label}</span>
        <span className="tabular-nums">{pct}</span>
      </div>
      <div className="h-1 bg-surface-variant rounded-full overflow-hidden">
        <div className="h-full bg-outline" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
