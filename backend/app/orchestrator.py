"""The 6-step state machine that drives ``POST /api/simulate``.

Steps (`SYS-11` — each observable via emitted events):

* **S1 clarify**  -> ``run_started`` + (optional) ``clarify``
* **S2 world**    -> ``world_ready``           (``build_world``)
* **S3 twins**    -> personas inside ``world_ready``
* **S4 events + counterfactual** -> ``timeline_event`` (skeleton first, then
  perturbation — `BE-04`) + ``metric``, with branches A & B run **in parallel**
  (`BE-03`) over a shared seeded RNG (`ALG-20/21`, `NFR-01`).
* **S5 analysis** -> ``fork_point`` + ``branch_score`` + ``credibility`` +
  ``recommendation``
* **S6**          -> ``done`` (what-if entry point lives in ``main.py``)

Wave 1 ships **stub implementations** of every §5 interface here so the full
stream is complete and well-formed with placeholder data. When a Wave-2
specialist lands their module (``rng.py``, ``personas.py``, ``events.py``,
``simulation.py``, ``scoring.py``) the orchestrator auto-binds the real
implementation (see "Wave-2 wiring" below) — no edit to this file required.

All natural-language result text uses **probabilistic** phrasing (`SYS-15`).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import random
import uuid
from typing import AsyncIterator, Callable

from app.schemas import (
    DIMENSIONS,
    BranchScore,
    ClarifyData,
    ClarifyQuestion,
    Credibility,
    CredibilityBreakdown,
    Dimension,
    DoneData,
    ErrorData,
    ForkPoint,
    Metric,
    OptionsData,
    Persona,
    Recommendation,
    RunStartedData,
    SimResult,
    SimulateRequest,
    TimelineEvent,
    ValueWeights,
    WhatIfRequest,
    World,
    WorldReadyData,
)
from app.sse import sse_bytes

logger = logging.getLogger("lynsea.orchestrator")

# horizon (months) per mode — P0 target = quick (6 months).
MODE_HORIZON: dict[str, int] = {"quick": 6, "medium": 18, "heavy": 24}

# High-risk decision keywords -> always surface the "simulation, not prophecy"
# guardrail (SYS-16). Lower-cased substring match on the decision text.
_HIGH_RISK_TERMS = (
    "quit", "resign", "divorce", "break up", "breakup", "split",
    "relationship", "marriage", "marry", "health", "sick", "loan",
    "debt", "mortgage", "bankrupt", "invest", "savings", "move abroad",
    "辞职", "分手", "离婚", "结婚", "搬家", "投资", "创业", "贷款",
)


# --------------------------------------------------------------------------- #
# In-memory run store (for GET /api/run/{run_id}/seed-check)
# --------------------------------------------------------------------------- #
RUNS: dict[str, dict[str, object]] = {}


def get_seed_check(run_id: str) -> dict[str, str] | None:
    """Return ``{"shared_event_hash": ...}`` for a run, or ``None`` if unknown."""
    state = RUNS.get(run_id)
    if state is None:
        return None
    return {"shared_event_hash": str(state["shared_event_hash"])}


# --------------------------------------------------------------------------- #
# Stub SeededRNG (Wave 1 placeholder for rng.py / BE-Engine)
# --------------------------------------------------------------------------- #
class StubSeededRNG:
    """Deterministic RNG with a seed-only **shared** stream.

    ``shared_event_hash()`` depends solely on the seed, so the same seed (and
    therefore the same shared, non-decision event stream) reproduces across
    runs and is identical across branches A and B (`ALG-20`, `NFR-01`). Branch-
    specific draws use :meth:`branch_rng`, which differs per branch.
    """

    def __init__(self, seed: int) -> None:
        self.seed = int(seed)
        self._shared = random.Random(self.seed)

    def random(self) -> float:
        return self._shared.random()

    def randint(self, a: int, b: int) -> int:
        return self._shared.randint(a, b)

    def choice(self, seq: list):  # type: ignore[type-arg]
        return self._shared.choice(seq)

    def branch_rng(self, branch: str) -> "StubSeededRNG":
        salt = sum(ord(c) for c in branch) * 2654435761
        return StubSeededRNG((self.seed ^ salt) & 0xFFFFFFFF)

    def shared_event_hash(self) -> str:
        r = random.Random(self.seed)
        tokens = [round(r.random(), 6) for _ in range(24)]
        return hashlib.sha256(json.dumps(tokens).encode()).hexdigest()[:16]


# --------------------------------------------------------------------------- #
# Stub interface implementations (Wave 1 placeholders)
# --------------------------------------------------------------------------- #
def _stub_build_world(req: SimulateRequest, rng: StubSeededRNG) -> World:
    """Placeholder digital-twin world. Real impl: personas.py (BE-Twin)."""
    # Option labels: use provided options, else infer two generic branches.
    if req.options and len(req.options) >= 2:
        opt_a, opt_b = req.options[0], req.options[1]
    else:
        opt_a = "Keep things as they are"
        opt_b = "Make the change"

    personas: list[Persona] = []

    # The decision-maker ("self") — confidence depends on whether a profile
    # was supplied (cold-start flagging, ALG-04).
    has_profile = req.profile is not None
    personas.append(
        Persona(
            id="self",
            role="you",
            influence_weight=10,
            confidence="high" if has_profile else "low",
            stance_on_decision="considering",
            key_concerns=(req.profile.core_values if req.profile else []) or [],
            big_five=_stub_big_five(rng),
            cold_start=not has_profile,
        )
    )

    # Social circle -> personas. A member with a stated stance is high-
    # confidence; otherwise it is a cold-start default (flagged "信息有限").
    for i, member in enumerate(req.social_circle[:4]):
        personas.append(
            Persona(
                id=f"{_slug(member.role)}-{i+1}",
                role=member.role,
                influence_weight=member.influence_weight,
                confidence="high" if member.stance_on_decision else "low",
                stance_on_decision=member.stance_on_decision,
                key_concerns=member.key_concerns,
                big_five=_stub_big_five(rng),
                cold_start=member.stance_on_decision is None,
            )
        )

    # Pad to a 3-persona minimum with population-default (cold-start) roles,
    # skipping any role already supplied via the social circle.
    existing_roles = {p.role.lower() for p in personas}
    for role in ("partner", "close friend", "mentor"):
        if len(personas) >= 3:
            break
        if role.lower() in existing_roles:
            continue
        existing_roles.add(role.lower())
        personas.append(
            Persona(
                id=_slug(role),
                role=role,
                influence_weight=5,
                confidence="low",
                key_concerns=[],
                big_five=_stub_big_five(rng),
                cold_start=True,
            )
        )

    return World(
        run_id="",  # set by the orchestrator after the handshake
        decision=req.decision,
        mode=req.mode,
        seed=rng.seed,
        options={"A": opt_a, "B": opt_b},
        personas=personas[:5],
        values=_value_weights(req),
    )


def _stub_generate_events(
    world: World, branch: str, rng: StubSeededRNG
) -> list[TimelineEvent]:
    """Placeholder skeleton+perturbation events. Real impl: events.py (BE-Engine)."""
    horizon = MODE_HORIZON.get(world.mode, 6)
    brng = rng.branch_rng(branch)
    label = world.options.get(branch, branch)
    persona_ids = [p.id for p in world.personas] or ["self"]

    events: list[TimelineEvent] = []
    counters: dict[int, int] = {}

    def _next_id(month: int) -> str:
        counters[month] = counters.get(month, 0) + 1
        return f"{branch}-m{month}-{counters[month]}"

    # Skeleton (high-probability, decision-driven milestones) — `ALG-30`.
    skeleton_months = sorted(set([1] + list(range(2, horizon + 1, 2)) + [horizon]))
    for month in skeleton_months:
        events.append(
            TimelineEvent(
                branch=branch,  # type: ignore[arg-type]
                event_id=_next_id(month),
                month=month,
                kind="skeleton",
                title=f"Month {month}: settling into '{label}'",
                detail=(
                    "A likely milestone implied by the decision and the "
                    "personas' baseline trajectory."
                ),
                personas=persona_ids[:2],
            )
        )

    # Perturbation (low-probability, occasional) — branch-specific draws.
    n_pert = 1 + (brng.randint(0, 1))
    pert_months = sorted({brng.randint(2, horizon) for _ in range(n_pert + 1)})[:n_pert]
    for month in pert_months:
        who = persona_ids[brng.randint(0, len(persona_ids) - 1)]
        events.append(
            TimelineEvent(
                branch=branch,  # type: ignore[arg-type]
                event_id=_next_id(month),
                month=month,
                kind="perturbation",
                title=f"Month {month}: an unexpected turn",
                detail=(
                    "A lower-probability event that could plausibly arise; "
                    "shown to stress-test the trajectory."
                ),
                personas=[who],
            )
        )

    return events


def _stub_run_simulation(
    world: World, branch: str, events: list[TimelineEvent], rng: StubSeededRNG
) -> SimResult:
    """Placeholder 5-dim metric curves. Real impl: simulation.py (BE-Sim)."""
    horizon = MODE_HORIZON.get(world.mode, 6)
    brng = rng.branch_rng(branch)
    metrics: list[Metric] = []

    for month in range(1, horizon + 1):
        f = month / horizon
        evidence = _evidence_for(events, month)
        for dim in DIMENSIONS:
            base = _dim_base(branch, dim, f)
            noise = (brng.random() - 0.5) * 8.0
            score = max(0.0, min(100.0, round(base + noise, 1)))
            metrics.append(
                Metric(
                    branch=branch,  # type: ignore[arg-type]
                    month=month,
                    dim=dim,
                    score=score,
                    evidence_event_ids=evidence,
                )
            )

    return SimResult(branch=branch, events=events, metrics=metrics)  # type: ignore[arg-type]


def _stub_detect_forks(a: SimResult, b: SimResult) -> list[ForkPoint]:
    """Placeholder fork detection. Real impl: scoring.py (BE-Score)."""
    a_map = _metric_map(a)
    b_map = _metric_map(b)
    months = sorted({m for (m, _d) in a_map} & {m for (m, _d) in b_map})
    if not months:
        return []

    best_month, best_div, best_dims = months[0], -1.0, []
    for month in months:
        diffs = {
            dim: abs(a_map.get((month, dim), 0) - b_map.get((month, dim), 0))
            for dim in DIMENSIONS
        }
        total = sum(diffs.values())
        if total > best_div:
            best_div = total
            best_month = month
            best_dims = [d for d, _ in sorted(diffs.items(), key=lambda kv: -kv[1])[:2]]

    magnitude = max(0.0, min(100.0, round(best_div / len(DIMENSIONS), 1)))
    return [
        ForkPoint(
            month=best_month,
            magnitude=magnitude,
            title=f"Paths diverge most around month {best_month}",
            explanation=(
                "Around this point the two branches likely pull apart the most — "
                f"roughly a {int(magnitude)}-point average gap across "
                f"{', '.join(best_dims) or 'several dimensions'}. The split is "
                "driven by the decision variable, not by chance events."
            ),
            dims=best_dims,  # type: ignore[arg-type]
        )
    ]


def _stub_score_branch(sim: SimResult, values: ValueWeights) -> BranchScore:
    """Placeholder value-weighted scoring. Real impl: scoring.py (BE-Score)."""
    # Use the mean of the last two months per dimension as the "outcome".
    by_dim: dict[str, list[float]] = {d: [] for d in DIMENSIONS}
    if sim.metrics:
        last_month = max(m.month for m in sim.metrics)
        window = {last_month, last_month - 1}
        for m in sim.metrics:
            if m.month in window:
                by_dim[m.dim].append(m.score)

    breakdown: dict[str, float] = {}
    for dim in DIMENSIONS:
        vals = by_dim[dim]
        breakdown[dim] = round(sum(vals) / len(vals), 1) if vals else 50.0

    weights = values.normalized()
    total = round(sum(breakdown[d] * weights[d] for d in DIMENSIONS), 1)
    return BranchScore(branch=sim.branch, total=total, breakdown=breakdown, weighted=True)


def _stub_credibility(world: World, sims: list[SimResult]) -> Credibility:
    """Placeholder credibility card. Real impl: scoring.py (BE-Score)."""
    n = len(world.personas) or 1
    high = sum(1 for p in world.personas if p.confidence == "high")
    data_sufficiency = int(35 + 55 * (high / n))
    # Quick mode skips formal SCM (ALG-22) -> moderate causal confidence.
    causal_confidence = 58
    event_plausibility = 82  # events are whitelist-constrained (ALG-31)
    overall = int(
        0.4 * data_sufficiency + 0.35 * causal_confidence + 0.25 * event_plausibility
    )
    notes = (
        f"Overall confidence is around {overall}%. Treat these trajectories as "
        "directional rather than predictive — quick mode constrains events with "
        "prompts instead of a full causal model, and "
        f"{n - high} of {n} personas rely on population defaults (information "
        "limited, for reference only)."
    )
    return Credibility(
        overall=overall,
        breakdown=CredibilityBreakdown(
            data_sufficiency=data_sufficiency,
            causal_confidence=causal_confidence,
            event_plausibility=event_plausibility,
        ),
        notes=notes,
    )


def _stub_recommend(
    world: World,
    scores: list[BranchScore],
    forks: list[ForkPoint],
    cred: Credibility,
) -> Recommendation:
    """Placeholder probabilistic recommendation. Real impl: scoring.py (BE-Score)."""
    by_branch = {s.branch: s for s in scores}
    a = by_branch.get("A")
    b = by_branch.get("B")
    a_total = a.total if a else 50.0
    b_total = b.total if b else 50.0
    diff = b_total - a_total

    if abs(diff) < 5:
        leaning = "neither"
    elif diff > 0:
        leaning = "B"
    else:
        leaning = "A"

    # Map the score gap to a soft probability (never deterministic — SYS-15).
    lean_pct = int(min(85, 50 + abs(diff) * 1.5))
    label = world.options.get(leaning, leaning) if leaning != "neither" else "neither"

    if leaning == "neither":
        rationale = (
            f"Weighted against your values, the two paths look close — around "
            f"{a_total:.0f}/100 vs {b_total:.0f}/100. Neither option is clearly "
            "better; the choice likely comes down to which trade-offs you can "
            "live with."
        )
    else:
        rationale = (
            f"Weighted against your values, '{label}' is likely the stronger "
            f"path — around {max(a_total, b_total):.0f}/100 vs "
            f"{min(a_total, b_total):.0f}/100, roughly a {lean_pct}% lean. This "
            "is a probabilistic read, not a certainty."
        )

    guardrail = (
        "This is a simulation, not a prophecy. The trajectories shown are "
        "probabilistic and could change. You can change this outcome — try "
        "adjusting an assumption (a key relationship, your risk tolerance, or "
        "timing) and re-running to see how the branches shift."
    )
    if _is_high_risk(world.decision):
        guardrail = (
            "⚠ This looks like a high-stakes decision. " + guardrail
        )

    return Recommendation(leaning=leaning, rationale=rationale, guardrail=guardrail)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Stub helpers
# --------------------------------------------------------------------------- #
def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.strip().lower()).strip("-") or "x"


def _stub_big_five(rng: StubSeededRNG) -> dict[str, float]:
    return {
        "openness": round(rng.random(), 2),
        "conscientiousness": round(rng.random(), 2),
        "extraversion": round(rng.random(), 2),
        "agreeableness": round(rng.random(), 2),
        "neuroticism": round(rng.random(), 2),
    }


def _dim_base(branch: str, dim: Dimension, f: float) -> float:
    """Deterministic baseline trajectory by branch + dimension + time fraction.

    Branch B is treated as the "change / leap" path (career & economics climb,
    relationships strain, mental health dips then partly recovers, autonomy
    rises); branch A is the stable status-quo path. This produces a clear,
    comparable fork for the demo (`E2E-1`: pay vs. wellbeing trade-off).
    """
    if branch == "B":
        table = {
            "economic": 45 + 35 * f,
            "career": 50 + 42 * f,
            "relationships": 62 - 22 * f,
            "mental_health": 58 - 28 * f + 18 * (f**2),
            "autonomy": 55 + 35 * f,
        }
    else:
        table = {
            "economic": 58 + 6 * f,
            "career": 55 + 4 * f,
            "relationships": 64 + 4 * f,
            "mental_health": 62 + 3 * math.sin(math.pi * f),
            "autonomy": 50 - 2 * f,
        }
    return table[dim]


def _evidence_for(events: list[TimelineEvent], month: int) -> list[str]:
    """At least one supporting event id for a metric (`ALG-40`)."""
    same = [e.event_id for e in events if e.month == month]
    if same:
        return same[:2]
    prior = [e for e in events if e.month <= month]
    if prior:
        return [max(prior, key=lambda e: e.month).event_id]
    if events:
        return [min(events, key=lambda e: e.month).event_id]
    return []


def _metric_map(sim: SimResult) -> dict[tuple[int, str], float]:
    return {(m.month, m.dim): m.score for m in sim.metrics}


def _value_weights(req: SimulateRequest) -> ValueWeights:
    """Derive per-dimension weights from the profile's core values (`M-d`)."""
    vw = ValueWeights()
    mapping = {
        "growth": "career", "career": "career", "ambition": "career",
        "stability": "economic", "money": "economic", "income": "economic",
        "financial": "economic", "wealth": "economic", "security": "economic",
        "family": "relationships", "relationship": "relationships",
        "relationships": "relationships", "love": "relationships",
        "friends": "relationships", "community": "relationships",
        "health": "mental_health", "wellbeing": "mental_health",
        "well-being": "mental_health", "balance": "mental_health",
        "peace": "mental_health", "happiness": "mental_health",
        "freedom": "autonomy", "independence": "autonomy", "autonomy": "autonomy",
    }
    if req.profile and req.profile.core_values:
        for value in req.profile.core_values:
            dim = mapping.get(value.strip().lower())
            if dim:
                setattr(vw, dim, getattr(vw, dim) + 1.5)
    return vw


def _is_high_risk(decision: str) -> bool:
    low = decision.lower()
    return any(term in low for term in _HIGH_RISK_TERMS)


# --------------------------------------------------------------------------- #
# Wave-2 wiring: bind the real implementation if its module exists, else stub.
# Specialists just create their module with the §5 signature — no edit here.
# --------------------------------------------------------------------------- #
def _bind(real_path: str, attr: str, stub: Callable) -> Callable:
    try:
        module = __import__(real_path, fromlist=[attr])
        impl = getattr(module, attr)
        logger.info("orchestrator: using real %s.%s", real_path, attr)
        return impl
    except Exception:  # ImportError or missing attr -> use the Wave-1 stub
        logger.info("orchestrator: using stub for %s.%s", real_path, attr)
        return stub


def _make_rng(seed: int):
    try:
        from app.rng import SeededRNG as _RealRNG  # type: ignore

        return _RealRNG(seed)
    except Exception:
        return StubSeededRNG(seed)


build_world = _bind("app.personas", "build_world", _stub_build_world)
generate_events = _bind("app.events", "generate_events", _stub_generate_events)
run_simulation = _bind("app.simulation", "run_simulation", _stub_run_simulation)
score_branch = _bind("app.scoring", "score_branch", _stub_score_branch)
detect_forks = _bind("app.scoring", "detect_forks", _stub_detect_forks)
credibility = _bind("app.scoring", "credibility", _stub_credibility)
recommend = _bind("app.scoring", "recommend", _stub_recommend)


# --------------------------------------------------------------------------- #
# Async helpers
# --------------------------------------------------------------------------- #
async def _maybe_async(fn: Callable, *args):
    """Run a §5 impl, supporting both sync stubs and async specialist impls.

    Sync impls run in a worker thread so the two branches genuinely overlap
    (`BE-03`); async impls are awaited directly.
    """
    if asyncio.iscoroutinefunction(fn):
        return await fn(*args)
    return await asyncio.to_thread(fn, *args)


def _ordered(
    events_a: list[TimelineEvent], events_b: list[TimelineEvent], kind: str
) -> list[TimelineEvent]:
    a = sorted((e for e in events_a if e.kind == kind), key=lambda e: e.month)
    b = sorted((e for e in events_b if e.kind == kind), key=lambda e: e.month)
    return a + b


# --------------------------------------------------------------------------- #
# /api/simulate driver
# --------------------------------------------------------------------------- #
async def simulate_stream(req: SimulateRequest) -> AsyncIterator[bytes]:
    """Run the 6-step machine and yield SSE-framed bytes for the whole contract."""
    run_id = str(uuid.uuid4())
    seed = _derive_seed(req)
    rng = _make_rng(seed)
    shared_hash = rng.shared_event_hash()
    RUNS[run_id] = {"seed": seed, "shared_event_hash": shared_hash}

    try:
        # --- S1: handshake + clarify -------------------------------------- #
        yield sse_bytes(
            "run_started",
            RunStartedData(run_id=run_id, mode=req.mode, branches=["A", "B"]),
        )
        # MVP proceeds with defaults; emit a non-blocking clarify so the step
        # is observable (SYS-11) and the frontend can optionally render it.
        yield sse_bytes(
            "clarify",
            ClarifyData(
                needs_answer=False,
                questions=[
                    ClarifyQuestion(
                        id="q-options",
                        text="Proceeding with two inferred options; you can refine them.",
                    )
                ],
            ),
        )

        # --- S2/S3: world + twins ----------------------------------------- #
        world: World = await _maybe_async(build_world, req, rng)
        world.run_id = run_id
        yield sse_bytes(
            "world_ready",
            WorldReadyData(
                personas=[p.public() for p in world.personas],
                options=OptionsData(
                    A=world.options.get("A", "Option A"),
                    B=world.options.get("B", "Option B"),
                ),
            ),
        )

        # --- S4: events (branches in parallel) ---------------------------- #
        events_a, events_b = await asyncio.gather(
            _maybe_async(generate_events, world, "A", rng),
            _maybe_async(generate_events, world, "B", rng),
        )
        # Skeleton events first, then perturbations (BE-04 streaming order).
        for ev in _ordered(events_a, events_b, "skeleton"):
            yield sse_bytes("timeline_event", ev)
        for ev in _ordered(events_a, events_b, "perturbation"):
            yield sse_bytes("timeline_event", ev)

        # --- S4: counterfactual simulation (branches in parallel) --------- #
        sim_a, sim_b = await asyncio.gather(
            _maybe_async(run_simulation, world, "A", events_a, rng),
            _maybe_async(run_simulation, world, "B", events_b, rng),
        )
        for metric in sim_a.metrics:
            yield sse_bytes("metric", metric)
        for metric in sim_b.metrics:
            yield sse_bytes("metric", metric)

        # --- S5: analysis ------------------------------------------------- #
        forks = await _maybe_async(detect_forks, sim_a, sim_b)
        for fork in forks:
            yield sse_bytes("fork_point", fork)

        score_a, score_b = await asyncio.gather(
            _maybe_async(score_branch, sim_a, world.values),
            _maybe_async(score_branch, sim_b, world.values),
        )
        yield sse_bytes("branch_score", score_a)
        yield sse_bytes("branch_score", score_b)

        cred = await _maybe_async(credibility, world, [sim_a, sim_b])
        yield sse_bytes("credibility", cred)

        rec = await _maybe_async(recommend, world, [score_a, score_b], forks, cred)
        yield sse_bytes("recommendation", rec)

        # --- S6: done ----------------------------------------------------- #
        yield sse_bytes("done", DoneData(run_id=run_id))

    except Exception as exc:  # graceful degrade — readable error, no white screen
        logger.exception("simulate_stream failed for run %s: %s", run_id, exc)
        yield sse_bytes(
            "error",
            ErrorData(
                message=f"The simulation hit an unexpected error and stopped: {exc}",
                recoverable=False,
            ),
        )
        yield sse_bytes("done", DoneData(run_id=run_id))


async def whatif_stream(req: WhatIfRequest) -> AsyncIterator[bytes]:
    """`POST /api/whatif` — P1. Wave 1 returns a readable, recoverable error.

    Kept SSE-shaped (error -> done) so the frontend's stream reader handles it
    cleanly instead of white-screening (`FE-29`).
    """
    yield sse_bytes(
        "error",
        ErrorData(
            message=(
                "What-if branching (branch C) is planned for V1.0 and is not "
                "available yet."
            ),
            recoverable=True,
        ),
    )
    yield sse_bytes("done", DoneData(run_id=req.run_id))


def _derive_seed(req: SimulateRequest) -> int:
    """Use the explicit seed, else derive one deterministically from the request.

    Deterministic-by-default means identical inputs reproduce (`NFR-01`) even
    when the caller omits ``seed``.
    """
    if req.seed is not None:
        return int(req.seed)
    canonical = req.model_dump(exclude={"seed"})
    blob = json.dumps(canonical, sort_keys=True, ensure_ascii=False, default=str)
    return int(hashlib.sha256(blob.encode()).hexdigest()[:12], 16)
