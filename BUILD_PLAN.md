# Lynsea MVP — Build Plan & Integration Contract (Single Source of Truth)

> **Language rule:** Everything in this repo is in **English** EXCEPT the `plans/` folder (Chinese: product spec, deep research, acceptance criteria).
> **This file is the contract.** Backend and frontend are built by separate agents. They MUST agree on the API + data shapes defined here. When in doubt, this file wins.

Lynsea turns one hard decision into **two side-by-side "parallel futures."** The user describes a decision and its two options; Lynsea builds digital-twin personas of the user + the people around them, then runs a **fixed-seed paired counterfactual** simulation so the two branches differ *only* by the decision (shared random events are byte-identical). Output: streaming month-by-month timelines, five metric curves, key branch points, and a credibility card — phrased as probabilities, never prophecy.

Acceptance targets live in `plans/Lynsea-验收标准.md` (Chinese). This MVP targets the **P0** rows.

---

## 1. Architecture

```
Browser (Next.js + Recharts)
   │  POST /api/simulate            → { sim_id }
   │  GET  /api/simulate/{id}/stream (SSE, realtime)   ← events as generated
   │  GET  /api/simulate/{id}        → full SimResult (reload)
   ▼
FastAPI (backend/app)
   ├─ api/        routes + SSE (sse-starlette), in-memory store, background sim task
   ├─ engine/     the simulation core (the differentiator)
   │   ├─ personas.py    build user + social-circle twins from minimal input (Claude)
   │   ├─ backbone.py    SEEDED-RNG shared exogenous event backbone (NO LLM → deterministic)
   │   ├─ simulate.py    per-branch decision-dependent events (Claude), plausibility guard
   │   ├─ scoring.py     5-dim metrics 0-100 per month + supporting events
   │   ├─ branchpoints.py  divergence detection + cause chain
   │   └─ credibility.py credibility card + value-weighted recommendation
   └─ config.py    Claude client + .env loading (PROVIDED — do not reinvent secret handling)
```

- **LLM:** Claude API via `backend/app/config.py`. Key + model come from repo-root `.env` (`CLAUDE_API_KEY`, `DEFAULT_MODEL=claude-haiku-4-5-20251001`). **Never hardcode or log the key.**
- **Store:** in-memory dict keyed by `sim_id` (MVP — not persistent across restarts; fine for demo).
- **Realtime:** the POST kicks off a background task that pushes events onto an `asyncio.Queue`; `/stream` yields them as SSE. **Skeleton events stream first**, perturbation/scoring fill in after.

---

## 2. API Contract (frozen for MVP)

### `POST /api/simulate`
Request:
```json
{
  "decision": "Should I take the higher-paying but high-stress job?",
  "options": ["Take the new job", "Stay at my current job"],
  "affected_people": ["my partner", "my mother"],
  "mode": "quick",
  "values": {"economic": 7, "career": 8, "relationship": 5, "mental": 6, "autonomy": 7},
  "seed": 12345
}
```
- `options`: exactly 2 (MVP). `affected_people`, `values`, `seed` optional.
- `values` each 0–10 (importance weights, for M-d recommendation). Default all 5.
- `seed` optional; if omitted derive deterministically from `decision` (stable hash).

Response: `{ "sim_id": "uuid-string" }`

### `GET /api/simulate/{sim_id}/stream` — Server-Sent Events
Each SSE message: `event: <type>` + `data: <json>`. Types and payloads:

| `event:` | `data:` payload | when |
|----------|-----------------|------|
| `status` | `{phase, message, progress}` (`phase`∈ clarify/personas/backbone/branchA/branchB/scoring/done; progress 0–1) | each phase |
| `persona` | `Persona` | one per persona, after personas built |
| `timeline_event` | `TimelineEvent` | as generated — skeleton first, then perturbation; shared exogenous appear in both branches |
| `metric` | `MetricPoint` | per branch per month |
| `branch_point` | `BranchPoint` | after both branches scored |
| `credibility` | `CredibilityCard` | near the end |
| `recommendation` | `{text, favored_branch}` (`favored_branch`∈ "A"/"B"/"tie") | near the end |
| `done` | `{sim_id}` | final; client may then GET the full result |
| `error` | `{message}` | on failure (graceful, never silent hang) |

### `GET /api/simulate/{sim_id}` → `SimResult` (full object, for reload)

---

## 3. Data Models (authoritative — see `backend/app/contracts.py`)

Branch `"A"` = `options[0]`, `"B"` = `options[1]`.

```
Persona            { id, name, role, big5{O,C,E,A,N: 0-10}, decision_style, risk_tolerance:0-10,
                     influence_weight:0-10, stance: supportive|opposed|neutral|unknown,
                     key_concerns:[str], is_default_inferred:bool }   # is_default_inferred → ALG-04 cold-start flag
TimelineEvent      { id, branch:"A"|"B", month:int, title, description,
                     kind: skeleton|perturbation|exogenous, is_shared_exogenous:bool,
                     shared_event_id:str|null, involved_personas:[str], evidence:str|null }
MetricPoint        { branch, month, economic, career, relationship, mental, autonomy (each 0-100),
                     supporting_event_ids:[str] }   # ALG-40 every score linked to ≥1 event
BranchPoint        { month, metric, magnitude, description, cause_chain }
CredibilityCard    { overall:0-100, data_sufficiency, causal_confidence, event_plausibility,
                     notes:[str], low_confidence_personas:[str] }
SimResult          { sim_id, decision, options:[str,str], mode, seed, personas:[Persona],
                     events:[TimelineEvent], metrics:[MetricPoint], branch_points:[BranchPoint],
                     credibility:CredibilityCard|null, recommendation:{text,favored_branch}|null, created_at }
```

The five metric dimensions are fixed: **economic, career, relationship, mental, autonomy** (0–100).

---

## 4. The Differentiator: Fixed-Seed Paired Counterfactual (M-b / M-c)

This is what makes Lynsea a *controlled experiment*, not two unrelated stories. Implement exactly:

1. **Seed** = `req.seed` else a stable hash of `decision` (e.g. first 4 bytes of sha256). Deterministic.
2. **Personas built ONCE** and shared by both branches (M-c: identical pre-fork state).
3. **Shared exogenous backbone** (`backbone.py`): use `random.Random(seed)` to select N exogenous, decision-independent life events from a curated template pool (e.g. "a close friend moves abroad", "rent goes up", "flu season", "a relative's wedding") and assign months. **No LLM here.** These events are emitted into **both** branches with identical `shared_event_id`, `month`, `title`, `description`, `is_shared_exogenous=true`, `kind="exogenous"`. → guarantees byte-identical shared events across branches (ALG-20) and reproducibility (NFR-01).
4. **Per-branch generation** (`simulate.py`): for each branch, Claude generates decision-DEPENDENT events (skeleton milestones first, then perturbations) **given the same personas + the same shared backbone + that branch's option.** LLM temperature does NOT affect the shared backbone (it's RNG-built), so reproducibility is testable even though the LLM is stochastic.
5. **Plausibility guard** (ALG-31/32): reject out-of-bounds events (lottery win, random death, etc.); resample ≤3 times; else downgrade to a flagged placeholder. Track resample rate → feeds `event_plausibility`.
6. **Scoring** (`scoring.py`): 5 dims 0–100 per branch per month, each with `supporting_event_ids`.
7. **Branch points** (`branchpoints.py`): months where summed |A−B| metric divergence spikes; attach a short `cause_chain`.
8. **Credibility + recommendation** (`credibility.py`): card + value-weighted (M-d) favored branch, phrased probabilistically (SYS-15) with a "this is a simulation, not a prophecy" caveat for high-risk outcomes (SYS-16).

---

## 5. Work Assignment (parallel, disjoint dirs — DO NOT touch the other side)

### Agent BACKEND → owns `backend/` only
Implement `engine/*`, `api/*`, `main.py`; use the PROVIDED `config.py` + `contracts.py`. TDD with pytest. Must produce a runnable `uvicorn app.main:app`. **Required tests:**
- `test_reproducible`: same `decision`+`seed` twice → identical shared exogenous events (hash-equal) and identical persona ids. (NFR-01)
- `test_shared_backbone_identical_across_branches`: the `is_shared_exogenous` events in branch A == branch B (hash-equal). (ALG-20)
- `test_plausibility_guard`: an injected implausible event is rejected or flagged. (ALG-31/32)
- `test_scores_have_supporting_events`: every `MetricPoint` references ≥1 event id. (ALG-40)
- Make Claude calls resilient: on API error, fall back to a deterministic stub generator so tests + demo never hard-crash (log a warning). Tests must pass WITHOUT a live key (use the stub path / monkeypatch).

### Agent FRONTEND → owns `frontend/` only
Next.js (App Router) + TS + Tailwind + Recharts. Scaffold with `npx create-next-app@latest frontend --ts --tailwind --app --no-src-dir --no-eslint --use-npm --yes` (fall back to a hand-written scaffold if offline). Build:
- **Input page**: decision text, two option fields, affected-people chips, mode selector (quick/medium/heavy), optional values sliders.
- **Results view**: **Small Multiples** — two columns (A vs B), same shared time axis, aligned months (FE-10). Shared exogenous events visually marked as shared in both columns.
- **Five metric curves** (Recharts) comparing A vs B (FE-11).
- **Branch points** highlighted on the timeline with cause text (FE-12).
- **Credibility card** (FE-22) + **uncertainty markers** for `is_default_inferred` personas (FE-23).
- **Realtime**: consume the SSE stream so events appear live, skeleton first (FE-21). Show phase/progress.
- **Safety copy**: probability phrasing; a "This is a simulation, not a prophecy" banner for high-risk results, with a "how to change this outcome" hint (FE-24/25).
- Read API base from `NEXT_PUBLIC_API_BASE` (default `http://localhost:8000`). Ship a sample `SimResult` fixture so the UI is demoable even if the backend is down.

---

## 6. Run / Dev

```bash
# Backend
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000      # docs at /docs

# Frontend
cd frontend && npm install
printf 'NEXT_PUBLIC_API_BASE=http://localhost:8000\n' > .env.local
npm run dev                                     # http://localhost:3000
```

---

## 7. Constraints (both agents)
- **English only** in all code/docs/comments (the `plans/` folder is the only Chinese exception — do not edit it).
- **Do NOT run any git commands** (the controller integrates + commits to avoid index races).
- **Do NOT touch the other agent's directory** or the repo-root `.env` / `plans/`.
- Never print, log, or hardcode the API key.
- Code must actually run. Prefer graceful degradation over crashes.

## 8. Build Status (controller updates each loop iteration)
- [x] Branch `feat/lynsea-mvp`, scaffold, contract, config.py, contracts.py
- [ ] Backend engine + API + SSE + tests (Agent BACKEND)
- [ ] Frontend app + realtime UI (Agent FRONTEND)
- [ ] Integration: end-to-end run, both servers, live SSE
- [ ] P0 acceptance pass (SYS-11/12/15/17, ALG-20/30/40, BE-03/04, FE-10/12/21, NFR-01)
- [ ] README (English) + demo script
