# Lynsea Prediction Enrichment — Design Spec

**Date:** 2026-06-13
**Status:** Approved (brainstorming) — pending implementation plan
**Branch:** `feat/claude-code-implement`

## 1. Goal

Move Lynsea from the simple single-pass MVP toward the richer vision in
`plans/Lynsea-计划.md` §4, referencing **EverOS** (self-evolving memory layer)
and **MiroFish** (multi-agent OASIS prediction engine). Three changes:

1. **Dynamic, per-decision dimensions** — replace the fixed 5 metrics with a
   schema-generated, decision-specific set (4–8), shared by both branches.
2. **A deeper agent system** — bounded month-by-month multi-agent interaction
   with in-process memory + reflection, so conflicts/events *emerge* (ALG-13)
   rather than being narrated by one LLM call (ALG-10/11/12).
3. **LLM-generated, iterative "Refine your world"** — the input refinement panel
   is no longer a hardcoded form; the LLM reads the decision and generates the
   relevant clarifying fields/questions for the user to select/edit and iterate
   on before running (FE-02 / S1 / ALG-05).

Hard constraint: the Claude API key throttles, so the design keeps **Quick mode
fast** and only runs the full agent simulation in **Medium/Heavy**. The
deterministic stub path (no key) is preserved so tests stay green.

## 2. Decisions (locked in brainstorming)

| Decision | Choice |
|----------|--------|
| Agent depth | **Bounded month-by-month interaction** (Quick light; Medium/Heavy full) |
| Dimensions | **Fully dynamic per decision**, schema-generated, 4–8, shared by A/B |
| Memory | **Lightweight in-process** (EverOS-inspired), recency×importance×**lexical** relevance; **no vector embeddings** for now (Claude has none) — future upgrade |
| Value sliders | Move to the **results page** (defaulted neutral, live re-weight), since dimensions exist only after generation |
| Refine-your-world | **LLM-generated + iterative** clarification, not a fixed form |

## 3. Architecture

### 3.1 New / changed backend engine modules (`backend/app/engine/`)
- `clarify.py` *(new)* — given the raw decision, generate a `ClarificationPlan`
  (suggested options, candidate affected people w/ inferred stance, key factors,
  value-priority prompts, constraints) via strict schema. Supports a refine
  round: user edits + free-text note → regenerate.
- `dimensions.py` *(new)* — generate the decision's dimension set (4–8) via
  schema, **once**, pre-fork → shared by both branches.
- `memory.py` *(new)* — per-agent memory stream: items with `text`,
  `importance(1–10)`, `month`, `source`, `kind`. Retrieval ranks by
  recency × importance × lexical-relevance (ALG-10). Reflection synthesizes a
  higher-level belief when cumulative importance crosses a threshold (ALG-11).
  Pure-Python, deterministic given inputs.
- `agents.py` *(new)* — the bounded interaction step: each core agent acts from
  persona + retrieved memories + beliefs + Theory-of-Mind of others + the
  branch's option + that month's shared backbone → proposes reactions/events; a
  light "world step" reconciles them into shared/branch events (emergent
  conflict, ALG-13) and writes back to memory.
- refactor `simulate.py`, `scoring.py`, `branchpoints.py`, `credibility.py` to
  be **dimension-agnostic** (operate over the generated dimension set).
- `orchestrator.py` — add `clarify` step usage + the interaction loop for
  Medium/Heavy, keep single-pass for Quick; preserve streaming + budgets.

### 3.2 Data contract (`backend/app/contracts.py` + frontend `lib/types.ts`)
- `Dimension { id, label, description, polarity: "higher_is_better"|"lower_is_better" }`
- `SimResult.dimensions: List[Dimension]`
- `MetricPoint`: replace the 5 fixed floats with `scores: Dict[str, float]`
  (dim_id → 0–100) + `supporting_event_ids`. **Breaking change** — frontend
  renders **N** curves dynamically.
- `BranchPoint.dimension: str` (dim_id; was fixed `metric`).
- `values` (M-d weights): `Dict[str, float]` keyed by dim_id, default neutral.
- `Persona`: add optional `beliefs: [str]` and `theory_of_mind: Dict[str,str]`
  (what this agent assumes about others), plus an attached memory stream
  (engine-internal, not necessarily in the API payload).
- New `ClarificationPlan` model for the clarify endpoint (fields below).

### 3.3 API (additive; existing routes stay)
- `POST /api/clarify` → body `{ decision }` (+ optional `prior` for refine
  rounds) → `ClarificationPlan { suggested_options:[str], affected_people:[{name, role, suggested_stance}], key_factors:[str], value_prompts:[{dim_hint, question}], constraints:[str], followup_questions:[str] }`.
- `POST /api/simulate` — unchanged shape, now also accepts the
  refined/confirmed fields; emits a new `dimensions` SSE event after generation,
  before metrics. `MetricPoint` payloads carry `scores` map.

## 4. Agent / memory / interaction model

- **Memory** is in-process (not the full EverOS markdown+SQLite+LanceDB stack):
  a list of memory items per agent; retrieval = top-k by
  `w_r·recency + w_i·importance + w_l·lexical_overlap`. Reflection: when summed
  importance since last reflection > threshold (≈150, per ALG-11), summarize
  retrieved memories into a new higher-importance belief item.
- **Interaction loop (Medium/Heavy):** for each month (batched to bound cost),
  each core agent (3–5 Quick → 8–12 Medium) takes a turn conditioned on
  persona + retrieved memory + beliefs; the world-step reconciles into events +
  updates memory + may reflect. Cost bounded by capping agents, batching months,
  and the existing per-phase/mode timeout budgets with preemptive stub fallback.
- **Quick mode** keeps the current fast single-pass event generation but **gains
  dynamic dimensions** (one extra cheap LLM call) — demo stays ~fast.

## 5. Determinism & safety (preserved)

- Dimensions generated **once** and shared → A/B stay comparable (M-c).
- **Seeded exogenous backbone unchanged** (no LLM) → ALG-20 / NFR-01 hold.
- Personas forked identically; agent interaction is where branches legitimately
  diverge (the controlled-experiment property: same world, only the decision +
  resulting interactions differ).
- **Deterministic stub path stays** for every new LLM step (clarify, dimensions,
  agents) so pytest passes with no key / no network.
- Probabilistic phrasing, high-risk guardrails, credibility card carry over.

## 6. Frontend changes (`frontend/`)

- **Input page:** "Refine your world" becomes dynamic — after typing the
  decision, call `/api/clarify`; render the generated options/people/factors/
  value-prompts as editable, selectable chips/fields; a "Refine again" control
  (free-text note → regenerate) for iteration; then Run.
- **Results page:** render **N** dimension curves from `sim.dimensions` (not 5);
  legend/composite scores/branch-point labels read dim metadata; **value sliders
  live here**, one per generated dimension, recomputing the M-d recommendation
  client-side. Keep the Stitch design language, split timeline, credibility card,
  safety copy, offline demo (fixture updated to the new shape).

## 7. Mode mapping

| | Quick | Medium | Heavy |
|--|------|--------|-------|
| Dimensions | dynamic (4–8) | dynamic | dynamic |
| Agent sim | single-pass | full interaction | full interaction + more agents/horizon |
| Agents | 3–5 | 8–12 | configurable |
| Horizon | 6 mo | 12–18 mo | ≥24 mo |
| Target latency | ~≤90s | minutes | by estimate |

## 8. Testing

- Update existing tests to the dynamic-dimension contract (scores map).
- New: `test_dimensions_generated_and_shared` (4–8 dims, identical across A/B),
  `test_memory_retrieval_ranking` (recency×importance×relevance order),
  `test_reflection_threshold` (reflection fires past threshold),
  `test_clarify_stub` (clarify returns a valid plan on the stub path),
  `test_emergent_event_traceable` (an interaction event links to agent memory).
- Keep all tests runnable on the **stub path** (no key).

## 9. Out of scope (future)

Vector embeddings for memory; full EverOS framework integration; GraphRAG world
graph; OpenRouter/Grok 100–1000-agent high-throughput tier (§4.5); persisted
checkpoints / what-if Branch-C re-simulation (BE-07/08).
