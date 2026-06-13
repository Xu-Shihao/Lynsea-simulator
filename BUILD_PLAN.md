# Lynsea — BUILD PLAN (integration contract · single source of truth)

> This file is the **single source of truth** for the parallel multi-agent build of Lynsea.
> Product spec: [`plans/Lynsea-计划.md`](plans/Lynsea-计划.md) · Acceptance: [`plans/Lynsea-验收标准.md`](plans/Lynsea-验收标准.md)
> API contract (backend↔frontend): [`docs/api-contract.md`](docs/api-contract.md) · Frontend design: [`docs/design/README.md`](docs/design/README.md)
>
> **Rule for every agent:** build ONLY the files you own (see §4 ownership map). Import/consume the
> interfaces in §5 — never re-define another agent's module. Never change event/field names in
> `docs/api-contract.md` without orchestrator sign-off. Never commit `.env` (it is gitignored).

## 1. What we are building (P0 / MVP)

A **decision-outcome simulator**: user describes one hard decision → backend builds a seeded world of
belief-driven personas, runs **two paired counterfactual branches (A/B)** that share the same random
events (only the decision variable differs), and streams back over SSE: side-by-side timelines,
5-dimension metric curves, fork points, value-weighted branch scores, a credibility card, and a
probabilistic (never deterministic) recommendation. Frontend renders this as two aligned "parallel
futures" columns. P0 target mode = **`quick`** (6 months, 2 branches, 3–5 personas, ≤90s full result).

P0 acceptance gates to satisfy (see acceptance doc §10 checklist):
`SYS-02/11/12/15/16/17`, `ALG-01/02/04/20/21/30/31/32/40`, `BE-03/04/11/12`, `FE-10/12/13/21/22/23`,
`NFR-01`, scenarios `E2E-1/2/5/6`.

## 2. Tech stack

- **Backend** (`backend/`): Python 3.11+, **FastAPI** + **uvicorn**, **SSE** via `sse-starlette` or
  raw `StreamingResponse`. Pydantic v2 models. LLM = **Claude API** only.
- **Frontend** (`frontend/`): **Next.js 14 (App Router) + TypeScript**, **Recharts** for curves,
  **Tailwind** for the design tokens in `docs/design/README.md`. Consumes SSE via `EventSource`/fetch-stream.
- **LLM access (`BE-11`):** ALL model calls go through `backend/app/llm.py`, which reads `.env`.
  `.env` keys: `CLAUDE_API_KEY`, `DEFAULT_MODEL` (currently `claude-haiku-4-5-20251001`).
  Model tier mapping: high-quality narrative/causal → Opus/Sonnet; high-frequency state/scoring →
  **Haiku** (the `.env` default). **No hardcoded provider that isn't in `.env`.** `.env.example` documents keys.

## 3. Reference material (git submodules — READ-ONLY)

- `MiroFish/` (OASIS/CAMEL-AI swarm prediction engine) — reference for the multi-agent world-sim
  pattern (`backend/app/{api,models,services}`). Borrow architecture/ideas; do **not** vendor wholesale.
- `EverOS/` (self-evolving memory; Markdown-as-truth, hybrid retrieval, `src/everos/{core,memory}`) —
  reference for the agent memory stream / retrieval in `simulation.py` + `memory_store.py`.
- **UserHarness** ([arXiv:2605.27721](https://arxiv.org/abs/2605.27721)) — the mind-modeling foundation:
  model every persona as **Environment→Observation→Belief→Goal→Action**; personas act on **beliefs**
  (incl. false/nested beliefs about others), so interpersonal conflict is **emergent** (from mutual
  misjudgement), not narrated. This grounds `personas.py` + `simulation.py` (`ALG-13/14`).
- Agents may `git submodule update --init MiroFish EverOS` to read source, but MUST NOT modify the
  submodules or commit gitlink/pointer changes.

## 4. File-ownership map (NO overlaps — this is what makes parallel PRs merge cleanly)

```
backend/
  app/
    main.py          FastAPI app, CORS(localhost:3000), route mounting        [BE-Core]
    config.py        .env loading, Settings, model-tier mapping               [BE-Core]
    llm.py           Claude client wrapper: call(), retry/backoff, degrade    [BE-Core]
    sse.py           SSE event framing helpers (event:/data: bytes)           [BE-Core]
    schemas.py       Pydantic models for EVERY api-contract event + requests  [BE-Core]
    orchestrator.py  6-step state machine; /simulate driver; wires modules    [BE-Core]
    interfaces.py    Protocol/ABCs the specialists implement (see §5)         [BE-Core]
    rng.py           SeededRNG, shared-event stream, shared_event_hash        [BE-Engine]
    events.py        skeleton+perturbation event generation, plausibility     [BE-Engine]
    personas.py      digital-twin build, Big5-from-behavior, cold-start tag   [BE-Twin]
    simulation.py    multi-agent social sim loop, belief updates, conflict    [BE-Sim]
    memory_store.py  memory stream (importance×recency×relevance) + reflect   [BE-Sim]
    scoring.py       5-dim scoring, value-weighting, fork detect, credibility,
                     recommendation+guardrail                                 [BE-Score]
  requirements.txt   [BE-Core seeds base deps; specialists APPEND their own lines only]
  .env.example       [BE-Core]
  tests/             [QA owns test_*.py; specialists may add unit tests for their module]
frontend/
  package.json, next.config.mjs, tailwind.config.ts, tsconfig.json, postcss   [FE-Console]
  app/layout.tsx, app/globals.css (design tokens), app/page.tsx (Console)     [FE-Console]
  lib/contract.ts  (TS types mirroring docs/api-contract.md)                  [FE-Console]
  lib/useSimulation.ts (SSE client hook + event reducer)                      [FE-Console]
  lib/mockStream.ts (local mock SSE so FE builds without backend)             [FE-Console]
  app/dashboard/page.tsx (Parallel Futures shell + column layout)             [FE-Dashboard]
  components/timeline/*  (small-multiples A/B timeline cards)                  [FE-Dashboard]
  components/charts/*    (5 Recharts dimension curves, A vs B)                 [FE-Dashboard]
  components/forks/*     (fork-point markers + explanation)                    [FE-Insight]
  components/credibility/*  (credibility gauge + 3 sub-bars)                   [FE-Insight]
  components/recommendation/*  (probabilistic leaning + guardrail strip)       [FE-Insight]
  components/evidence/*  (click-event → evidence drill-down)                   [FE-Insight]
docs/, plans/, BUILD_PLAN.md, .gitignore   [orchestrator only]
```

## 5. Interface contracts (so modules compose) — defined in `backend/app/interfaces.py` by BE-Core

BE-Core lands these Python `Protocol`s + Pydantic models FIRST, with **stub implementations** so the
full SSE stream runs end-to-end with placeholder data on day one. Specialists then replace each stub
with the real implementation in their own file, keeping the signature.

- `build_world(req: SimulateRequest, rng: SeededRNG) -> World`  → `personas.py` (BE-Twin)
- `generate_events(world: World, branch: str, rng: SeededRNG) -> list[TimelineEvent]` → `events.py` (BE-Engine)
- `run_simulation(world, branch, events, rng) -> SimResult` → `simulation.py` (BE-Sim)
- `score_branch(sim: SimResult, values: ValueWeights) -> BranchScore` + `detect_forks(A, B)`,
  `credibility(...)`, `recommend(...)` → `scoring.py` (BE-Score)
- `SeededRNG` (deterministic; same seed ⇒ identical shared-event stream across A/B; exposes
  `shared_event_hash()`) → `rng.py` (BE-Engine). **`ALG-20/21` + `NFR-01` hinge on this.**

`World`, `Persona`, `TimelineEvent`, `Metric`, `ForkPoint`, `BranchScore`, `Credibility`,
`Recommendation`, `SimulateRequest`, `ValueWeights` are all Pydantic models in `schemas.py`, field-named
exactly per `docs/api-contract.md`.

## 6. Git / PR workflow for every build agent

1. You run on the **Mac runtime** (GitHub push auth is in the Mac keychain — `git credential fill` host
   github.com). Repo is **public** (`github.com/Xu-Shihao/Lynsea-simulator`); clone needs no auth, push does.
2. Work in your OWN scratch dir to avoid colliding with other agents' working copies:
   ```
   git clone https://github.com/Xu-Shihao/Lynsea-simulator ~/Desktop/claude_hackathon/_work/<your-slug>
   cd ~/Desktop/claude_hackathon/_work/<your-slug>
   git checkout feat/lynsea-mvp
   git checkout -b build/<your-slug>
   ```
3. Implement ONLY your owned files (§4). Run your module's tests / a local smoke run.
4. Commit; push `build/<your-slug>`; open a PR **into `feat/lynsea-mvp`** (NOT main) via the GitHub
   REST API using the token from `git credential fill` (no `gh` CLI on the box). PR body: list files,
   which acceptance IDs you satisfied, and how you verified.
5. Post a result comment on your issue and set it to `in_review`. Do NOT touch `.env`, the submodules,
   or files you don't own.

## 7. Build waves (dependency-ordered; orchestrator merges between waves)

- **Wave 1 — scaffolds (parallel, no shared files):**
  - `BE-Core` → full `backend/` skeleton with stubbed modules so the SSE contract runs end-to-end with
    placeholder data (`/api/health`, `/api/simulate` streaming all event types, `/api/run/{id}/seed-check`).
  - `FE-Console` → full `frontend/` skeleton: Decision Console + SSE hook + `lib/mockStream.ts`, renders
    against the contract using the mock. Design tokens from `docs/design/README.md`.
  - `QA` → acceptance harness in `backend/tests/` + `scripts/`: contract-shape checks, `NFR-01` seed
    reproducibility check, `E2E-1/2/5/6` drivers (run against the stubbed backend first).
- **Wave 2 — real implementations (parallel, each in its owned files, on top of merged Wave 1):**
  `BE-Twin`, `BE-Engine`, `BE-Sim`, `BE-Score`, `FE-Dashboard`, `FE-Insight`.
- **Wave 3 — integration & acceptance:** wire real modules, run QA gates, fix P0 reds, demo polish.

## 8. Definition of done (P0)

`backend` runs `uvicorn app.main:app`; `frontend` runs `next dev`; submitting a decision in the
Console streams two aligned timelines + 5 curves + ≥1 fork point + credibility card + probabilistic
recommendation; `seed-check` returns equal `shared_event_hash` for a repeated run (`NFR-01`); the P0
checklist in `plans/Lynsea-验收标准.md` §10 is green or has a recorded known-degradation.
</content>
</invoke>
