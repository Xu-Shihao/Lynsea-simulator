# Lynsea API Contract (v0.1 — MVP)

> **This is the integration contract between backend and frontend.** Both sides build against it in parallel.
> Backend implements these endpoints; frontend consumes them. Do **not** change event names / field names without updating this file and notifying the orchestrator.
>
> Acceptance criteria this contract serves: see `plans/Lynsea-验收标准.md` (IDs `SYS-*`, `BE-*`, `FE-*`, `ALG-*`).

## Base

- Backend dev server: `http://localhost:8000`
- Frontend dev server: `http://localhost:3000`
- All bodies are JSON (`Content-Type: application/json`).
- CORS: backend allows `http://localhost:3000`.
- Metric dimensions (fixed, 5): `economic`, `career`, `relationships`, `mental_health`, `autonomy`. Each scored `0–100`.
- Branches: MVP runs exactly **2** options/branches, labelled `A` and `B`.
- Modes: `quick` (6mo, 2 branches, 3–5 personas), `medium` (12–24mo), `heavy` (>=24mo, distributions). MVP target = `quick`.

---

## 1. `GET /api/health`
Returns `{ "status": "ok", "version": "0.1.0" }`. Used for readiness checks.

## 2. `POST /api/simulate` → **SSE stream**

Kicks off a simulation and streams progress as Server-Sent Events. The frontend renders skeleton events first, then fills in.

**Request body**
```json
{
  "decision": "Should I quit my stable job to join an early-stage startup?",
  "mode": "quick",
  "options": ["Stay at current job", "Join the startup"],
  "profile": {
    "age": 29, "city": "Shanghai", "occupation": "Backend engineer",
    "risk_tolerance": 6, "core_values": ["growth", "stability", "family"],
    "decision_style": "analytical"
  },
  "social_circle": [
    { "role": "partner", "influence_weight": 8, "stance_on_decision": "opposed", "key_concerns": ["stability", "income"] },
    { "role": "mother", "influence_weight": 6, "stance_on_decision": "opposed" }
  ]
}
```
`options`, `profile`, `social_circle` are optional. If `options` is omitted the backend infers two options from `decision`. If `profile`/`social_circle` is sparse the backend uses defaults and marks affected personas as low-confidence.

**Response**: `Content-Type: text/event-stream`. Each event has an `event:` type and a JSON `data:` payload. Event types, in typical order:

| `event:` | `data` payload | Meaning |
|----------|----------------|---------|
| `run_started` | `{ "run_id": str, "mode": str, "branches": ["A","B"] }` | Handshake; frontend creates 2 columns. |
| `clarify` *(optional)* | `{ "needs_answer": bool, "questions": [{ "id": str, "text": str }] }` | Backend wants more info. Frontend may show inline; MVP can skip and proceed with defaults. |
| `world_ready` | `{ "personas": [{ "id": str, "role": str, "influence_weight": int, "confidence": "high"\|"low" }], "options": { "A": str, "B": str } }` | Digital twins + branch labels ready. |
| `timeline_event` | `{ "branch": "A"\|"B", "event_id": str, "month": int, "kind": "skeleton"\|"perturbation", "title": str, "detail": str, "personas": [str] }` | One life event. `skeleton` stream first, `perturbation` fill in later. |
| `metric` | `{ "branch": "A"\|"B", "month": int, "dim": str, "score": 0-100, "evidence_event_ids": [str] }` | One datapoint for one dimension curve. Must reference ≥1 event (`ALG-40`). |
| `fork_point` | `{ "month": int, "magnitude": 0-100, "title": str, "explanation": str, "dims": [str] }` | Where the two branches diverge sharply. |
| `branch_score` | `{ "branch": "A"\|"B", "total": 0-100, "breakdown": { "<dim>": 0-100 }, "weighted": bool }` | Final per-branch score (value-weighted, `M-d`). |
| `credibility` | `{ "overall": 0-100, "breakdown": { "data_sufficiency": int, "causal_confidence": int, "event_plausibility": int }, "notes": str }` | Credibility card (`SYS-17`, `ALG-42`). |
| `recommendation` | `{ "leaning": "A"\|"B"\|"neither", "rationale": str, "guardrail": str }` | Probabilistic, never deterministic (`SYS-15`). `guardrail` shown for high-risk results. |
| `error` | `{ "message": str, "recoverable": bool }` | Something failed; frontend shows readable error, not white screen (`FE-29`). |
| `done` | `{ "run_id": str }` | Stream complete. |

**SSE framing** (exact bytes per event):
```
event: timeline_event
data: {"branch":"A","event_id":"a-m1-1","month":1,"kind":"skeleton","title":"...","detail":"...","personas":["partner"]}

```
(blank line terminates each event).

## 3. `POST /api/whatif` → **SSE stream**  *(P1, V1.0)*
Body: `{ "run_id": str, "from_month": int, "branch": "A"|"B", "change": "free-text what-if" }`.
Streams the same event types for a **new branch `C`** that forks from `from_month`. Frontend overlays it as a third coloured timeline (`FE-20`).

---

## Determinism / seed contract (`M-b`, `ALG-20`, `NFR-01`)
- `POST /api/simulate` accepts optional `"seed": int`. Same `seed` + same input ⇒ identical non-decision (shared) random events across branches A and B, and reproducible output.
- Backend exposes `GET /api/run/{run_id}/seed-check` → `{ "shared_event_hash": str }` so QA can assert branch A and B share the same random-event stream (differences only from the decision variable).

## Conventions
- IDs: `event_id` = `"{branch}-m{month}-{n}"`. `run_id` = uuid4 string.
- Times: `month` is an integer offset from 0 (decision point).
- All natural-language result text MUST be probabilistic ("likely", "around a 60% chance"), never "will"/"definitely" (`SYS-15`, `FE-25`).
