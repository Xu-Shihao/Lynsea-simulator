"use client";

import { BRANCH_COLORS } from "../lib/theme";
import type { Recommendation } from "../lib/types";
import { Icon } from "./Brand";

/**
 * Footer recommendation strip content. Probabilistic copy (e.g. "Leans B —
 * around a 60% chance…"), the value rationale, and the guardrail line. For
 * high-risk results the prominent "This is a simulation, not a prophecy"
 * guardrail (FE-24/25) is shown.
 */
export function RecommendationCard({
  recommendation,
  options,
  highRisk = false,
}: {
  recommendation: Recommendation;
  options: [string, string];
  highRisk?: boolean;
}) {
  const fav = recommendation.favored_branch;
  const isTie = fav === "tie";
  const color = isTie ? "var(--primary)" : BRANCH_COLORS[fav];
  const icon = isTie ? "balance" : "trending_up";

  return (
    <div>
      <div className="flex items-center gap-sm mb-xs">
        <Icon name={icon} style={{ color }} />
        <span className="font-label font-bold text-on-surface">
          {isTie ? (
            "Roughly even — both branches score similarly for you."
          ) : (
            <>
              Leans {fav}{" "}
              <span className="text-on-surface-variant font-medium">
                ({fav === "A" ? options[0] : options[1]})
              </span>
            </>
          )}
        </span>
      </div>
      <p className="font-caption text-caption text-on-surface-variant leading-relaxed max-w-2xl">
        {recommendation.text}
      </p>
      {highRisk ? (
        <p className="font-caption text-caption text-warn mt-1 text-[10px] uppercase tracking-wide font-semibold">
          This is a simulation, not a prophecy — one or more paths show a sharp
          dip. Treat it as a “what could happen” warning, not a verdict.
        </p>
      ) : (
        <p className="font-caption text-outline mt-1 text-[10px] uppercase tracking-wide">
          This is a simulation, not a prediction — change any assumption and
          re-run.
        </p>
      )}
    </div>
  );
}
