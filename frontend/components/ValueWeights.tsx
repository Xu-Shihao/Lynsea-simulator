"use client";

import { favoredFromComposite } from "../lib/simSelectors";
import { BRANCH_COLORS } from "../lib/theme";
import type {
  Dimension,
  MetricPoint,
  ValueWeights as ValueWeightsMap,
} from "../lib/types";
import { Icon } from "./Brand";

/**
 * Results-page value sliders (M-d). One slider per generated dimension
 * (0–10, default 5). Changing weights live-recomputes the polarity-aware
 * composite + which branch the recommendation favors — all client-side, no
 * re-run. Sliders only exist once dimensions have been generated.
 */
export function ValueWeights({
  dimensions,
  metrics,
  weights,
  onChange,
  onReset,
}: {
  dimensions: Dimension[];
  metrics: MetricPoint[];
  weights: ValueWeightsMap;
  onChange: (dimId: string, value: number) => void;
  onReset: () => void;
}) {
  if (!dimensions.length) return null;

  const { favored, a, b, gap } = favoredFromComposite(
    metrics,
    dimensions,
    weights,
  );
  const customized = dimensions.some((d) => (weights[d.id] ?? 5) !== 5);

  return (
    <div className="p-md border-b border-surface-variant">
      <div className="flex items-center justify-between mb-sm">
        <h3 className="font-title text-title text-on-surface">
          What matters to you
        </h3>
        {customized && (
          <button
            type="button"
            onClick={onReset}
            className="text-[11px] text-primary hover:underline focus-ring rounded"
          >
            Reset
          </button>
        )}
      </div>
      <p className="font-caption text-caption text-on-surface-variant mb-md">
        Re-weight the dimensions to see which path fits your priorities. The
        composite scores update instantly.
      </p>

      <div className="space-y-3">
        {dimensions.map((d) => {
          const value = weights[d.id] ?? 5;
          return (
            <div key={d.id}>
              <div className="flex justify-between mb-1 gap-2">
                <span
                  className="font-caption text-caption text-on-surface-variant truncate"
                  title={d.description}
                >
                  {d.label}
                </span>
                <span className="font-data-numeric text-data-numeric text-primary text-xs shrink-0">
                  {value}/10
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={10}
                value={value}
                onChange={(e) => onChange(d.id, Number(e.target.value))}
                className="lynsea-range w-full"
                aria-label={`${d.label} importance`}
              />
            </div>
          );
        })}
      </div>

      {a != null && b != null && (
        <div className="mt-md flex items-center gap-2 rounded-lg bg-surface-variant/50 px-3 py-2 text-xs">
          <Icon name="balance" className="text-[14px] text-on-surface-variant" />
          {favored === "tie" ? (
            <span className="text-on-surface-variant">
              With these priorities, the two paths score about even (
              {a} vs {b}).
            </span>
          ) : (
            <span className="text-on-surface-variant">
              With these priorities, Branch{" "}
              <span
                className="font-semibold"
                style={{ color: BRANCH_COLORS[favored] }}
              >
                {favored}
              </span>{" "}
              leads by ~{gap} points.
            </span>
          )}
        </div>
      )}
    </div>
  );
}
