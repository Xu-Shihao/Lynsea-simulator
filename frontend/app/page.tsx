"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Header, Icon } from "../components/Brand";
import { createSimulation } from "../lib/api";
import { sampleResult } from "../lib/sampleResult";
import { DEMO_STORAGE_KEY } from "../lib/storage";
import { BRANCH_COLORS } from "../lib/theme";
import {
  METRIC_KEYS,
  METRIC_LABELS,
  type SimMode,
  type ValueWeights,
} from "../lib/types";

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

const DEFAULT_VALUES: ValueWeights = {
  economic: 5,
  career: 5,
  relationship: 5,
  mental: 5,
  autonomy: 5,
};

type PersonStance = "supportive" | "opposed" | "neutral";

interface Influence {
  name: string;
  stance: PersonStance;
  influence: number; // 1..10
}

const STANCE_NEXT: Record<PersonStance, PersonStance> = {
  neutral: "supportive",
  supportive: "opposed",
  opposed: "neutral",
};

const STANCE_META: Record<
  PersonStance,
  { label: string; color: string; bg: string }
> = {
  supportive: { label: "Supports", color: "#34d399", bg: "rgba(52,211,153,0.12)" },
  opposed: { label: "Opposed", color: "#fd6f85", bg: "rgba(200,71,93,0.15)" },
  neutral: { label: "Neutral", color: "#a3aac5", bg: "rgba(109,117,142,0.18)" },
};

export default function InputPage() {
  const router = useRouter();
  const [decision, setDecision] = useState("");
  const [optionA, setOptionA] = useState("");
  const [optionB, setOptionB] = useState("");
  const [influences, setInfluences] = useState<Influence[]>([]);
  const [personInput, setPersonInput] = useState("");
  const [mode, setMode] = useState<SimMode>("quick");
  const [showRefine, setShowRefine] = useState(false);
  const [values, setValues] = useState<ValueWeights>(DEFAULT_VALUES);
  const [useValues, setUseValues] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    decision.trim().length > 0 &&
    optionA.trim().length > 0 &&
    optionB.trim().length > 0 &&
    !submitting;

  function addPerson() {
    const v = personInput.trim();
    if (v && !influences.some((p) => p.name === v)) {
      setInfluences((p) => [
        ...p,
        { name: v, stance: "neutral", influence: 5 },
      ]);
    }
    setPersonInput("");
  }

  function removePerson(name: string) {
    setInfluences((p) => p.filter((x) => x.name !== name));
  }

  function cycleStance(name: string) {
    setInfluences((p) =>
      p.map((x) =>
        x.name === name ? { ...x, stance: STANCE_NEXT[x.stance] } : x,
      ),
    );
  }

  function setInfluence(name: string, value: number) {
    setInfluences((p) =>
      p.map((x) => (x.name === name ? { ...x, influence: value } : x)),
    );
  }

  async function handleSubmit() {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const { sim_id } = await createSimulation({
        decision: decision.trim(),
        options: [optionA.trim(), optionB.trim()],
        affected_people: influences.length
          ? influences.map((p) => p.name)
          : undefined,
        mode,
        values: useValues ? values : undefined,
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
    setInfluences([
      { name: "Partner", stance: "opposed", influence: 8 },
      { name: "Mother", stance: "opposed", influence: 6 },
    ]);
    setShowRefine(true);
  }

  return (
    <>
      <Header active="Console" />
      <main className="flex-grow flex flex-col items-center pt-16 pb-16 px-lg w-full max-w-4xl mx-auto relative z-10">
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
              <Icon
                name="info"
                className="text-outline-variant text-sm"
              />
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

        {/* Refinement panel */}
        <div className="w-full bg-surface-container-low rounded-lg border border-surface-variant overflow-hidden mb-xl">
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
                (optional)
              </span>
            </div>
            <Icon
              name={showRefine ? "expand_less" : "expand_more"}
              className="text-on-surface-variant"
            />
          </button>

          {showRefine && (
            <div className="p-lg grid grid-cols-1 md:grid-cols-2 gap-xl animate-in">
              {/* Social circle influences */}
              <div className="space-y-md">
                <h3 className="font-label text-outline uppercase tracking-wider text-xs mb-sm">
                  Social Circle Influences
                </h3>
                <div className="space-y-sm">
                  {influences.map((p) => (
                    <InfluenceRow
                      key={p.name}
                      person={p}
                      onCycleStance={() => cycleStance(p.name)}
                      onInfluence={(v) => setInfluence(p.name, v)}
                      onRemove={() => removePerson(p.name)}
                    />
                  ))}
                  <div className="flex gap-2">
                    <input
                      value={personInput}
                      onChange={(e) => setPersonInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          addPerson();
                        }
                      }}
                      placeholder="e.g. Partner, Mother, Manager"
                      className="flex-1 bg-surface-container border border-surface-variant rounded px-3 py-2 text-sm text-on-surface focus-ring placeholder:text-outline-variant"
                    />
                    <button
                      type="button"
                      onClick={addPerson}
                      className="py-2 px-3 border border-dashed border-outline-variant rounded text-on-surface-variant font-label text-caption hover:text-primary hover:border-primary/50 transition-colors flex items-center gap-xs"
                    >
                      <Icon name="add_circle" className="text-sm" /> Add
                    </button>
                  </div>
                  <p className="font-caption text-caption text-outline">
                    Tap a stance to cycle Neutral → Supports → Opposed. Slide to
                    set how much sway each person holds.
                  </p>
                </div>
              </div>

              {/* Value sliders */}
              <div className="space-y-md">
                <div className="flex items-center justify-between mb-sm">
                  <h3 className="font-label text-outline uppercase tracking-wider text-xs">
                    What matters most to you
                  </h3>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <span className="font-caption text-caption text-outline">
                      {useValues ? "Custom" : "Auto"}
                    </span>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={useValues}
                      onClick={() => setUseValues((v) => !v)}
                      className={`w-9 h-5 rounded-full relative transition-colors border ${
                        useValues
                          ? "bg-primary/30 border-primary/50"
                          : "bg-surface-container-high border-surface-variant"
                      }`}
                    >
                      <span
                        className={`absolute top-0.5 w-3.5 h-3.5 rounded-full transition-transform ${
                          useValues
                            ? "translate-x-4 bg-primary"
                            : "translate-x-0.5 bg-outline"
                        }`}
                      />
                    </button>
                  </label>
                </div>
                <div
                  className={`space-y-3 ${useValues ? "" : "opacity-50 pointer-events-none"}`}
                >
                  {METRIC_KEYS.map((key) => (
                    <div key={key}>
                      <div className="flex justify-between mb-1">
                        <span className="font-caption text-caption text-on-surface-variant">
                          {METRIC_LABELS[key]}
                        </span>
                        <span className="font-data-numeric text-data-numeric text-primary text-xs">
                          {values[key]}/10
                        </span>
                      </div>
                      <input
                        type="range"
                        min={0}
                        max={10}
                        value={values[key]}
                        onChange={(e) =>
                          setValues((v) => ({
                            ...v,
                            [key]: Number(e.target.value),
                          }))
                        }
                        className="lynsea-range w-full"
                        aria-label={`${METRIC_LABELS[key]} importance`}
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {error && (
          <div
            role="alert"
            className="w-full mb-lg rounded-lg border border-error/30 bg-error/10 px-4 py-3 text-sm text-error"
          >
            {error}
          </div>
        )}

        {/* CTA + demo */}
        <div className="flex flex-col sm:flex-row items-center gap-md">
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="bg-primary hover:bg-primary-dim text-on-primary-fixed font-title text-title font-semibold py-md px-xl rounded-lg shadow-[0_0_20px_rgba(159,146,255,0.4)] hover:shadow-[0_0_30px_rgba(159,146,255,0.6)] transition-all flex items-center gap-md group disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none focus-ring"
          >
            {submitting ? "Starting simulation…" : "Run simulation"}
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
          No backend? “Load demo” renders a full sample result offline.
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

function InfluenceRow({
  person,
  onCycleStance,
  onInfluence,
  onRemove,
}: {
  person: Influence;
  onCycleStance: () => void;
  onInfluence: (v: number) => void;
  onRemove: () => void;
}) {
  const meta = STANCE_META[person.stance];
  return (
    <div className="flex items-center justify-between bg-surface-container p-sm rounded border border-surface-variant gap-2">
      <div className="flex items-center gap-md min-w-0">
        <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center border border-primary/30 shrink-0">
          <Icon name="person" className="text-primary text-sm" fill />
        </div>
        <div className="min-w-0">
          <span className="block font-body text-sm text-on-surface truncate">
            {person.name}
          </span>
          {/* Influence indicator: 5 dots, filled by influence level. */}
          <div className="flex gap-1 mt-1 items-center">
            {[0, 1, 2, 3, 4].map((i) => (
              <span
                key={i}
                className="w-1.5 h-1.5 rounded-full"
                style={{
                  background:
                    i < Math.round(person.influence / 2)
                      ? "#9f92ff"
                      : "#181f31",
                }}
              />
            ))}
            <span className="font-caption text-outline text-[10px] ml-1 leading-none">
              {person.influence}
            </span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <input
          type="range"
          min={1}
          max={10}
          value={person.influence}
          onChange={(e) => onInfluence(Number(e.target.value))}
          className="lynsea-range w-16 hidden sm:block"
          aria-label={`${person.name} influence`}
        />
        <button
          type="button"
          onClick={onCycleStance}
          className="font-label text-caption px-2 py-1 rounded transition-colors"
          style={{ color: meta.color, background: meta.bg }}
          aria-label={`${person.name} stance: ${meta.label}. Click to change.`}
        >
          {meta.label}
        </button>
        <button
          type="button"
          onClick={onRemove}
          className="text-outline hover:text-error transition-colors"
          aria-label={`Remove ${person.name}`}
        >
          <Icon name="close" className="text-sm" />
        </button>
      </div>
    </div>
  );
}
