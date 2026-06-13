"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Header, Logo } from "../components/Brand";
import { createSimulation } from "../lib/api";
import { sampleResult } from "../lib/sampleResult";
import { DEMO_STORAGE_KEY } from "../lib/storage";
import {
  METRIC_KEYS,
  METRIC_LABELS,
  type SimMode,
  type ValueWeights,
} from "../lib/types";

const MODES: { id: SimMode; label: string; blurb: string }[] = [
  { id: "quick", label: "Quick", blurb: "Fast sketch · ~6 months" },
  { id: "medium", label: "Medium", blurb: "More detail · deeper personas" },
  { id: "heavy", label: "Heavy", blurb: "Most thorough · slowest" },
];

const DEFAULT_VALUES: ValueWeights = {
  economic: 5,
  career: 5,
  relationship: 5,
  mental: 5,
  autonomy: 5,
};

export default function InputPage() {
  const router = useRouter();
  const [decision, setDecision] = useState("");
  const [optionA, setOptionA] = useState("");
  const [optionB, setOptionB] = useState("");
  const [people, setPeople] = useState<string[]>([]);
  const [personInput, setPersonInput] = useState("");
  const [mode, setMode] = useState<SimMode>("quick");
  const [showValues, setShowValues] = useState(false);
  const [values, setValues] = useState<ValueWeights>(DEFAULT_VALUES);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    decision.trim().length > 0 &&
    optionA.trim().length > 0 &&
    optionB.trim().length > 0 &&
    !submitting;

  function addPerson() {
    const v = personInput.trim();
    if (v && !people.includes(v)) {
      setPeople((p) => [...p, v]);
    }
    setPersonInput("");
  }

  function removePerson(name: string) {
    setPeople((p) => p.filter((x) => x !== name));
  }

  async function handleSubmit() {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const { sim_id } = await createSimulation({
        decision: decision.trim(),
        options: [optionA.trim(), optionB.trim()],
        affected_people: people.length ? people : undefined,
        mode,
        values: showValues ? values : undefined,
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
      "Should I take the higher-paying but higher-stress job, or stay where I am?",
    );
    setOptionA("Take the new job");
    setOptionB("Stay at my current job");
    setPeople(["my partner", "my mother"]);
  }

  return (
    <>
      <Header />
      <main className="mx-auto w-full max-w-[860px] px-5 py-10 flex-1">
        {/* Hero */}
        <section className="text-center mb-9">
          <div className="inline-flex items-center justify-center mb-4">
            <Logo className="w-12 h-12" />
          </div>
          <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-[var(--ink)]">
            Two futures. One decision.
          </h1>
          <p className="mt-3 text-[var(--muted)] max-w-xl mx-auto leading-relaxed">
            Describe one hard choice with exactly two options. Lynsea simulates
            two parallel futures that differ{" "}
            <span className="text-[var(--ink)] font-medium">only</span> by your
            decision — a controlled experiment, framed as probabilities, not
            prophecy.
          </p>
        </section>

        <div className="card p-6 sm:p-7">
          {/* Decision */}
          <label
            htmlFor="decision"
            className="block text-sm font-medium text-[var(--ink)] mb-1.5"
          >
            The decision you&apos;re facing
          </label>
          <textarea
            id="decision"
            value={decision}
            onChange={(e) => setDecision(e.target.value)}
            placeholder="e.g. Should I take the higher-paying but higher-stress job, or stay where I am?"
            rows={3}
            className="w-full resize-none rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3.5 py-3 text-[15px] focus-ring placeholder:text-[var(--muted)]/70"
          />
          <div className="mt-1.5 text-right">
            <button
              type="button"
              onClick={prefillExample}
              className="text-xs text-[var(--accent)] hover:underline focus-ring rounded"
            >
              Fill an example
            </button>
          </div>

          {/* Two options */}
          <div className="mt-5 grid sm:grid-cols-2 gap-4">
            <OptionField
              branch="A"
              value={optionA}
              onChange={setOptionA}
              placeholder="Take the new job"
            />
            <OptionField
              branch="B"
              value={optionB}
              onChange={setOptionB}
              placeholder="Stay at my current job"
            />
          </div>
          <p className="mt-2 text-xs text-[var(--muted)]">
            Exactly two options. Branch{" "}
            <span className="branch-a-text font-medium">A</span> compares
            against branch{" "}
            <span className="branch-b-text font-medium">B</span> on the same
            timeline.
          </p>

          {/* Affected people */}
          <div className="mt-6">
            <label
              htmlFor="person"
              className="block text-sm font-medium text-[var(--ink)] mb-1.5"
            >
              People affected{" "}
              <span className="text-[var(--muted)] font-normal">
                (optional)
              </span>
            </label>
            <div className="flex flex-wrap gap-2 mb-2">
              {people.map((name) => (
                <span key={name} className="chip bg-[var(--surface-2)]">
                  {name}
                  <button
                    type="button"
                    aria-label={`Remove ${name}`}
                    onClick={() => removePerson(name)}
                    className="text-[var(--muted)] hover:text-[var(--bad)] focus-ring rounded"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                id="person"
                value={personInput}
                onChange={(e) => setPersonInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addPerson();
                  }
                }}
                placeholder="e.g. my partner"
                className="flex-1 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3.5 py-2.5 text-sm focus-ring placeholder:text-[var(--muted)]/70"
              />
              <button
                type="button"
                onClick={addPerson}
                className="rounded-xl border border-[var(--border)] bg-[var(--surface-2)] px-4 text-sm font-medium hover:bg-[var(--border)] focus-ring"
              >
                Add
              </button>
            </div>
          </div>

          {/* Mode */}
          <div className="mt-6">
            <span className="block text-sm font-medium text-[var(--ink)] mb-2">
              Depth
            </span>
            <div className="grid grid-cols-3 gap-2">
              {MODES.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setMode(m.id)}
                  aria-pressed={mode === m.id}
                  className={`rounded-xl border px-3 py-2.5 text-left transition focus-ring ${
                    mode === m.id
                      ? "border-[var(--accent)] bg-[var(--accent)]/5 ring-1 ring-[var(--accent)]/30"
                      : "border-[var(--border)] hover:bg-[var(--surface-2)]"
                  }`}
                >
                  <div className="text-sm font-medium text-[var(--ink)]">
                    {m.label}
                  </div>
                  <div className="text-[11px] text-[var(--muted)] mt-0.5">
                    {m.blurb}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Value sliders */}
          <div className="mt-6">
            <button
              type="button"
              onClick={() => setShowValues((s) => !s)}
              className="flex items-center gap-2 text-sm font-medium text-[var(--ink)] focus-ring rounded"
            >
              <span
                className={`transition-transform ${showValues ? "rotate-90" : ""}`}
                aria-hidden
              >
                ▸
              </span>
              What matters most to you{" "}
              <span className="text-[var(--muted)] font-normal">
                (optional)
              </span>
            </button>
            {showValues && (
              <div className="mt-3 grid sm:grid-cols-2 gap-x-6 gap-y-3 animate-in">
                {METRIC_KEYS.map((key) => (
                  <div key={key}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-[var(--ink)]">
                        {METRIC_LABELS[key]}
                      </span>
                      <span className="text-[var(--muted)] tabular-nums">
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
            )}
          </div>

          {error && (
            <div
              role="alert"
              className="mt-5 rounded-xl border border-[var(--bad)]/30 bg-[var(--bad)]/5 px-3.5 py-3 text-sm text-[var(--bad)]"
            >
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="mt-7 flex flex-col sm:flex-row gap-3">
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!canSubmit}
              className="flex-1 rounded-xl bg-[var(--accent)] px-5 py-3 text-white font-medium shadow-sm transition hover:brightness-105 disabled:opacity-50 disabled:cursor-not-allowed focus-ring"
            >
              {submitting ? "Starting simulation…" : "Simulate both futures"}
            </button>
            <button
              type="button"
              onClick={loadDemo}
              className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-5 py-3 font-medium hover:bg-[var(--surface-2)] focus-ring"
            >
              Load demo
            </button>
          </div>
          <p className="mt-3 text-center text-xs text-[var(--muted)]">
            No backend? &ldquo;Load demo&rdquo; renders a full sample result
            offline.
          </p>
        </div>
      </main>
      <footer className="text-center text-xs text-[var(--muted)] py-6">
        Lynsea simulations are illustrative, not predictive. Always trust your
        own judgment.
      </footer>
    </>
  );
}

function OptionField({
  branch,
  value,
  onChange,
  placeholder,
}: {
  branch: "A" | "B";
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  const color = branch === "A" ? "var(--branch-a)" : "var(--branch-b)";
  return (
    <div>
      <label
        className="flex items-center gap-2 text-sm font-medium mb-1.5"
        style={{ color }}
      >
        <span
          className="inline-flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-bold text-white"
          style={{ background: color }}
        >
          {branch}
        </span>
        Option {branch}
      </label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-xl border bg-[var(--surface)] px-3.5 py-2.5 text-sm focus-ring placeholder:text-[var(--muted)]/70"
        style={{ borderColor: `${color}55` }}
      />
    </div>
  );
}
