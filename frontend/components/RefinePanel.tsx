"use client";

import { useState } from "react";
import { clarify } from "../lib/api";
import type { ClarificationPlan } from "../lib/types";
import { Icon } from "./Brand";

export type RefineStance = "supportive" | "opposed" | "neutral";

export interface RefinePerson {
  name: string;
  role: string;
  stance: RefineStance;
  selected: boolean;
}

/** What the input page consumes when the user applies a refinement. */
export interface RefineResult {
  optionA?: string;
  optionB?: string;
  people: RefinePerson[];
}

const STANCE_NEXT: Record<RefineStance, RefineStance> = {
  neutral: "supportive",
  supportive: "opposed",
  opposed: "neutral",
};

const STANCE_META: Record<RefineStance, { label: string; color: string; bg: string }> = {
  supportive: { label: "Supports", color: "#34d399", bg: "rgba(52,211,153,0.12)" },
  opposed: { label: "Opposed", color: "#fd6f85", bg: "rgba(200,71,93,0.15)" },
  neutral: { label: "Neutral", color: "#a3aac5", bg: "rgba(109,117,142,0.18)" },
};

function normalizeStance(raw: string): RefineStance {
  const s = (raw ?? "").toLowerCase();
  if (s.includes("support") || s.includes("favor") || s.includes("for")) return "supportive";
  if (s.includes("oppos") || s.includes("against") || s.includes("resist")) return "opposed";
  return "neutral";
}

/**
 * Dynamic "Refine your world" panel (FE-02 / S1). After a decision is typed,
 * "Refine" calls POST /api/clarify and renders the LLM-generated suggested
 * options, affected people (selectable stance chips), key factors, value
 * prompts, constraints, and followup questions — all editable. A free-text
 * note re-calls clarify(decision, prior, note) for iterative refinement.
 * Confirmed selections are applied back to the simulate request via onApply.
 */
export function RefinePanel({
  decision,
  onApply,
}: {
  decision: string;
  onApply: (result: RefineResult) => void;
}) {
  const [plan, setPlan] = useState<ClarificationPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Editable, local copies of the generated plan.
  const [people, setPeople] = useState<RefinePerson[]>([]);
  const [keyFactors, setKeyFactors] = useState<string[]>([]);
  const [constraints, setConstraints] = useState<string[]>([]);
  const [followups, setFollowups] = useState<string[]>([]);
  const [note, setNote] = useState("");

  function hydrate(p: ClarificationPlan) {
    setPlan(p);
    setPeople(
      p.affected_people.map((ap) => ({
        name: ap.name,
        role: ap.role,
        stance: normalizeStance(ap.suggested_stance),
        selected: true,
      })),
    );
    setKeyFactors(p.key_factors);
    setConstraints(p.constraints);
    setFollowups(p.followup_questions);
  }

  async function runClarify(useNote: boolean) {
    if (!decision.trim()) {
      setError("Type your decision first, then refine.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const next = await clarify(
        decision.trim(),
        useNote ? plan : null,
        useNote ? note.trim() || null : null,
      );
      hydrate(next);
      if (useNote) setNote("");
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Could not refine the decision. You can still run it directly.",
      );
    } finally {
      setLoading(false);
    }
  }

  function togglePerson(name: string) {
    setPeople((ps) =>
      ps.map((p) => (p.name === name ? { ...p, selected: !p.selected } : p)),
    );
  }
  function cyclePersonStance(name: string) {
    setPeople((ps) =>
      ps.map((p) =>
        p.name === name ? { ...p, stance: STANCE_NEXT[p.stance] } : p,
      ),
    );
  }

  function applyOption(branch: "A" | "B", text: string) {
    onApply(branch === "A" ? { optionA: text, people } : { optionB: text, people });
  }
  function applyAll() {
    const opts = plan?.suggested_options ?? [];
    onApply({ optionA: opts[0], optionB: opts[1], people });
  }

  return (
    <div className="p-lg space-y-lg animate-in">
      {/* Initial generate / status */}
      {!plan && (
        <div className="flex flex-col items-start gap-sm">
          <p className="font-body text-sm text-on-surface-variant max-w-xl">
            Let Lynsea read your decision and suggest the options, the people
            involved, and the factors worth modeling. You can edit everything
            before running — or skip this and run now.
          </p>
          <button
            type="button"
            onClick={() => runClarify(false)}
            disabled={loading}
            className="rounded-lg bg-primary/15 border border-primary/40 px-4 py-2 font-label text-sm text-primary hover:bg-primary/25 transition-colors focus-ring disabled:opacity-50 flex items-center gap-2"
          >
            <Icon name="auto_awesome" className="text-base" />
            {loading ? "Refining…" : "Refine with Lynsea"}
          </button>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-error/30 bg-error/10 px-3 py-2 text-xs text-error"
        >
          {error}
        </div>
      )}

      {plan && (
        <>
          {/* Suggested options */}
          {plan.suggested_options.length > 0 && (
            <Field label="Suggested options" hint="Prefill the two branch fields.">
              <div className="flex flex-wrap gap-2">
                {plan.suggested_options.map((opt, i) => (
                  <div
                    key={`${opt}-${i}`}
                    className="flex items-center gap-1 rounded-full bg-surface-container border border-surface-variant pl-3 pr-1 py-1 text-sm text-on-surface"
                  >
                    <span className="max-w-[16rem] truncate" title={opt}>
                      {opt}
                    </span>
                    <button
                      type="button"
                      onClick={() => applyOption("A", opt)}
                      className="text-[11px] font-semibold px-1.5 py-0.5 rounded-full"
                      style={{ color: "#22D3EE", background: "rgba(34,211,238,0.14)" }}
                      title="Use as Option A"
                    >
                      → A
                    </button>
                    <button
                      type="button"
                      onClick={() => applyOption("B", opt)}
                      className="text-[11px] font-semibold px-1.5 py-0.5 rounded-full"
                      style={{ color: "#FBBF24", background: "rgba(251,191,36,0.14)" }}
                      title="Use as Option B"
                    >
                      → B
                    </button>
                  </div>
                ))}
              </div>
              {plan.suggested_options.length >= 2 && (
                <button
                  type="button"
                  onClick={applyAll}
                  className="mt-2 text-xs text-primary hover:underline focus-ring rounded"
                >
                  Use the first two as A &amp; B
                </button>
              )}
            </Field>
          )}

          {/* Affected people — selectable stance chips */}
          {people.length > 0 && (
            <Field
              label="Affected people"
              hint="Tap a name to include/exclude. Tap the stance to cycle it."
            >
              <div className="flex flex-wrap gap-2">
                {people.map((p) => {
                  const meta = STANCE_META[p.stance];
                  return (
                    <div
                      key={p.name}
                      className={`flex items-center gap-2 rounded-full border pl-1 pr-1 py-1 transition-colors ${
                        p.selected
                          ? "bg-surface-container border-primary/40"
                          : "bg-surface-container-low border-surface-variant opacity-55"
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => togglePerson(p.name)}
                        className="flex items-center gap-1.5 pl-2 focus-ring rounded-full"
                        aria-pressed={p.selected}
                      >
                        <Icon
                          name={p.selected ? "check_circle" : "radio_button_unchecked"}
                          className="text-sm"
                          fill={p.selected}
                        />
                        <span className="text-sm text-on-surface">{p.name}</span>
                        {p.role && (
                          <span className="text-[11px] text-on-surface-variant">
                            · {p.role}
                          </span>
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => cyclePersonStance(p.name)}
                        className="font-label text-[11px] px-2 py-0.5 rounded-full"
                        style={{ color: meta.color, background: meta.bg }}
                        aria-label={`${p.name} stance: ${meta.label}`}
                      >
                        {meta.label}
                      </button>
                    </div>
                  );
                })}
              </div>
            </Field>
          )}

          {/* Key factors — editable list */}
          {keyFactors.length > 0 && (
            <Field label="Key factors" hint="Edit or clear any that don't fit.">
              <EditableList items={keyFactors} onChange={setKeyFactors} />
            </Field>
          )}

          {/* Value prompts (read-only guidance) */}
          {plan.value_prompts.length > 0 && (
            <Field
              label="Value questions"
              hint="You'll weigh these on the results page once dimensions are generated."
            >
              <ul className="space-y-1.5">
                {plan.value_prompts.map((vp, i) => (
                  <li
                    key={i}
                    className="flex gap-2 text-xs text-on-surface-variant leading-relaxed"
                  >
                    <span className="text-primary shrink-0" aria-hidden>
                      •
                    </span>
                    <span>
                      <span className="text-on-surface">{vp.question}</span>
                      {vp.dim_hint && (
                        <span className="ml-1 text-outline">({vp.dim_hint})</span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </Field>
          )}

          {/* Constraints — editable list */}
          {constraints.length > 0 && (
            <Field label="Constraints" hint="Hard limits Lynsea should respect.">
              <EditableList items={constraints} onChange={setConstraints} />
            </Field>
          )}

          {/* Followup questions — editable */}
          {followups.length > 0 && (
            <Field
              label="Open questions"
              hint="Answer inline to sharpen the next refinement."
            >
              <EditableList items={followups} onChange={setFollowups} />
            </Field>
          )}

          {/* Refine again — iterative note */}
          <div className="rounded-lg border border-surface-variant bg-surface-container-low p-md">
            <label className="font-label text-outline uppercase tracking-wider text-xs mb-2 block">
              Refine again
            </label>
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                value={note}
                onChange={(e) => setNote(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    runClarify(true);
                  }
                }}
                placeholder="e.g. My partner doesn't know yet; budget is tight"
                className="flex-1 bg-surface-container border border-surface-variant rounded px-3 py-2 text-sm text-on-surface focus-ring placeholder:text-outline-variant"
              />
              <button
                type="button"
                onClick={() => runClarify(true)}
                disabled={loading}
                className="rounded-lg border border-primary/40 bg-primary/15 px-4 py-2 font-label text-sm text-primary hover:bg-primary/25 transition-colors focus-ring disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <Icon name="refresh" className="text-base" />
                {loading ? "Refining…" : "Refine"}
              </button>
            </div>
          </div>

          <button
            type="button"
            onClick={applyAll}
            className="rounded-lg bg-primary/15 border border-primary/40 px-4 py-2 font-label text-sm text-primary hover:bg-primary/25 transition-colors focus-ring flex items-center gap-2"
          >
            <Icon name="done_all" className="text-base" />
            Apply suggestions to the form
          </button>
        </>
      )}
    </div>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="font-label text-outline uppercase tracking-wider text-xs mb-1">
        {label}
      </h3>
      {hint && (
        <p className="font-caption text-caption text-outline mb-2">{hint}</p>
      )}
      {children}
    </div>
  );
}

/** A small editable string list with per-row edit + remove. */
function EditableList({
  items,
  onChange,
}: {
  items: string[];
  onChange: (next: string[]) => void;
}) {
  return (
    <div className="space-y-1.5">
      {items.map((item, i) => (
        <div key={i} className="flex items-center gap-2">
          <input
            value={item}
            onChange={(e) => {
              const next = items.slice();
              next[i] = e.target.value;
              onChange(next);
            }}
            className="flex-1 bg-surface-container border border-surface-variant rounded px-3 py-1.5 text-sm text-on-surface focus-ring"
          />
          <button
            type="button"
            onClick={() => onChange(items.filter((_, j) => j !== i))}
            className="text-outline hover:text-error transition-colors focus-ring rounded"
            aria-label="Remove"
          >
            <Icon name="close" className="text-sm" />
          </button>
        </div>
      ))}
    </div>
  );
}
