# Lynsea Prediction Enrichment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Lynsea's fixed 5-metric single-pass engine with per-decision schema-generated dimensions, a bounded multi-agent memory/interaction simulation (Medium/Heavy), and an LLM-generated iterative "Refine your world" clarification flow — without breaking determinism, the stub path, or Quick-mode latency.

**Architecture:** Backend foundation = a dynamic `Dimension` set generated once and shared by both branches; `MetricPoint.scores` becomes a `{dim_id: 0-100}` map. New engine modules `dimensions.py`, `memory.py`, `agents.py`, `clarify.py`. Quick mode keeps the current single-pass generator (now dimension-aware); Medium/Heavy run a month-by-month agent interaction loop with an in-process memory stream + reflection. Frontend renders N dynamic curves, an LLM-driven clarification panel, and results-page value sliders.

**Tech Stack:** FastAPI + Pydantic v2 + sse-starlette + Anthropic SDK (backend, Python 3.9, venv at `backend/.venv`); Next.js 16 + Tailwind v4 + Recharts (frontend). Tests: pytest (stub path, no key). Spec: `docs/superpowers/specs/2026-06-13-lynsea-prediction-enrichment-design.md`.

**Branch:** `feat/claude-code-implement`. Run tests with `backend/.venv/bin/pytest backend/tests -q`. All new LLM steps MUST route through `app.config.complete*` and fall back to a deterministic stub so tests pass with no key.

---

## Phase 1 — Data contract foundation (everything depends on this)

### Task 1: Add `Dimension`, dynamic `MetricPoint.scores`, `ClarificationPlan` to contracts

**Files:**
- Modify: `backend/app/contracts.py`
- Test: `backend/tests/test_contracts_dynamic.py`

- [ ] **Step 1: Write failing tests**
```python
# backend/tests/test_contracts_dynamic.py
from app.contracts import Dimension, MetricPoint, BranchPoint, ClarificationPlan, SimResult

def test_dimension_model():
    d = Dimension(id="economic", label="Economic", description="money & security",
                  polarity="higher_is_better")
    assert d.polarity == "higher_is_better"

def test_metricpoint_scores_map():
    mp = MetricPoint(branch="A", month=1, scores={"economic": 60.0, "career": 55.0},
                     supporting_event_ids=["ev_A_00"])
    assert mp.scores["economic"] == 60.0 and mp.supporting_event_ids

def test_branchpoint_uses_dimension():
    bp = BranchPoint(month=3, dimension="mental", magnitude=12.0,
                     description="diverges", cause_chain="...")
    assert bp.dimension == "mental"

def test_clarification_plan():
    cp = ClarificationPlan(suggested_options=["A","B"],
        affected_people=[{"name":"partner","role":"partner","suggested_stance":"unknown"}],
        key_factors=["stress"], value_prompts=[{"dim_hint":"mental","question":"How much does wellbeing matter?"}],
        constraints=["mortgage"], followup_questions=["Does your partner know?"])
    assert cp.suggested_options == ["A","B"]
```
- [ ] **Step 2: Run** `backend/.venv/bin/pytest backend/tests/test_contracts_dynamic.py -q` → FAIL (models undefined).
- [ ] **Step 3: Implement** in `contracts.py`:
  - `Dimension {id:str, label:str, description:str, polarity:str}` (polarity ∈ higher_is_better|lower_is_better).
  - Change `MetricPoint`: remove the 5 float fields; add `scores: Dict[str, float] = {}` (validate 0–100 per value) keep `branch, month, supporting_event_ids`.
  - Change `BranchPoint.metric` → `dimension: str`.
  - `SimResult`: add `dimensions: List[Dimension] = []`.
  - `SimRequest.values: Optional[Dict[str,float]]` (already dict-ish) — keep; semantics now dim_id→weight.
  - Add `AffectedPersonHint {name, role, suggested_stance}`, `ValuePrompt {dim_hint, question}`, `ClarificationPlan {suggested_options, affected_people:[AffectedPersonHint], key_factors, value_prompts:[ValuePrompt], constraints, followup_questions}`.
  - Add `ClarifyRequest {decision:str, prior: Optional[ClarificationPlan]=None, note: Optional[str]=None}`.
  - Keep `METRIC_DIMS`/`DEFAULT_VALUES` exported for the stub fallback default dimension set.
- [ ] **Step 4: Run** the test → PASS.
- [ ] **Step 5: Commit** `feat(contracts): dynamic dimensions + clarification models`.

### Task 2: Add a canonical default dimension set for the stub path

**Files:** Modify `backend/app/contracts.py` (or `engine/common.py`); Test `backend/tests/test_contracts_dynamic.py`
- [ ] **Step 1:** add `DEFAULT_DIMENSIONS: List[Dimension]` = the original 5 (economic/career/relationship/mental/autonomy, each higher_is_better except mental/relationship also higher_is_better) so stub generation is deterministic. Test asserts `len(DEFAULT_DIMENSIONS)==5` and unique ids.
- [ ] **Step 2:** Commit `feat: default dimension set for stub path`.

---

## Phase 2 — `dimensions.py` (generate the per-decision set)

### Task 3: Dimension generation (LLM + stub), shared across branches

**Files:** Create `backend/app/engine/dimensions.py`; Test `backend/tests/test_dimensions.py`
- [ ] **Step 1: Write failing tests** (force stub via monkeypatching `config.complete_json`→None):
```python
# backend/tests/test_dimensions.py
import app.config as config
from app.engine.dimensions import generate_dimensions

def test_generates_4_to_8_unique(monkeypatch):
    monkeypatch.setattr(config, "complete_json", lambda *a, **k: None)  # stub path
    dims = generate_dimensions("Should I take a higher-paying but stressful job?", seed=123)
    assert 4 <= len(dims) <= 8
    assert len({d.id for d in dims}) == len(dims)

def test_deterministic_for_seed(monkeypatch):
    monkeypatch.setattr(config, "complete_json", lambda *a, **k: None)
    a = generate_dimensions("X decision", seed=7); b = generate_dimensions("X decision", seed=7)
    assert [d.id for d in a] == [d.id for d in b]
```
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** `generate_dimensions(decision: str, seed: int) -> List[Dimension]`:
  - Build a strict prompt asking for 4–8 dimensions as JSON `[{id,label,description,polarity}]` relevant to the decision; call `config.complete_json`.
  - Validate into `Dimension` (slugify ids, dedupe, clamp count to [4,8]); on None/invalid → return `DEFAULT_DIMENSIONS` (deterministic). `seed` only affects the stub ordering, not LLM.
  - Generated ONCE per simulation by the orchestrator and passed to both branches.
- [ ] **Step 4: Run** → PASS. **Step 5: Commit** `feat(engine): per-decision dimension generation`.

---

## Phase 3 — `memory.py` (EverOS-inspired in-process memory)

### Task 4: Memory stream, retrieval ranking, reflection

**Files:** Create `backend/app/engine/memory.py`; Test `backend/tests/test_memory.py`
- [ ] **Step 1: Write failing tests:**
```python
# backend/tests/test_memory.py
from app.engine.memory import MemoryStream, MemoryItem

def test_retrieval_ranks_recency_importance_relevance():
    ms = MemoryStream()
    ms.add(MemoryItem(text="got a promotion at work", importance=9, month=5, source="event"))
    ms.add(MemoryItem(text="watered the plants", importance=1, month=1, source="event"))
    top = ms.retrieve(query="work promotion raise", now_month=5, k=1)
    assert "promotion" in top[0].text

def test_reflection_fires_past_threshold():
    ms = MemoryStream(reflection_threshold=10)
    for i in range(4):
        ms.add(MemoryItem(text=f"stressful overtime {i}", importance=5, month=i, source="event"))
    reflections = ms.maybe_reflect(now_month=4)
    assert reflections and reflections[0].importance >= 5  # a synthesized higher-level belief
```
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement:**
  - `MemoryItem {text, importance:int(1-10), month:int, source:str, kind:str="obs"}`.
  - `MemoryStream`: `add()`, `retrieve(query, now_month, k)` scoring `score = wr*recency + wi*(importance/10) + wl*lexical_overlap(query,text)` where `recency=1/(1+now_month-month)`, lexical = Jaccard over lowercased word sets; deterministic tie-break by (importance, -month). `maybe_reflect(now_month)`: if summed importance since last reflection ≥ threshold, synthesize a reflection item (text = joined top retrieved memories or an LLM summary via `config.complete` with stub fallback = concatenated salient texts), importance = min(10, avg+2), kind="reflection"; reset counter. No vector embeddings.
- [ ] **Step 4: Run** → PASS. **Step 5: Commit** `feat(engine): in-process agent memory stream + reflection`.

---

## Phase 4 — `agents.py` (bounded multi-agent interaction)

### Task 5: Agent step + world reconciliation producing emergent, traceable events

**Files:** Create `backend/app/engine/agents.py`; Test `backend/tests/test_agents.py`
- [ ] **Step 1: Write failing test** (stub path):
```python
# backend/tests/test_agents.py
import app.config as config
from app.engine.agents import run_interaction
from app.engine.personas import build_personas

def test_emergent_events_are_traceable(monkeypatch):
    monkeypatch.setattr(config, "complete_json", lambda *a, **k: None)
    monkeypatch.setattr(config, "complete", lambda *a, **k: None)
    personas = build_personas("relocate for partner", ["Move","Stay"], ["my partner"], seed=1, mode="medium")
    out = run_interaction(branch="A", option_text="Move", decision="relocate for partner",
                          personas=personas, backbone=[], dimensions=[], seed=1, mode="medium")
    assert out.events  # produced events
    # every interaction-origin event references a persona that exists
    ids = {p.id for p in personas}
    assert all(set(e.involved_personas) <= ids for e in out.events)
```
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** `run_interaction(...) -> InteractionResult{events:[TimelineEvent], memories: per-agent}`:
  - Give each persona a `MemoryStream`, seeded with persona key_concerns + beliefs.
  - For each month in the horizon (batched: process every month but allow 1 LLM call per agent-month in Medium, fewer in Heavy via batching): retrieve memories, build a per-agent prompt (persona + beliefs + ToM + retrieved memory + branch option + this month's shared backbone) asking for the agent's reaction/action as JSON; `config.complete_json` with stub fallback (deterministic, persona-trait-driven reaction).
  - World step: reconcile agent reactions into `TimelineEvent`s (skeleton for expected milestones, perturbation for clashes where two agents' stances conflict → emergent conflict event). Write outcomes back to each agent's memory; call `maybe_reflect`.
  - Respect `config.force_stub_active` / budget escalation (reuse orchestrator hook).
  - Deterministic stub path: no LLM → trait-based reactions so tests are stable.
- [ ] **Step 4: Run** → PASS. **Step 5: Commit** `feat(engine): bounded multi-agent interaction loop`.

---

## Phase 5 — `clarify.py` + `/api/clarify`

### Task 6: Clarification plan generation

**Files:** Create `backend/app/engine/clarify.py`; Test `backend/tests/test_clarify.py`
- [ ] **Step 1: Write failing test** (stub path): `generate_clarification("Should I quit to start a startup?", prior=None, note=None)` returns a `ClarificationPlan` with ≥2 suggested_options, ≥1 key_factor, ≥1 value_prompt (stub fallback derives from keywords). Refine round: passing `prior`+`note` returns a plan incorporating the note (stub: appends note to constraints).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** `generate_clarification(decision, prior, note) -> ClarificationPlan` via `config.complete_json` (schema) with deterministic keyword-based stub fallback.
- [ ] **Step 4: Run** → PASS. **Step 5: Commit** `feat(engine): LLM clarification plan + stub`.

### Task 7: `/api/clarify` route

**Files:** Modify `backend/app/api/routes.py`; Test `backend/tests/test_api.py`
- [ ] **Step 1: Write failing test:** TestClient `POST /api/clarify {"decision":"..."}` → 200 with a valid ClarificationPlan JSON.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** `POST /api/clarify` calling `clarify.generate_clarification`, returning `ClarificationPlan.model_dump()`.
- [ ] **Step 4: Run** → PASS. **Step 5: Commit** `feat(api): POST /api/clarify`.

---

## Phase 6 — Make scoring/branchpoints/credibility dimension-agnostic + orchestrator wiring

### Task 8: Dimension-agnostic scoring

**Files:** Modify `backend/app/engine/scoring.py`; Test `backend/tests/test_scoring.py` (update)
- [ ] **Step 1: Update test:** `score_branch(branch, option_text, personas, events, seed, mode, dimensions)` → every `MetricPoint.scores` has a key for EVERY dimension id, each 0–100, and `supporting_event_ids` non-empty (ALG-40 preserved).
- [ ] **Step 2: Run** → FAIL (signature/shape changed).
- [ ] **Step 3: Implement:** generalize `_option_bias`/`_event_month_effects` to emit per-dimension deltas keyed by dim_id (map known ids to existing keyword effects; unknown dims get a neutral baseline + small event-driven drift using the dimension's polarity to orient skeleton vs perturbation effects). Build `scores={dim.id: clamp(state[dim.id])}`.
- [ ] **Step 4: Run** → PASS. **Step 5: Commit** `refactor(scoring): dimension-agnostic scores map`.

### Task 9: Branch points + credibility + recommendation over dynamic dims

**Files:** Modify `branchpoints.py`, `credibility.py`; Tests update `test_scoring.py`/new
- [ ] **Step 1: Update tests:** branch points reference a real dim id; recommendation aggregates value-weighted over dims (default neutral); probabilistic phrasing retained (no "will/definitely").
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement:** `detect_branch_points(metrics, events, dimensions)` computes per-dim |A−B| divergence; `build_recommendation(metrics, options, values, dimensions)` weights by `values.get(dim.id, 5)` and dimension polarity.
- [ ] **Step 4: Run** → PASS. **Step 5: Commit** `refactor: branchpoints + recommendation over dynamic dims`.

### Task 10: Orchestrator — generate dims, stream `dimensions`, branch by mode

**Files:** Modify `backend/app/engine/orchestrator.py`, `backend/app/api/store.py` (history), `backend/app/api/routes.py` (SSE type allowed); Tests update `test_api.py`, new `test_dimensions_shared.py`
- [ ] **Step 1: Write failing test** `test_dimensions_shared.py` (stub path, drive orchestrator): after run, `result.dimensions` non-empty and the SAME for branch A and B scoring (shared); a `dimensions` event was emitted before `metric` events.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement:** in `run_simulation`: after personas+backbone, call `dimensions.generate_dimensions(decision, seed)` once → `emit("dimensions", {"dimensions":[...]})`; pass dims to scoring/branchpoints/credibility/recommendation. Mode switch: Quick → existing `simulate.generate_branch_events` (single-pass, now also fine with dims); Medium/Heavy → `agents.run_interaction` for events. Keep skeleton-first streaming, budgets, cancel, timeout. Add `"dimensions"` to allowed SSE types.
- [ ] **Step 4: Run** full `backend/.venv/bin/pytest backend/tests -q` → PASS (update any remaining old-shape assertions). **Step 5: Commit** `feat(orchestrator): dynamic dims + mode-based agent sim`.

---

## Phase 7 — Frontend

### Task 11: Types + API for dynamic dims and clarify

**Files:** Modify `frontend/lib/types.ts`, `frontend/lib/api.ts`, `frontend/lib/useSimStream.ts`
- [ ] Add `Dimension`; change `MetricPoint` to `{branch,month,scores:Record<string,number>,supporting_event_ids:string[]}`; `BranchPoint.dimension`; `SimResult.dimensions`. Add `clarify(decision, prior?, note?)` POST helper + `ClarificationPlan` type. Handle the new `dimensions` SSE event in `useSimStream` (store `dimensions`). Build must compile: `cd frontend && npm run build`.
- [ ] Commit `feat(fe): dynamic dimension + clarify types/api`.

### Task 12: Dynamic N-curve charts + results-page value sliders

**Files:** Modify `frontend/components/MetricCharts.tsx`, `CompositeScores.tsx`, `BranchPoints.tsx`, `lib/simSelectors.ts`, `ResultsView.tsx`
- [ ] Render one chart per `sim.dimensions` (not 5), reading `scores[dim.id]`, labeled by `dim.label`, A=cyan/B=amber. Composite score = value-weighted over dims (polarity-aware). Add a value-weights panel on the results page (one slider per dimension, default neutral) that live-recomputes the recommendation/composite client-side. `npm run build` green. Commit.

### Task 13: Dynamic "Refine your world" clarification panel (iterative)

**Files:** Modify `frontend/app/page.tsx`; Create `frontend/components/RefinePanel.tsx`
- [ ] After the decision textarea, a "Refine" action calls `clarify()`; render generated suggested options (prefill the two option fields), affected-people candidates (selectable chips with stance), key factors, value prompts, constraints, and followup questions as editable fields. A "Refine again" control sends a free-text note → re-calls `clarify(decision, prior, note)` (iterative). Confirmed selections feed the simulate request. Keep "Load demo" + "skip / run now". `npm run build` green. Commit.

### Task 14: Update offline demo fixture to the new shape

**Files:** Modify `frontend/lib/sampleResult.ts`
- [ ] Rebuild the fixture with `dimensions` (5–6) + `scores` maps per MetricPoint + `BranchPoint.dimension`. Offline demo route renders N curves. `npm run build` green. Commit.

---

## Phase 8 — Integration & verification

### Task 15: Live E2E + demo.sh + full suite
- [ ] `backend/.venv/bin/pytest backend/tests -q` → all green.
- [ ] Start backend; live Quick sim → confirm `dimensions` streamed, N curves, skeleton-first, completes. Medium sim → confirm multi-agent interaction events appear and are memory-traceable.
- [ ] Update `demo.sh` assertions for the dynamic-dimension shape (E2E-1/2/5/6) and the `/api/clarify` flow. Run `./demo.sh --no-frontend` (stub) → 4/4 pass.
- [ ] `cd frontend && npm run build` green; screenshot the dashboard (N curves) + the dynamic refine panel.
- [ ] Commit + push; merge to `main` per the established flow.

---

## Self-Review notes
- **Spec coverage:** dynamic dims (T1–3,8–12), multi-agent memory/interaction (T4,5,10,15), iterative clarify (T6,7,13), determinism/stub (every task forces stub in tests; dims generated once/shared T10), value sliders on results page (T12), frontend N-curves (T11–14). Out-of-scope items (embeddings, OASIS, GraphRAG, Branch-C) intentionally excluded.
- **Type consistency:** `MetricPoint.scores: Dict[str,float]`, `BranchPoint.dimension: str`, `Dimension{id,label,description,polarity}`, `generate_dimensions(decision,seed)`, `run_interaction(branch,option_text,decision,personas,backbone,dimensions,seed,mode)`, `generate_clarification(decision,prior,note)` — used consistently across tasks.
- **Stub path:** every new LLM call has a deterministic fallback so pytest needs no key.
