"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { cancelSimulation } from "../lib/api";
import { compositeScores, isHighRisk } from "../lib/simSelectors";
import { BRANCH_COLORS } from "../lib/theme";
import type { SimResult, TimelineEvent } from "../lib/types";
import { useSimStream } from "../lib/useSimStream";
import { BranchPoints } from "./BranchPoints";
import { Header, Icon } from "./Brand";
import { ClarificationSummary } from "./ClarificationSummary";
import { CompositeScores } from "./CompositeScores";
import { CredibilityPanel } from "./CredibilityPanel";
import { EventDetail } from "./EventDetail";
import { MetricCharts } from "./MetricCharts";
import { Personas } from "./Personas";
import { RecommendationCard } from "./RecommendationCard";
import { SafetyBanner } from "./SafetyBanner";
import { SplitTimeline } from "./SplitTimeline";
import { StreamProgress } from "./StreamProgress";
import { WhatIfEntry } from "./WhatIfEntry";

export function ResultsView({
  simId,
  staticResult,
}: {
  simId: string;
  staticResult?: SimResult | null;
}) {
  const sim = useSimStream({ simId, staticResult });
  const [selected, setSelected] = useState<TimelineEvent | null>(null);
  const [cancelling, setCancelling] = useState(false);

  const options = sim.options ?? ["Option A", "Option B"];
  const highRisk = useMemo(() => isHighRisk(sim.metrics), [sim.metrics]);
  const scores = useMemo(
    () => compositeScores(sim.metrics),
    [sim.metrics],
  );

  const hasAnyData =
    sim.personas.length > 0 ||
    sim.events.length > 0 ||
    sim.metrics.length > 0;

  const streaming = !staticResult && !sim.done && !sim.error;
  const eventCount = sim.events.length + sim.metrics.length;

  async function handleCancel() {
    if (cancelling) return;
    setCancelling(true);
    try {
      // Server emits an `error` event on the open stream, surfaced by useSimStream.
      await cancelSimulation(simId);
    } catch {
      // If the cancel request itself fails, the stream may still finish; the
      // error/retry UI below handles surfacing problems.
    } finally {
      setCancelling(false);
    }
  }

  return (
    <>
      <Header active="Observatory" subtitle="Parallel Futures" />

      <main className="flex-1 flex flex-col lg:flex-row relative z-10">
        {/* Dashboard canvas */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Dashboard header */}
          <div className="px-lg py-lg flex flex-col xl:flex-row justify-between items-start xl:items-center gap-md border-b border-surface-variant/50 bg-background/90 backdrop-blur-sm">
            <div className="max-w-2xl">
              <p className="font-caption text-caption text-on-surface-variant uppercase tracking-wider mb-xs">
                Decision Matrix
              </p>
              <h1 className="font-headline text-headline text-on-surface">
                {sim.decision || "Simulating your decision…"}
              </h1>
            </div>
            <div className="flex flex-col items-start xl:items-end gap-sm">
              <div className="flex items-center gap-sm flex-wrap">
                <span className="px-3 py-1 rounded-full bg-surface-container-high border border-outline-variant font-label text-xs flex items-center gap-1 text-on-surface-variant capitalize">
                  <Icon name="timer" className="text-[14px]" />
                  {staticResult?.mode ?? "Quick"}
                </span>
                {streaming ? (
                  <>
                    <span className="px-3 py-1 rounded-full bg-surface-container-high border border-primary/30 font-label text-xs flex items-center gap-2 text-primary">
                      <span className="w-2 h-2 rounded-full bg-primary pulse-dot" />
                      Streaming… {eventCount} events
                    </span>
                    <button
                      type="button"
                      onClick={handleCancel}
                      disabled={cancelling}
                      className="px-3 py-1 rounded-full bg-error/10 border border-error/40 font-label text-xs flex items-center gap-1 text-error hover:bg-error/20 transition-colors disabled:opacity-50 focus-ring"
                    >
                      <Icon name="stop_circle" className="text-[14px]" />
                      {cancelling ? "Cancelling…" : "Cancel"}
                    </button>
                  </>
                ) : (
                  !sim.error && (
                    <span className="px-3 py-1 rounded-full bg-surface-container-high border border-good/30 font-label text-xs flex items-center gap-1 text-good">
                      <Icon name="check_circle" className="text-[14px]" />
                      Complete
                    </span>
                  )
                )}
              </div>
              <div className="flex items-center gap-2 text-on-surface-variant font-caption text-caption">
                <Icon
                  name="verified"
                  className="text-[14px] text-brand-cyan"
                />
                seed-locked ✓ controlled experiment
              </div>
              {/* A/B legend */}
              <div className="flex gap-md mt-sm flex-wrap">
                <LegendChip
                  branch="A"
                  label={`A = ${truncate(options[0])}`}
                />
                <LegendChip
                  branch="B"
                  label={`B = ${truncate(options[1])}`}
                />
              </div>
            </div>
          </div>

          {/* Streaming / progress + clarification + error states */}
          <div className="px-lg pt-md space-y-md">
            {streaming && (
              <StreamProgress status={sim.status} done={sim.done} />
            )}

            {!sim.error && sim.status && (sim.decision || sim.options) && (
              <ClarificationSummary
                decision={sim.decision}
                options={options}
                personas={sim.personas}
                constraints={sim.credibility?.notes}
              />
            )}

            {sim.error && (
              <div
                role="alert"
                className="bg-surface-container border border-error/40 rounded-lg p-5 border-l-2 border-l-error"
              >
                <div className="font-title text-on-surface font-semibold">
                  The simulation stopped
                </div>
                <p className="mt-1 text-sm text-on-surface-variant">
                  {sim.error}
                </p>
                <div className="mt-3 flex gap-2">
                  <button
                    type="button"
                    onClick={sim.retry}
                    className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary-fixed hover:bg-primary-dim focus-ring"
                  >
                    Retry
                  </button>
                  <Link
                    href="/"
                    className="rounded-lg border border-surface-variant px-4 py-2 text-sm font-medium text-on-surface hover:bg-surface-container-high focus-ring"
                  >
                    Start over
                  </Link>
                </div>
              </div>
            )}

            {/* Skeleton-first empty state */}
            {!sim.error && !hasAnyData && !sim.done && (
              <div className="bg-surface-container border border-surface-variant rounded-lg p-8 text-center text-sm text-on-surface-variant">
                Spinning up two parallel futures… expect the first milestones to
                appear shortly.
              </div>
            )}

            {hasAnyData && <SafetyBanner highRisk={highRisk} />}
          </div>

          {/* Split timeline */}
          {sim.events.length > 0 && (
            <SplitTimeline
              events={sim.events}
              options={options}
              branchPoints={sim.branchPoints}
              onSelect={setSelected}
              selectedId={selected?.id ?? null}
            />
          )}

          {/* Branch points + final gaps */}
          {(sim.branchPoints.length > 0 || sim.metrics.length > 0) && (
            <div className="px-lg pb-md">
              <BranchPoints
                branchPoints={sim.branchPoints}
                metrics={sim.metrics}
                options={options}
              />
            </div>
          )}

          {/* Personas */}
          {sim.personas.length > 0 && (
            <div className="px-lg pb-md">
              <Personas
                personas={sim.personas}
                lowConfidenceIds={
                  sim.credibility?.low_confidence_personas ?? []
                }
              />
            </div>
          )}

          {/* Footer recommendation strip */}
          {sim.recommendation && (
            <div className="bg-surface-container-high border-t border-surface-variant p-md relative z-20 mt-auto">
              <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-md">
                <RecommendationCard
                  recommendation={sim.recommendation}
                  options={options}
                  highRisk={highRisk}
                />
                <WhatIfEntry />
              </div>
            </div>
          )}
        </div>

        {/* Right metrics sidebar */}
        {(sim.metrics.length > 0 || sim.credibility) && (
          <div className="w-full lg:w-96 bg-surface-container-low border-t lg:border-t-0 lg:border-l border-surface-variant flex flex-col shrink-0">
            {sim.metrics.length > 0 && (
              <CompositeScores metrics={sim.metrics} />
            )}
            <div className="p-md flex-1 overflow-y-auto flex flex-col gap-md">
              {sim.metrics.length > 0 && (
                <MetricCharts
                  metrics={sim.metrics}
                  branchPoints={sim.branchPoints}
                />
              )}
              {sim.credibility && (
                <div className="mt-auto">
                  <CredibilityPanel card={sim.credibility} />
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Click-for-evidence drawer */}
      <EventDetail
        event={selected}
        personas={sim.personas}
        metrics={sim.metrics}
        options={options}
        onClose={() => setSelected(null)}
      />
    </>
  );
}

function truncate(s: string, n = 22): string {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}

function LegendChip({
  branch,
  label,
}: {
  branch: "A" | "B";
  label: string;
}) {
  const color = BRANCH_COLORS[branch];
  const glow = branch === "A" ? "glow-cyan" : "glow-amber";
  return (
    <div className="flex items-center gap-2 bg-surface-container px-3 py-1 rounded-full border border-surface-variant">
      <span
        className={`w-3 h-3 rounded-full ${glow}`}
        style={{ background: color }}
      />
      <span className="font-label text-xs text-on-surface">{label}</span>
    </div>
  );
}
