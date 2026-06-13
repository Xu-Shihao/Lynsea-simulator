# Lynsea — Decision Outcome Simulator

> One hard decision, two side-by-side parallel futures. Lynsea is a
> **fixed-seed paired-counterfactual decision simulator**: it turns a single
> tough choice and its two options into two month-by-month timelines that differ
> *only* by the decision — phrased as probabilities, never prophecy.

---

## What Lynsea is

You describe a decision (e.g. *"Should I take the higher-paying but high-stress
job?"*), its two options, and the people it affects. Lynsea then:

1. Builds **digital-twin personas** of you and the people around you from minimal
   input (Big Five traits, stance, concerns — inferred, never hand-entered).
2. Runs a **fixed-seed paired counterfactual** simulation: both branches share a
   **byte-identical exogenous event backbone** (rent rises, a friend moves
   abroad, flu season, a relative's wedding…) so the only thing that differs
   between the two futures is the decision itself.
3. Streams back, in real time: two aligned timelines, five metric curves
   (economic, career, relationship, mental, autonomy — each 0–100), the key
   **branch points** where the futures diverge with a cause chain, and a
   **credibility card** plus a value-weighted recommendation.

### The differentiator — a controlled experiment, not two stories

Most "what-if" tools generate two unrelated narratives. Lynsea makes the two
branches a *controlled experiment*:

- **Same seed → same world.** The shared random life events are drawn by a
  seeded RNG (`random.Random(seed)`), **no LLM involved**, and emitted with
  identical `shared_event_id`, `month`, `title`, and `description` into *both*
  branches. Run the same decision + seed twice and the shared event stream is
  hash-equal (reproducibility, NFR-01 / ALG-20).
- **Personas built once, then forked.** The pre-decision state is identical for
  both branches; divergence comes only from the choice and its causal downstream
  (state-fork control, M-c).
- **Probabilities, not prophecy.** Recommendations are phrased probabilistically
  with a credibility card; high-risk results (relationship break-up, financial
  or mental-health decline) surface a "this is a simulation, not a prophecy"
  banner and a "how to change this outcome" hint (SYS-15 / SYS-16).

The authoritative technical contract for all of this is
[`BUILD_PLAN.md`](./BUILD_PLAN.md) section 4.

---

## Repository layout

```
Lynsea-simulator-cc/
├─ README.md                  ← you are here (product + how to run)
├─ BUILD_PLAN.md              ← authoritative API + data contract (English)
├─ demo.sh                    ← runnable P0 end-to-end demo (see "Demo" below)
├─ backend/                   ← FastAPI engine + API (Python)
│  ├─ app/
│  │  ├─ main.py              ← FastAPI app entrypoint
│  │  ├─ contracts.py         ← Pydantic data models (single source of truth)
│  │  ├─ config.py            ← Claude client + .env loading (do not reinvent)
│  │  ├─ api/                 ← routes + SSE + in-memory store
│  │  └─ engine/              ← the simulation core (the differentiator)
│  │     ├─ personas.py       ← build user + social-circle twins
│  │     ├─ backbone.py       ← SEEDED-RNG shared exogenous backbone (no LLM)
│  │     ├─ simulate.py       ← per-branch events + plausibility guard
│  │     ├─ scoring.py        ← 5-dim metrics 0–100 per month
│  │     ├─ branchpoints.py   ← divergence detection + cause chain
│  │     ├─ credibility.py    ← credibility card + value-weighted recommendation
│  │     └─ orchestrator.py   ← async run; both branches concurrent; SSE
│  ├─ tests/                  ← pytest (runs without a live key, uses stubs)
│  └─ requirements.txt
└─ frontend/                  ← Next.js (App Router) + TS + Tailwind + Recharts
   ├─ app/                    ← input page + results view
   ├─ components/             ← small-multiples timelines, metric curves,
   │                            branch points, credibility card, SafetyBanner
   └─ lib/                    ← API client, SSE consumer, sample fixture
```

- The `plans/` folder is the only Chinese content (product spec, deep research,
  acceptance criteria). Everything else is English.

---

## Architecture at a glance

```
Browser (Next.js + Recharts)
   │  POST /api/simulate              → { sim_id }
   │  GET  /api/simulate/{id}/stream  → SSE (events as generated)
   │  GET  /api/simulate/{id}         → full SimResult (reload)
   ▼
FastAPI (backend/app)
   ├─ api/      routes + SSE (sse-starlette), in-memory store, background task
   ├─ engine/   personas → seeded backbone → per-branch sim → scoring →
   │            branch points → credibility / recommendation
   └─ config.py Claude client + .env (CLAUDE_API_KEY, DEFAULT_MODEL)
```

The `POST` kicks off a background task that pushes events onto an
`asyncio.Queue`; `/stream` yields them as Server-Sent Events. **Skeleton events
stream first**, then perturbations and scoring fill in (BE-04 / FE-21). If the
Claude API is slow or unavailable, the engine **degrades gracefully to
deterministic stubs** — it still runs end to end, which is what makes the demo
and the tests reliable without a live key.

---

## Prerequisites

- **Python 3.9+** (backend)
- **Node.js 18+ and npm** (frontend)
- Optional: a Claude API key in the repo-root `.env`
  (`CLAUDE_API_KEY=...`, `DEFAULT_MODEL=claude-haiku-4-5-20251001`). Without it,
  the backend runs on deterministic stubs — fully demoable, just less narratively
  rich. **Never hardcode or log the key.**

---

## Setup & run (both servers together)

Lynsea is two processes: the backend on **port 8000** and the frontend on
**port 3000**. The frontend reads the backend base URL from
`NEXT_PUBLIC_API_BASE` (default `http://localhost:8000`).

### 1. Backend (port 8000)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000      # OpenAPI docs at /docs
```

Smoke test: `curl http://localhost:8000/health` → `{"status":"ok"}`.

### 2. Frontend (port 3000)

In a second terminal:

```bash
cd frontend
npm install
printf 'NEXT_PUBLIC_API_BASE=http://localhost:8000\n' > .env.local
npm run dev                                     # http://localhost:3000
```

Open <http://localhost:3000>, describe a decision and its two options, pick
**Quick** mode, and watch the two futures stream in.

### Or: one command for the full P0 demo

```bash
./demo.sh
```

This starts both servers, waits for them to be ready, runs the four P0
end-to-end scenarios against the live API, prints a pass/fail report (including
the BE-04 first-event timing), and tears everything down. See **Demo** below.

---

## Demo

[`demo.sh`](./demo.sh) exercises the four **P0** end-to-end scenarios from the
acceptance criteria (`plans/Lynsea-验收标准.md` section 8). It boots the backend
(and, unless `--no-frontend` is passed, the frontend), then drives the API:

| Scenario | What it checks | Acceptance IDs |
|----------|----------------|----------------|
| **E2E-1** Job decision, Quick mode | 2 timelines + 5 metric dims + ≥1 branch point + credibility card | SYS-12, ALG-40, FE-10/11/12 |
| **E2E-2** End a relationship (high-risk), Quick mode | Probabilistic phrasing, no deterministic "will/definitely", + "simulation, not a prophecy" guardrail | SYS-15/16, FE-24/25 |
| **E2E-5** Same decision + same seed, twice | Shared exogenous event stream is **hash-equal** across runs | ALG-20/21, NFR-01 |
| **E2E-6** Cold start, minimal input | Default-value personas flagged `is_default_inferred` + a "cold start / information limited" credibility note | ALG-04/05, FE-23 |

The script also records the **BE-04** timing target: the first skeleton
`timeline_event` should arrive within **≤ 20s** in Quick mode (relaxed
acceptance line; 10s is the stretch goal). It exits non-zero if any P0 scenario
fails.

Usage:

```bash
./demo.sh                 # backend + frontend, run all P0 scenarios
./demo.sh --no-frontend   # backend + scenarios only (skip npm/Next.js)
./demo.sh --keep          # leave servers running after the report
```

> Note: with a live Claude key in `.env`, a Quick run makes several real LLM
> calls and may take noticeably longer (and can hit the 45s per-call timeout
> before falling back to stubs). Without a key, runs are fast and deterministic.
> The demo waits accordingly.

---

## P0 acceptance summary

The MVP targets the **P0** rows of the acceptance criteria. The Demo-ready
checklist lives in [`plans/Lynsea-验收标准.md`](./plans/Lynsea-验收标准.md)
section 10 (Chinese; the IDs are what matter). Highlights:

- **SYS-11/12** — observable six-step loop; side-by-side timelines + metric
  curves + result score + branch points all appear.
- **SYS-15/16, FE-24/25, NFR-06** — probabilistic phrasing + high-risk guardrail
  ("simulation, not a prophecy" + "how to change this outcome").
- **SYS-17 / ALG-42, FE-22** — a credibility card ships with every result.
- **ALG-01/02/04** — minimal-input start; Big Five inferred from behaviour, not
  typed numbers; cold-start personas transparently flagged.
- **ALG-20/21, NFR-01** — fixed-seed paired counterfactual: shared random events
  are hash-equal across branches and across reruns; pre-fork state identical.
- **ALG-30/31/32** — skeleton + perturbation two-layer events; out-of-bounds
  rate ≤ 2%; incompatible events resampled ≤ 3× then downgraded and flagged.
- **ALG-40** — five-dimension scoring with every score linked to ≥ 1 supporting
  event.
- **BE-03/04** — branches run concurrently; streaming, skeleton-first.
- **BE-11/12** — only the `.env`-configured provider on the main path; graceful
  degradation on LLM failure.
- **FE-10/12/13, FE-21/23** — small-multiples aligned columns, highlighted
  branch points with evidence on click, progressive streaming, uncertainty
  markers.

Run `./demo.sh` for an automated pass/fail readout of the four P0 E2E scenarios.

---

## Tests

```bash
cd backend
.venv/bin/pytest tests -q
```

The backend tests monkeypatch the Claude client to force the deterministic stub
path, so they pass with **no live key, no network, and no tokens spent** —
covering reproducibility (NFR-01), shared-backbone identity across branches
(ALG-20), the plausibility guard (ALG-31/32), and supporting-event links
(ALG-40).

---

## Reference docs

- [`BUILD_PLAN.md`](./BUILD_PLAN.md) — **authoritative** API + data contract,
  architecture, and the fixed-seed paired-counterfactual algorithm (English).
- [`plans/Lynsea-验收标准.md`](./plans/Lynsea-验收标准.md) — acceptance criteria;
  the P0 Demo-ready checklist is in section 10, the E2E scenarios in section 8
  (Chinese).
- [`plans/Lynsea-计划.md`](./plans/Lynsea-计划.md) — product spec and core
  mechanisms (Chinese).
- [`plans/Deep-research.md`](./plans/Deep-research.md) — technical research and
  the B1–B6 bottlenecks (Chinese).
- [`backend/README.md`](./backend/README.md) — backend engine pipeline details.
- [`frontend/README.md`](./frontend/README.md) — frontend dev notes.
</content>
</invoke>
