"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Header, Icon } from "../components/Brand";
import {
  RefinePanel,
  type RefinePerson,
  type RefineResult,
} from "../components/RefinePanel";
import { createSimulation } from "../lib/api";
import { sampleResult } from "../lib/sampleResult";
import { DEMO_STORAGE_KEY } from "../lib/storage";
import { BRANCH_COLORS } from "../lib/theme";
import { type SimMode } from "../lib/types";

const MODES: { id: SimMode; label: string }[] = [
  { id: "quick", label: "Quick (≤10 min)" },
  { id: "medium", label: "Medium (≤1 hr)" },
  { id: "heavy", label: "Heavy" },
];

const MODE_BLURB: Record<SimMode, string> = {
  quick:
    "Quick mode prioritizes immediate logical branching over deep narrative depth.",
  medium: "Medium mode adds deeper personas and richer per-month detail.",
  heavy: "Heavy mode is the most thorough simulation — and the slowest.",
};

// On the hosted GitHub Pages build there is no backend (static export only), so
// the input runs the bundled sample result instead of calling the live API.
// This is inlined at build time via NEXT_PUBLIC_STATIC_DEMO=1.
const STATIC_DEMO = process.env.NEXT_PUBLIC_STATIC_DEMO === "1";

export default function InputPage() {
  const router = useRouter();
  const [decision, setDecision] = useState("");
  const [optionA, setOptionA] = useState("");
  const [optionB, setOptionB] = useState("");
  // People affected, sourced from the refine panel selections.
  const [people, setPeople] = useState<RefinePerson[]>([]);
  const [mode, setMode] = useState<SimMode>("quick");
  const [showRefine, setShowRefine] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    decision.trim().length > 0 &&
    optionA.trim().length > 0 &&
    optionB.trim().length > 0 &&
    !submitting;

  function applyRefine(result: RefineResult) {
    if (result.optionA) setOptionA(result.optionA);
    if (result.optionB) setOptionB(result.optionB);
    if (result.people) setPeople(result.people);
  }

  async function handleSubmit() {
    // No backend on the hosted static demo — render the bundled sample instead.
    if (STATIC_DEMO) {
      loadDemo();
      return;
    }
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    // Confirmed (selected) affected people feed the simulate request.
    const chosen = people.filter((p) => p.selected).map((p) => p.name);
    try {
      const { sim_id } = await createSimulation({
        decision: decision.trim(),
        options: [optionA.trim(), optionB.trim()],
        affected_people: chosen.length ? chosen : undefined,
        mode,
        // Value weights now live on the results page (dimensions are generated
        // server-side), so the request omits them — defaulted neutral there.
      });
      router.push(`/sim/${sim_id}`);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Could not reach the simulator. Try the demo instead.",
      );
      setSubmitting(false);
    }
  }

  function loadDemo() {
    try {
      sessionStorage.setItem(DEMO_STORAGE_KEY, JSON.stringify(sampleResult));
    } catch {
      // ignore storage failures — the results page falls back to the fixture.
    }
    router.push(`/sim/${sampleResult.sim_id}?demo=1`);
  }

  function prefillExample() {
    setDecision(
      "Should I quit my stable backend job to join an early-stage startup?",
    );
    setOptionA("Stay at my current job");
    setOptionB("Join the early-stage startup");
    setPeople([
      { name: "Partner", role: "partner", stance: "opposed", selected: true },
      { name: "Mother", role: "parent", stance: "opposed", selected: true },
    ]);
    setShowRefine(true);
  }

  return (
    <>
      <Header active="Console" />
      <main className="flex-grow flex flex-col items-center pt-16 pb-16 px-lg w-full max-w-4xl mx-auto relative z-10">
        {/* Hosted static-demo notice: no live backend on GitHub Pages. */}
        {STATIC_DEMO && (
          <div className="w-full mb-lg rounded-lg border border-primary/30 bg-primary/10 px-4 py-3 flex items-start gap-3">
            <Icon name="info" className="text-primary mt-0.5" />
            <p className="font-caption text-caption text-on-surface-variant">
              Hosted static demo — the simulation backend isn’t connected here,
              so this page renders a full <strong>sample result</strong>. Run
              Lynsea locally (see the{" "}
              <a
                href="https://github.com/Xu-Shihao/Lynsea-simulator#setup--run-both-servers-together"
                target="_blank"
                rel="noreferrer"
                className="text-primary hover:underline"
              >
                README
              </a>
              ) for live simulations against your own decisions.
            </p>
          </div>
        )}

        {/* Hero */}
        <div className="text-center mb-12 mt-10">
          <h1 className="font-display text-display text-on-surface mb-sm tracking-tight">
            See your futures before you choose.
          </h1>
          <p className="font-body text-body text-on-surface-variant max-w-2xl mx-auto">
            Describe a complex life decision. Lynsea will simulate probabilistic
            parallel futures, mapping out consequences to help you navigate
            uncertainty with clarity.
          </p>
        </div>

        {/* Decision input with glow border + left primary accent bar */}
        <div className="w-full bg-surface-container rounded-xl border border-surface-variant glow-border transition-all duration-300 relative overflow-hidden mb-lg shadow-2xl">
          <div className="absolute top-0 left-0 w-1 h-full bg-primary" />
          <textarea
            value={decision}
            onChange={(e) => setDecision(e.target.value)}
            className="w-full h-40 bg-transparent border-none text-on-surface font-body text-body p-lg resize-none focus:ring-0 focus:outline-none placeholder:text-outline-variant"
            placeholder="What are you deciding? What do you want to predict? Who or what will be affected?"
          />
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-sm px-lg py-md border-t border-surface-variant bg-surface-container-low">
            <div className="flex items-center gap-md">
              <span className="font-label text-on-surface-variant uppercase tracking-wider text-[11px]">
                Mode
              </span>
              <div className="flex bg-surface-container-high rounded-full p-1 border border-outline-variant/30">
                {MODES.map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => setMode(m.id)}
                    aria-pressed={mode === m.id}
                    className={`px-4 py-1.5 rounded-full font-label text-xs transition-all ${
                      mode === m.id
                        ? "bg-primary/20 text-primary border border-primary/30"
                        : "text-on-surface-variant hover:text-on-surface"
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-sm">
              <Icon name="info" className="text-outline-variant text-sm" />
              <span className="font-caption text-caption text-outline">
                {MODE_BLURB[mode]}
              </span>
            </div>
          </div>
        </div>

        {/* Example prefill */}
        <div className="w-full -mt-2 mb-md text-right">
          <button
            type="button"
            onClick={prefillExample}
            className="text-xs text-primary hover:underline focus-ring rounded"
          >
            Fill an example
          </button>
        </div>

        {/* Two options — branch A / branch B (frozen 2-option contract) */}
        <div className="w-full grid sm:grid-cols-2 gap-md mb-lg">
          <OptionField
            branch="A"
            label="Option A — Branch A"
            value={optionA}
            onChange={setOptionA}
            placeholder="e.g. Stay at my current job"
          />
          <OptionField
            branch="B"
            label="Option B — Branch B"
            value={optionB}
            onChange={setOptionB}
            placeholder="e.g. Join the early-stage startup"
          />
        </div>

        {/* Dynamic "Refine your world" panel (LLM-generated clarification) */}
        <div className="w-full bg-surface-container-low rounded-lg border border-surface-variant overflow-hidden mb-md">
          <button
            type="button"
            onClick={() => setShowRefine((s) => !s)}
            aria-expanded={showRefine}
            className="w-full px-lg py-md flex items-center justify-between text-left hover:bg-surface-container transition-colors border-b border-surface-variant"
          >
            <div className="flex items-center gap-sm">
              <Icon name="tune" className="text-primary" />
              <span className="font-title text-base text-on-surface">
                Refine your world
              </span>
              <span className="font-caption text-caption text-outline ml-2">
                (optional — Lynsea suggests the details)
              </span>
            </div>
            <Icon
              name={showRefine ? "expand_less" : "expand_more"}
              className="text-on-surface-variant"
            />
          </button>

          {showRefine && (
            <RefinePanel decision={decision} onApply={applyRefine} />
          )}
        </div>

        {/* Selected people summary (when applied via refine) */}
        {people.some((p) => p.selected) && (
          <div className="w-full -mt-1 mb-lg flex flex-wrap items-center gap-2">
            <span className="font-caption text-caption text-outline">
              Modeling:
            </span>
            {people
              .filter((p) => p.selected)
              .map((p) => (
                <span
                  key={p.name}
                  className="inline-flex items-center gap-1 rounded-full bg-surface-container border border-surface-variant px-2.5 py-1 text-xs text-on-surface"
                >
                  <Icon name="person" className="text-sm text-primary" fill />
                  {p.name}
                </span>
              ))}
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="w-full mb-lg rounded-lg border border-error/30 bg-error/10 px-4 py-3 text-sm text-error"
          >
            {error}
          </div>
        )}

        {/* CTA + demo (skip / run now path) */}
        <div className="flex flex-col sm:flex-row items-center gap-md">
          <button
            type="button"
            onClick={handleSubmit}
            disabled={STATIC_DEMO ? false : !canSubmit}
            className="bg-primary hover:bg-primary-dim text-on-primary-fixed font-title text-title font-semibold py-md px-xl rounded-lg shadow-[0_0_20px_rgba(159,146,255,0.4)] hover:shadow-[0_0_30px_rgba(159,146,255,0.6)] transition-all flex items-center gap-md group disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none focus-ring"
          >
            {STATIC_DEMO
              ? "Explore sample result"
              : submitting
                ? "Starting simulation…"
                : "Run simulation"}
            <Icon
              name="arrow_forward"
              className="group-hover:translate-x-1 transition-transform"
            />
          </button>
          <button
            type="button"
            onClick={loadDemo}
            className="rounded-lg border border-surface-variant bg-surface-container px-6 py-md font-label text-on-surface hover:bg-surface-container-high transition-colors focus-ring"
          >
            Load demo
          </button>
        </div>
        <p className="mt-md text-center font-caption text-caption text-outline">
          Refining is optional — fill the two options and run now, or let Lynsea
          suggest the details. No backend? “Load demo” renders a full sample
          result offline.
        </p>
      </main>

      {/* Footer */}
      <footer className="w-full py-md px-lg flex flex-col md:flex-row justify-between items-center gap-sm bg-surface-dim border-t border-surface-variant relative z-10 mt-auto">
        <div className="font-caption text-caption text-outline">
          © 2026 Lynsea. Simulations are probabilistic models, not deterministic
          predictions.
        </div>
        <div className="flex gap-lg">
          <span className="font-caption text-caption text-on-surface-variant">
            Terms of Service
          </span>
          <span className="font-caption text-caption text-on-surface-variant">
            Privacy Policy
          </span>
          <span className="font-caption text-caption text-on-surface-variant">
            Methodology
          </span>
        </div>
      </footer>
    </>
  );
}

function OptionField({
  branch,
  label,
  value,
  onChange,
  placeholder,
}: {
  branch: "A" | "B";
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  const color = BRANCH_COLORS[branch];
  return (
    <div className="bg-surface-container border border-surface-variant rounded-lg p-md">
      <label
        className="flex items-center gap-2 font-label text-label mb-2"
        style={{ color }}
      >
        <span
          className="inline-flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-bold text-surface"
          style={{ background: color }}
        >
          {branch}
        </span>
        {label}
      </label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded bg-surface-container-low border px-3 py-2 text-sm text-on-surface focus-ring placeholder:text-outline-variant"
        style={{ borderColor: `${color}55` }}
      />
    </div>
  );
}
