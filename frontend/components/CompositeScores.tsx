"use client";

import { compositeScores } from "../lib/simSelectors";
import { METRIC_LABELS, type MetricPoint, type ValueWeights } from "../lib/types";
import { Icon } from "./Brand";

/**
 * Composite Scores card for the metrics sidebar: a cyan Branch A number and an
 * amber Branch B number, with the value-weighted note. Scores are the
 * final-month value-weighted composite (0–100).
 */
export function CompositeScores({
  metrics,
  weights,
}: {
  metrics: MetricPoint[];
  weights?: ValueWeights | null;
}) {
  const { A, B, topValue } = compositeScores(metrics, weights);
  if (A == null && B == null) return null;

  return (
    <div className="p-md border-b border-surface-variant">
      <h3 className="font-title text-title text-on-surface mb-sm">
        Composite Scores
      </h3>
      <div className="flex justify-between items-end mb-md">
        <div className="text-center">
          <div className="font-display text-display text-brand-cyan glow-cyan">
            {A ?? "—"}
          </div>
          <div className="font-caption text-caption text-on-surface-variant">
            Branch A
          </div>
        </div>
        <div className="text-center">
          <div className="font-display text-display text-brand-amber glow-amber">
            {B ?? "—"}
          </div>
          <div className="font-caption text-caption text-on-surface-variant">
            Branch B
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 text-xs text-on-surface-variant bg-surface-variant/50 p-2 rounded">
        <Icon name="scale" className="text-[14px]" />
        {topValue
          ? `Value-weighted based on '${METRIC_LABELS[topValue]}' priority`
          : "Equal-weighted across the five life dimensions"}
      </div>
    </div>
  );
}
