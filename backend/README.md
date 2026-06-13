# Lynsea backend

Decision-outcome simulator: turns ONE hard decision + 2 options into TWO
side-by-side parallel futures via a fixed-seed paired counterfactual. Both
branches share a byte-identical exogenous backbone and differ ONLY by the
decision, so any divergence is attributable to the choice.

## Run

From inside `backend/`:

```bash
.venv/bin/uvicorn app.main:app --port 8000
```

(`uvicorn app.main:app` must be launched from the `backend/` directory.)

Optional Claude inference reads `CLAUDE_API_KEY` / `DEFAULT_MODEL` from the
repo-root `.env` (handled by `app/config.py`). With no key, the engine degrades
gracefully to deterministic stubs — it still runs end to end.

## API (frozen contract)

- `POST /api/simulate` — body = `SimRequest` -> `{"sim_id": "<uuid>"}`. Starts a
  background asyncio task that fills the stream queue and stores the result.
- `GET /api/simulate/{sim_id}/stream` — Server-Sent Events. Event types:
  `status, persona, timeline_event, metric, branch_point, credibility,
  recommendation, done, error`. Each message data is a JSON string. The stream
  replays already-emitted history, so late subscribers still get everything.
- `GET /api/simulate/{sim_id}` — full `SimResult` JSON (404 unknown id; 425 if
  the background task has not finished yet).
- `GET /health` — liveness probe.

## Engine pipeline (`app/engine/`)

1. `common.py` — deterministic seed (explicit `seed`, else sha256 of decision),
   mode->horizon (quick=6, medium=18, heavy=24), slugs, clamp.
2. `personas.py` — user ("You", `p_user`) + one twin per affected person. Big5 /
   stance / traits inferred from text via Claude; cold-start population defaults
   (`is_default_inferred=True`) when the LLM is unavailable. Stable ids.
3. `backbone.py` — seeded RNG draws decision-INDEPENDENT life events from a
   curated pool. No LLM. Emitted identically into both branches.
4. `simulate.py` — two-layer (skeleton + perturbation) decision-dependent events
   (LLM or deterministic stub), then merges the shared backbone. Plausibility
   guard rejects out-of-bounds events, resamples <=3x, else downgrades + flags.
5. `scoring.py` — 5 metrics (0-100) per branch per month; every `MetricPoint`
   references >=1 supporting event id.
6. `branchpoints.py` — months of peak |A-B| divergence + dominant dim + cause chain.
7. `credibility.py` — credibility card + value-weighted, probabilistic
   recommendation (never "will"/"definitely"; adds a "simulation, not a
   prophecy" caveat on high-risk declines).
8. `orchestrator.py` — async run; branches generated concurrently; emits the
   stream and assembles the full `SimResult`.

## Tests

```bash
.venv/bin/pytest tests -q
```

Tests monkeypatch `config.complete*` to `None`, forcing the deterministic stub
path — no live key, no network, no tokens spent.
