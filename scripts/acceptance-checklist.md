# Lynsea P0 Acceptance Checklist

> Source of truth for P0 gates: `plans/Lynsea-验收标准.md §10`.
> Run each command; mark ✅ when it exits 0 (all PASS) or ❌ with notes.
> Backend must be running at `http://localhost:8000` for live-marked items.
> Mock-only items (marked `[MOCK]`) run without a server.

---

## Prerequisites

```bash
# Install Python dependencies
pip install pytest requests

# Start the backend (required for [LIVE] items)
uvicorn app.main:app --reload   # from backend/

# Run all mock (contract-shape) tests first
pytest backend/tests -q
```

---

## P0 Checklist

### SYS-02 — Mode time limits (≤10 min for Quick)

- **Verification**: Time the E2E-1 scenario end-to-end.
- **Command** `[LIVE]`:
  ```bash
  time python scripts/e2e.py --base http://localhost:8000
  ```
- **Pass threshold**: E2E-1 completes in ≤ 90 seconds (Quick mode SLA).
- [ ] ✅ / ❌

---

### SYS-11 — Six-step cycle observable

- **Verification**: Backend logs show each step (S1–S6) with start/end events and SSE stream delivers all required event types in order.
- **Command** `[MOCK]`:
  ```bash
  pytest backend/tests/test_contract_shape.py::TestContractShapeMock::test_event_ordering_run_started_first -v
  pytest backend/tests/test_contract_shape.py::TestContractShapeMock::test_event_ordering_done_last -v
  pytest backend/tests/test_contract_shape.py::TestContractShapeMock::test_world_ready_before_timeline_events -v
  ```
- **Pass threshold**: All 3 tests PASS.
- [ ] ✅ / ❌

---

### SYS-12 — Parallel timelines + metric curves + fork point + credibility card

- **Verification**: E2E-1 scenario delivers all 4 elements.
- **Command** `[MOCK]`:
  ```bash
  python scripts/e2e.py --mock
  ```
  Look for `E2E-1` overall PASS.
- **Command** `[LIVE]`:
  ```bash
  python scripts/e2e.py --base http://localhost:8000
  ```
- **Pass threshold**: E2E-1 overall PASS (all sub-checks green).
- [ ] ✅ / ❌

---

### SYS-15 / SYS-16 — Probabilistic copy + high-risk guardrails

- **Verification**: E2E-2 (relationship breakup) produces no deterministic language and includes guardrail.
- **Command** `[MOCK]`:
  ```bash
  pytest backend/tests/test_guardrails.py -v
  python scripts/e2e.py --mock  # check E2E-2
  ```
- **Command** `[LIVE]`:
  ```bash
  pytest backend/tests/test_guardrails.py -v --base http://localhost:8000
  python scripts/e2e.py --base http://localhost:8000  # check E2E-2
  ```
- **Pass threshold**: All guardrail tests PASS; E2E-2 overall PASS.
- [ ] ✅ / ❌

---

### SYS-17 — Credibility card with every result

- **Verification**: Every simulated run includes exactly 1 `credibility` event with `overall`, `breakdown.data_sufficiency`, `breakdown.causal_confidence`, `breakdown.event_plausibility`.
- **Command** `[MOCK]`:
  ```bash
  pytest backend/tests/test_contract_shape.py -k "credibility" -v
  ```
- **Pass threshold**: All credibility shape tests PASS.
- [ ] ✅ / ❌

---

### ALG-01 / ALG-02 / ALG-04 — Minimal info / Big-5 inferred / cold-start tagged

- **Verification**: E2E-6 cold-start produces personas tagged "信息有限/limited info".
- **Command** `[MOCK]`:
  ```bash
  python scripts/e2e.py --mock  # check E2E-6
  pytest backend/tests/test_contract_shape.py::TestContractShapeMock::test_cold_start_stream_structural_contract -v
  ```
- **Pass threshold**: E2E-6 overall PASS; at least 1 persona with `confidence: low`; "信息有限" annotation found in output.
- [ ] ✅ / ❌

---

### ALG-20 / ALG-21 — Paired counterfactual seed: shared event hash equal, pre-fork state consistent

- **Verification**: Two runs with same seed produce equal `shared_event_hash` from `GET /api/run/{id}/seed-check`.
- **Command** `[MOCK]`:
  ```bash
  pytest backend/tests/test_nfr01_seed.py -v
  python scripts/e2e.py --mock  # check E2E-5
  ```
- **Command** `[LIVE]`:
  ```bash
  pytest backend/tests/test_nfr01_seed.py -v --base http://localhost:8000
  python scripts/e2e.py --base http://localhost:8000  # check E2E-5
  ```
- **Pass threshold**: All NFR-01/ALG-20 tests PASS; E2E-5 overall PASS.
- [ ] ✅ / ❌

---

### ALG-30 / ALG-31 / ALG-32 — Skeleton+perturbation events, plausibility, incompatibility handling

- **Verification**: All `timeline_event` events are labelled `skeleton` or `perturbation`; no extreme/incompatible events appear.
- **Command** `[MOCK]`:
  ```bash
  pytest backend/tests/test_contract_shape.py -k "timeline" -v
  ```
- **Pass threshold**: All timeline shape tests PASS; `kind` field is always `skeleton` or `perturbation`.
- [ ] ✅ / ❌

---

### ALG-40 — 5-dim metrics, each with ≥1 evidence_event_ids

- **Verification**: Every `metric` event has all 5 dims and non-empty `evidence_event_ids`.
- **Command** `[MOCK]`:
  ```bash
  pytest backend/tests/test_contract_shape.py -k "metric" -v
  ```
- **Pass threshold**: All metric shape tests PASS.
- [ ] ✅ / ❌

---

### BE-03 / BE-04 — Parallel branches + SSE streaming (skeleton first)

- **Verification**: Skeleton `timeline_event` events arrive before `perturbation` events; SSE stream starts within mode threshold.
- **Command** `[MOCK]`:
  ```bash
  pytest backend/tests/test_contract_shape.py::TestContractShapeMock::test_timeline_events_before_metrics -v
  pytest backend/tests/test_contract_shape.py::TestContractShapeMock::test_world_ready_before_timeline_events -v
  ```
- **Pass threshold**: Both tests PASS.
- [ ] ✅ / ❌

---

### BE-11 / BE-12 — LLM calls only via `.env` config + failure degradation

- **Verification**: Code scan confirms no hardcoded provider; retry/degradation logic present.
- **Command** (code inspection):
  ```bash
  grep -r "openai\|gpt-4\|hardcoded" backend/app/ || echo "No violations found"
  cat backend/app/llm.py  # verify: reads CLAUDE_API_KEY, DEFAULT_MODEL from env
  ```
- **Pass threshold**: No hardcoded providers; `llm.py` reads from `.env`; degradation logic present.
- [ ] ✅ / ❌

---

### FE-10 / FE-12 / FE-13 — Small Multiples, fork highlights, click-to-evidence

- **Verification**: Visual inspection + contract check that all required data is present for frontend rendering.
- **Command** `[MOCK]`:
  ```bash
  pytest backend/tests/test_contract_shape.py -v
  ```
- **Verification note**: Full visual check requires running `next dev` and manually verifying the UI. Contract checks confirm the backend data is structurally sufficient.
- [ ] ✅ / ❌ (contract-shape) / manual UI check pending

---

### FE-21 / FE-22 / FE-23 — Progressive reveal + credibility card + uncertainty labels

- **Verification**: Contract checks confirm data is present; UI visual verification required.
- **Command** `[MOCK]`:
  ```bash
  pytest backend/tests/test_contract_shape.py -k "credibility or world_ready" -v
  ```
- [ ] ✅ / ❌ (contract-shape) / manual UI check pending

---

### NFR-01 — Same seed → same result (reproducibility)

- **Verification**: Two identical runs produce equal `shared_event_hash`.
- **Command** `[MOCK]`:
  ```bash
  pytest backend/tests/test_nfr01_seed.py -v
  ```
- **Command** `[LIVE]`:
  ```bash
  pytest backend/tests/test_nfr01_seed.py -v --base http://localhost:8000
  ```
- **Pass threshold**: All NFR-01 seed tests PASS.
- [ ] ✅ / ❌

---

### E2E-1 / E2E-2 / E2E-5 / E2E-6 — Four P0 end-to-end scenarios

- **Command** `[MOCK]`:
  ```bash
  python scripts/e2e.py --mock
  ```
- **Command** `[LIVE]`:
  ```bash
  python scripts/e2e.py --base http://localhost:8000
  ```
- **Pass threshold**: All four scenarios (E2E-1, E2E-2, E2E-5, E2E-6) show `PASS`.
- [ ] ✅ / ❌

---

## Full Suite Commands

```bash
# Run all mock/contract tests (no backend required)
pytest backend/tests -q

# Run all tests with verbose output
pytest backend/tests -v

# Run E2E mock suite
python scripts/e2e.py --mock

# Run E2E against live backend
python scripts/e2e.py --base http://localhost:8000

# Run live-backend pytest suite
pytest backend/tests -v --base http://localhost:8000
```

---

## Known Degradations (to record here if any P0 item cannot be fully verified at demo time)

| ID | Gate | Degradation | Minimum viable line still met? |
|----|------|-------------|-------------------------------|
| (none yet) | | | |

---

*Last updated: auto-generated by Lynsea QA agent (LIN-48).*
