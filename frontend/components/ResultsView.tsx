"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { isHighRisk } from "../lib/simSelectors";
import type { SimResult, TimelineEvent } from "../lib/types";
import { useSimStream } from "../lib/useSimStream";
import { BranchPoints } from "./BranchPoints";
import { Header } from "./Brand";
import { ClarificationSummary } from "./ClarificationSummary";
import { CredibilityPanel } from "./CredibilityPanel";
import { EventDetail } from "./EventDetail";
import { MetricCharts } from "./MetricCharts";
import { Personas } from "./Personas";
import { RecommendationCard } from "./RecommendationCard";
import { SafetyBanner } from "./SafetyBanner";
import { SmallMultiples } from "./SmallMultiples";
import { StreamProgress } from "./StreamProgress";

export function ResultsView({
  simId,
  staticResult,
}: {
  simId: string;
  staticResult?: SimResult | null;
}) {
  const sim = useSimStream({ simId, staticResult });
  const [selected, setSelected] = useState<TimelineEvent | null>(null);

  const options = sim.options ?? ["Option A", "Option B"];
  const highRisk = useMemo(() => isHighRisk(sim.metrics), [sim.metrics]);

  const hasAnyData =
    sim.personas.length > 0 ||
    sim.events.length > 0 ||
    sim.metrics.length > 0;

  return (
    <>
      <Header subtitle="Simulation results" />
      <main className="mx-auto w-full max-w-[1180px] px-4 sm:px-5 py-6 flex-1 space-y-5">
        {/* Decision summary */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="text-xs text-[var(--muted)] mb-1">
              Your decision
            </div>
            <h1 className="text-xl sm:text-2xl font-semibold tracking-tight text-[var(--ink)] max-w-3xl">
              {sim.decision || "Simulating your decision…"}
            </h1>
            {sim.options && (
              <div className="mt-2 flex items-center gap-3 text-sm flex-wrap">
                <span className="flex items-center gap-1.5">
                  <Dot branch="A" />
                  <span className="branch-a-text font-medium">A</span>
                  <span className="text-[var(--foreground)]">{options[0]}</span>
                </span>
                <span className="text-[var(--muted)]">vs</span>
                <span className="flex items-center gap-1.5">
                  <Dot branch="B" />
                  <span className="branch-b-text font-medium">B</span>
                  <span className="text-[var(--foreground)]">{options[1]}</span>
                </span>
              </div>
            )}
          </div>
          <Link
            href="/"
            className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3.5 py-2 text-sm font-medium hover:bg-[var(--surface-2)] focus-ring"
          >
            New simulation
          </Link>
        </div>

        {/* Live progress while streaming */}
        {!staticResult && (
          <StreamProgress status={sim.status} done={sim.done} />
        )}

        {/* Clarification summary — what Lynsea understood, for confirmation.
            Shown once the clarify phase has reported the decision/options. */}
        {!sim.error && sim.status && (sim.decision || sim.options) && (
          <ClarificationSummary
            decision={sim.decision}
            options={options}
            personas={sim.personas}
            constraints={sim.credibility?.notes}
          />
        )}

        {/* Error + retry */}
        {sim.error && (
          <div
            role="alert"
            className="card p-5 border-l-4 border-l-[var(--bad)]"
          >
            <div className="font-semibold text-[var(--ink)]">
              The simulation hit a problem
            </div>
            <p className="mt-1 text-sm text-[var(--muted)]">{sim.error}</p>
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                onClick={sim.retry}
                className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white hover:brightness-105 focus-ring"
              >
                Retry
              </button>
              <Link
                href="/"
                className="rounded-lg border border-[var(--border)] px-4 py-2 text-sm font-medium hover:bg-[var(--surface-2)] focus-ring"
              >
                Start over
              </Link>
            </div>
          </div>
        )}

        {/* Empty state while waiting for first events */}
        {!sim.error && !hasAnyData && !sim.done && (
          <div className="card p-8 text-center text-sm text-[var(--muted)]">
            Spinning up two parallel futures… expect the first milestones to
            appear shortly.
          </div>
        )}

        {/* Safety banner */}
        {hasAnyData && <SafetyBanner highRisk={highRisk} />}

        {/* Recommendation */}
        {sim.recommendation && (
          <RecommendationCard
            recommendation={sim.recommendation}
            options={options}
          />
        )}

        {/* Small multiples timeline — the controlled-experiment view */}
        {sim.events.length > 0 && (
          <SmallMultiples
            events={sim.events}
            options={options}
            branchPoints={sim.branchPoints}
            onSelect={setSelected}
            selectedId={selected?.id ?? null}
          />
        )}

        {/* Metric curves */}
        {sim.metrics.length > 0 && (
          <MetricCharts
            metrics={sim.metrics}
            options={options}
            branchPoints={sim.branchPoints}
          />
        )}

        {/* Branch points + final gaps */}
        {(sim.branchPoints.length > 0 || sim.metrics.length > 0) && (
          <BranchPoints
            branchPoints={sim.branchPoints}
            metrics={sim.metrics}
            options={options}
          />
        )}

        {/* Two-column lower section */}
        <div className="grid lg:grid-cols-2 gap-5">
          {sim.personas.length > 0 && (
            <Personas
              personas={sim.personas}
              lowConfidenceIds={
                sim.credibility?.low_confidence_personas ?? []
              }
            />
          )}
          {sim.credibility && <CredibilityPanel card={sim.credibility} />}
        </div>
      </main>

      <footer className="text-center text-xs text-[var(--muted)] py-6">
        Lynsea simulations are illustrative, not predictive. Always trust your
        own judgment.
      </footer>

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

function Dot({ branch }: { branch: "A" | "B" }) {
  const color = branch === "A" ? "var(--branch-a)" : "var(--branch-b)";
  return (
    <span
      className="inline-block h-2.5 w-2.5 rounded-full"
      style={{ background: color }}
    />
  );
}
