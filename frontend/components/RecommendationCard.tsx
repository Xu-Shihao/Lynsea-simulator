"use client";

import { BRANCH_COLORS } from "../lib/theme";
import type { Recommendation } from "../lib/types";

export function RecommendationCard({
  recommendation,
  options,
}: {
  recommendation: Recommendation;
  options: [string, string];
}) {
  const fav = recommendation.favored_branch;
  const isTie = fav === "tie";
  const color = isTie ? "var(--accent)" : BRANCH_COLORS[fav];
  const favLabel = isTie
    ? "Roughly even"
    : fav === "A"
      ? options[0]
      : options[1];

  return (
    <section
      className="card p-5 border-l-4"
      style={{ borderLeftColor: color }}
    >
      <div className="flex items-center gap-2 mb-2 flex-wrap">
        <h2 className="text-lg font-semibold text-[var(--ink)]">
          Lynsea&apos;s read
        </h2>
        <span
          className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium text-white"
          style={{ background: color }}
        >
          {isTie ? (
            "Leans even"
          ) : (
            <>
              <span className="font-bold">{fav}</span>
              <span className="max-w-[180px] truncate">· {favLabel}</span>
            </>
          )}
        </span>
      </div>
      <p className="text-sm text-[var(--foreground)] leading-relaxed">
        {recommendation.text}
      </p>
      <p className="mt-3 text-[11px] text-[var(--muted)]">
        This is a probabilistic lean from a simulation — a prompt for your own
        reflection, not advice to follow.
      </p>
    </section>
  );
}
