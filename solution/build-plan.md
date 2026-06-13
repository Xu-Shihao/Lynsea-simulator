# Build Plan — Lynsea: a General Decision Outcome Simulator

**One-liner:** Point Lynsea at *any* decision — personal, business, product, or policy — and it builds a
living world model of the people and forces that decision touches, fast-forwards that world under each
option as a seed-locked counterfactual, and shows you the scored, side-by-side futures plus the exact
moments and human dynamics that made them diverge.

**Build-day target:** a working, demo-ready vertical slice in ~1 day with 2 builders.

> This is the BUILD-READY unified plan. It merges **Plan 01 (Lynsea life-sim sandbox)** and
> **Plan 03 (Decision Twin)** into one decision-agnostic engine. See §1 for exactly how they merge.

---

## 1. How Plan 01 and Plan 03 are merged (explicit)

The two plans are two halves of the same engine; each fixes the other's weakness.

| Ingredient | From | What it contributes to the merged product |
|---|---|---|
| Persistent **stakeholder/force agents** populate the world; outcomes **emerge from agent interactions** | 01 | Realism + non-obvious second-order consequences (the co-founder friendship fractures) |
| **Referee + Outcome agent** convert free-form dialogue into structured, scoreable events | 01 | Stops narrative runaway and unfalsifiable optimism |
| **Shared seeded `WorldState`** stepped over time; **paired counterfactual rollouts under a fixed seed** | 03 | Branches differ *only* by the decision → honest, causal contrast |
| **Values-weighted outcome score** the user calibrates + live **counterfactual interrogation** | 03 | "Better *for you*", and the memorable interactive demo beat |

- **01's weakness** — a thin causal/scoring story — is fixed by **03's** seeded paired rollouts and
  values-weighted scorer.
- **03's weakness** — abstract "life-domain" agents instead of real actors — is fixed by **01's**
  persistent stakeholder persona agents.
- **The merge generalizes both.** 01 was career-pivot-shaped; 03 was relocation-shaped. The unified
  engine is **decision-agnostic**: the same loop runs "stay vs. move to Seattle," "ship feature A vs. B,"
  or "raise prices 10%." You only instantiate different **entity agents** — *stakeholder personas*
  (partner, manager, co-founder) and/or *force agents* (a market, churn, support load, regulation) —
  plus a per-decision values vector.

---

## 2. Unified product spec — the decision-agnostic core loop

One input box: *"What are you deciding, and who/what does it touch?"* Then five stages:

1. **Frame** — the **Framer** extracts the decision, its 2–3 options, and the entities it touches
   (stakeholders + forces) from plain language.
2. **Model** — the **Twin-Builder** runs a short structured interview → a `UserModel` (values weights,
   risk tolerance, constraints). Each extracted entity is materialized as a persona/force agent with an
   editable card (goals, fears, style).
3. **Simulate** — the **Orchestrator** forks the seeded `WorldState` once per option and steps time
   forward. Each step, entity agents react to events and to each other; a **Referee** caps drift and an
   **Outcome/Scorer** agent logs structured events. Paired branches share the same seed, so only the
   decision variable differs.
4. **Score & contrast** — each branch's trajectory is folded into a values-weighted **Decision Outcome
   Score**; divergence points and the dynamics that drove them are surfaced side by side.
5. **Interrogate** — the user asks "what if X?" and that single counterfactual re-runs live in seconds.

---

## 3. Merged architecture

```
                         ┌──────────────────────────────────────────────┐
   user input ──▶ FRAMER ─▶ decision + options + entities (stakeholders/forces)
                         └──────────────────────────────────────────────┘
                                          │
                         TWIN-BUILDER ─▶ UserModel (values, risk, constraints)
                                          │
                         ┌──────────────────────────────────────────────┐
                         │              ORCHESTRATOR (Multica fan-out)    │
                         │  forks seeded WorldState → one branch / option │
                         └──────────────────────────────────────────────┘
                            │  branch A (seed S)          │  branch B (seed S)
                            ▼                              ▼
              step loop ×N:                    step loop ×N:
              ┌─ persona/force agents ─┐       ┌─ persona/force agents ─┐
              │ propose deltas + events│       │ propose deltas + events│
              ├─ REFEREE: cap drift,   │       ├─ REFEREE: cap drift,   │
              │   schema-validate      │       │   schema-validate      │
              ├─ OUTCOME: log events,  │       ├─ OUTCOME: log events,  │
              │   update WorldState    │       │   update WorldState    │
              └────────────────────────┘       └────────────────────────┘
                            │                              │
                            └───────────▶ SCORER ◀─────────┘
                              values-weighted Decision Outcome Score
                                          │
                                          ▼
                                   UI: side-by-side timelines + divergence points
                                       + "what if?" live re-run
```

**Components**
- **Framer** (Claude/Opus): plain language → decision, options, entity list (typed stakeholder vs. force).
- **Twin-Builder** (Claude/Opus): structured interview → `UserModel` with values weights and constraints.
- **Orchestrator** (Multica): owns the seeded `WorldState`, forks one branch per option, runs the step
  loop, parallelizes branches and per-entity agent calls.
- **Per-entity agents** (Claude/Sonnet): one per stakeholder persona or domain/force; each proposes
  monthly/weekly state deltas + candidate events, in role.
- **Referee** (Claude/Sonnet): caps deltas per step, enforces JSON schema, rejects contradictions and
  runaway optimism, keeps persona memory consistent.
- **Outcome/Scorer** (Claude/Opus): commits validated events into `WorldState`; folds the trajectory into
  the values-weighted score with uncertainty bands.
- **Shared seeded `WorldState`**: single source of truth, identical seed across paired branches.
- **UI**: single-page React app — input → editable entity cards → "Run" → side-by-side timelines with
  divergence markers and a "what if?" box.

**Where Claude Code + Multica are central**
- Claude Code *builds* the orchestrator, schemas, and agent prompts on build day, and is used live to
  re-run counterfactuals.
- Multica *orchestrates* the parallel branch rollouts and the per-entity sub-agent fan-out at runtime —
  the multi-agent world **is** the product, not a wrapper.

---

## 4. Data schemas (JSON)

**UserModel** — the decider's calibration.
```json
{
  "decider_id": "u1",
  "decision": "Stay in current job vs. join friend's startup",
  "options": ["stay", "join_fulltime", "join_parttime"],
  "values_weights": { "finance": 0.30, "relationships": 0.30, "career_growth": 0.25, "wellbeing": 0.15 },
  "risk_tolerance": 0.4,
  "constraints": ["6-month runway max", "partner must agree on income dip"],
  "horizon_steps": 24,
  "step_unit": "week"
}
```

**WorldState** — the shared, seed-locked, per-branch object stepped over time.
```json
{
  "branch": "join_fulltime",
  "seed": 1337,
  "t": 6,
  "step_unit": "week",
  "metrics": { "finance": 42, "relationships": 61, "career_growth": 70, "wellbeing": 55 },
  "entities": [
    { "id": "partner", "type": "stakeholder", "persona": { "goals": ["stability"], "fears": ["income dip"], "style": "direct" }, "memory": ["agreed to 3-month trial"] },
    { "id": "cofounder", "type": "stakeholder", "persona": { "goals": ["fast hire"], "fears": ["equity dilution"], "style": "intense" }, "memory": [] },
    { "id": "market", "type": "force", "params": { "volatility": 0.6 }, "memory": [] }
  ],
  "event_log": []
}
```

**Event** — every committed step output (the unit the Scorer reads).
```json
{
  "id": "evt_018",
  "branch": "join_fulltime",
  "t": 14,
  "source_entity": "cofounder",
  "type": "conflict",
  "summary": "Equity split renegotiation strains the friendship.",
  "metric_deltas": { "relationships": -18, "career_growth": +4, "wellbeing": -9 },
  "is_divergence_point": true,
  "confidence": 0.62
}
```

**Values-weighted scoring function** — deterministic, computed by a tool (not the narrating agents).
```
score(branch) = Σ_domain  w_domain * normalize(final_metric_domain)
              − risk_penalty(volatility_of_trajectory, user.risk_tolerance)

Reported as: point score + uncertainty band (e.g. "78 ± 6"), plus per-domain breakdown
and the ranked list of divergence-point events. "Directional, not destiny."
```

---

## 5. Build-day scope — the ~1-day vertical slice

**MVP (must work live):**
- One seeded scenario, **2 decision branches**.
- **3 entity agents** (e.g. partner + co-founder + a market/force) + Referee + Outcome/Scorer.
- **N steps** stepped forward (target 12–24), shared seed across both branches.
- Values-weighted **Decision Outcome Score** with uncertainty band + per-domain breakdown.
- **Side-by-side timeline UI** with divergence-point markers (3 pivotal moments highlighted).
- **One live counterfactual re-run** ("what if the startup folds?").
- Entity cards editable before the run.

**Explicitly OUT of scope for the day:**
- Real personal-data ingestion (use the guided interview).
- Auth / accounts / persistence beyond a session.
- More than 2 branches; more than ~4 entities.
- Mobile polish; fine-grained statistical calibration; multi-decision projects.

**Hour-by-hour cut (~1 day, 2 builders):**

| Time | Builder A (engine) | Builder B (UI + demo) |
|---|---|---|
| 0–2h | `UserModel`/`WorldState`/`Event` schemas + Framer & Twin-Builder prompts | Scaffold React SPA: input box, entity cards, run button |
| 2–5h | Orchestrator fork + seeded step loop + per-entity/Referee/Outcome agents end-to-end in terminal | Timeline component + side-by-side metric traces wired to mock data |
| 5–7h | Deterministic Scorer + divergence detection; expose live counterfactual re-run endpoint | Connect UI to real engine; divergence markers; score panel with bands |
| 7–8h | **Seed-lock** the demo scenario; pre-warm cache; parallelize branches | Script + rehearse the 2-min demo; polish the "wow" beat |

---

## 6. The 2-minute demo script

| Time | On screen / action | Narration |
|---|---|---|
| 0:00 | Type the dilemma live: *"Stay in my job, or join my friend's startup."* Framer extracts 3 entities + 2 options. | "One decision. Lynsea finds the people and forces it touches." |
| 0:25 | Click the **partner** card; tweak fear → "financial instability." | "These are real actors you can edit — not a single model's guess." |
| 0:40 | Hit **Run**. Two futures animate step-by-step; agents react to each other. | "Same seed, only the decision differs — a controlled counterfactual." |
| 1:10 | A *surprising* emergent event surfaces in the Join branch: the co-founder friendship fractures over equity. | "This came from the people simulating each other." |
| 1:30 | Side-by-side lands: Stay = safe but flat (score 71); Join = spikes then craters at the equity fight (78 → divergence marked). | "Not advice — a trajectory, scored *for her values*." |
| 1:40 | **WOW BEAT — live counterfactual:** judge picks the fear, "what if the startup folds in year 1?" We re-run that one branch live; Join collapses to 48 and the UI highlights the exact divergence step. | "Now she's not guessing — she's *seen* it." |
| 2:00 | — | Close. |

---

## 7. Evaluation plan

Aligned to the research dossier's methodology (`solution/research-dossier.md`): demonstrate **causal
honesty**, **face validity vs. a baseline**, and **decision-usefulness before/after**.

1. **Causal sanity (controlled counterfactual).** Fix the seed; flip *only* the decision variable. Diff
   the two `WorldState` event logs: shared random events stay identical while decision-driven events
   diverge. A side-by-side diff view proves the contrast is causal, not noise — and that persona memory
   stays stable across branches.
2. **Face validity vs. baseline.** Blind-rate generated divergence-point events as "could realistically
   happen" against a single-prompt GPT "pros/cons" baseline. Target: the multi-agent paired rollout is
   rated markedly more concrete, plausible, and decision-useful, and surfaces more *non-obvious*
   second-order consequences.
3. **Before/after decision confidence.** Capture the user's stated confidence and clarity in the decision
   pre- vs. post-simulation; expect a measurable shift toward "I can see the trade-off."

(If `research-dossier.md` specifies named metrics or a panel size, adopt those verbatim; the three checks
above map onto its causal-sim and evidence-based-evaluation methodology.)

---

## 8. Risks & mitigations

| Risk | Mitigation / fallback |
|---|---|
| **Narrative runaway / unfalsifiable optimism** (agents tell a rosy story) | Referee caps deltas per step; Outcome events are schema-validated; the Scorer is a deterministic tool, not a narrating agent. |
| **Incoherent long trajectories** (agents drift/contradict across steps) | Shared `WorldState` is single source of truth; per-step delta caps; schema-validate every agent output; persona memory pinned. |
| **"Fake-precision" credibility** (78 vs. 71 looks like false certainty) | Report uncertainty bands, frame as "directional, not destiny," and lead with the *divergence point*, not the absolute number. |
| **Demo flakiness from many live LLM calls** | Seed-locked, pre-warmed deterministic main path; only the single counterfactual is a live call on stage; cache the rehearsed scenario. |
| **Latency from agent fan-out** | Cap to ~3 entities × N steps × 2 branches; parallelize branches and per-entity calls via Multica. |
| **Skepticism that "it's just role-play"** | Open the demo with the seed-locked causal diff and the baseline comparison, not the story. |

---

## 9. Self-score (1–5 each)

- **Technical innovation: 5/5** — a seeded multi-agent counterfactual world with state-divergence control,
  persistent stakeholder/force agents, *and* a values-weighted scorer is a genuine mechanism that neither
  Plan 01 nor 03 had alone; the merge is strictly stronger than either.
- **Implementation quality (demo-ability in 1 day): 3/5** — multi-agent, multi-step coherence across two
  branches is the riskiest slice; seed-locking and the single-live-counterfactual demo make it
  demo-able, but the moving-part count is ambitious for one day.
- **Potential impact: 5/5** — the engine is decision-agnostic (personal, business, product, policy), so
  the same build addresses a universal, underserved, high-stakes problem; the "see your alternate future"
  hook is memorable and broadly applicable.
- **Total: 13/15**
