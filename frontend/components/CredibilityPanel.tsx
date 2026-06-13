"use client";

import { credibilityBand } from "../lib/theme";
import type { CredibilityCard } from "../lib/types";

export function CredibilityPanel({ card }: { card: CredibilityCard }) {
  const band = credibilityBand(card.overall);
  return (
    <section className="card p-5">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <h2 className="text-lg font-semibold text-[var(--ink)]">
            How much to trust this
          </h2>
          <p className="text-xs text-[var(--muted)] mt-0.5">
            A self-assessed confidence read — not a measure of what will happen.
          </p>
        </div>
        <div className="text-right">
          <div
            className="text-2xl font-semibold tabular-nums"
            style={{ color: band.color }}
          >
            {Math.round(card.overall * 100)}%
          </div>
          <div
            className="text-[11px] font-medium"
            style={{ color: band.color }}
          >
            {band.label}
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <ScoreBar label="Data sufficiency" value={card.data_sufficiency} />
        <ScoreBar label="Causal confidence" value={card.causal_confidence} />
        <ScoreBar label="Event plausibility" value={card.event_plausibility} />
      </div>

      {card.notes.length > 0 && (
        <ul className="mt-4 space-y-1.5">
          {card.notes.map((n, i) => (
            <li
              key={i}
              className="flex gap-2 text-xs text-[var(--muted)] leading-relaxed"
            >
              <span className="text-[var(--accent)]" aria-hidden>
                •
              </span>
              <span>{n}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  const band = credibilityBand(value);
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-[var(--ink)]">{label}</span>
        <span className="tabular-nums text-[var(--muted)]">{pct}%</span>
      </div>
      <div className="h-2 rounded-full bg-[var(--surface-2)] overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${pct}%`, background: band.color }}
        />
      </div>
    </div>
  );
}
