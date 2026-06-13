"""Simulation orchestration (BE-03 concurrent branches, BE-04 streaming).

run_simulation(req, emit) drives the full pipeline, calling emit(event_type,
payload) at each step so the API layer can stream Server-Sent Events, and returns
the fully-assembled SimResult for storage/reload.

Emit order:
  status(phase) -> persona(each) -> timeline_event(skeleton streamed per branch
  as soon as THAT branch returns, then perturbation, then shared exogenous in
  BOTH branches) -> metric(per branch per month) -> branch_point -> credibility
  -> recommendation -> done {sim_id}
On failure / timeout / cancel: error {message}. Never hangs silently.

The two branches are generated concurrently via asyncio.to_thread so total time
~= single-branch time even though the per-branch LLM calls are blocking. Their
skeleton events are streamed the moment each branch completes (BE-04 / FE-21),
not batched after both finish, and progress status updates are emitted as
branches land so the client never sees a stuck progress bar (NFR-02).

A whole-run timeout (config.mode_timeout + buffer) wraps the pipeline so a
hung LLM call can never strand the client (SYS-02); a cooperative cancel flag
lets the API stop a run on user request.
"""
from __future__ import annotations

import asyncio
import datetime
from typing import Awaitable, Callable, Dict, List, Optional, Tuple

from .. import config
from ..contracts import (
    Dimension,
    MetricPoint,
    Persona,
    SimRequest,
    SimResult,
    TimelineEvent,
)
from . import backbone as backbone_mod
from . import branchpoints as bp_mod
from . import credibility as cred_mod
from . import dimensions as dimensions_mod
from . import personas as personas_mod
from . import scoring as scoring_mod
from . import simulate as sim_mod
from .common import horizon_for_mode, stable_seed

# emit may be sync or async; we normalize via _safe_emit.
EmitFn = Callable[[str, Dict[str, object]], object]

# Extra wall-clock headroom on top of the mode budget before the hard root
# timeout fires (SYS-02). The mode budget is the *target*; the root timeout is
# the *backstop* that guarantees the client always gets a terminal event.
_ROOT_TIMEOUT_BUFFER: float = 10.0


class SimulationCancelled(Exception):
    """Raised when a run is cancelled cooperatively via its CancelToken."""


class CancelToken:
    """Cooperative cancel flag shared with the API layer.

    The orchestrator checks .cancelled at phase boundaries; the API sets it from
    the /cancel endpoint. This is best-effort cooperative cancellation — it does
    not kill an in-flight blocking LLM call, but the per-call timeout bounds that.
    """

    __slots__ = ("_cancelled",)

    def __init__(self) -> None:
        self._cancelled = False

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True


async def _safe_emit(emit: Optional[EmitFn], event_type: str, payload: Dict[str, object]) -> None:
    if emit is None:
        return
    try:
        result = emit(event_type, payload)
        if asyncio.iscoroutine(result):
            await result
    except Exception:
        # Emission must never crash the simulation.
        pass


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


async def run_simulation(
    req: SimRequest,
    emit: Optional[EmitFn] = None,
    sim_id: str = "",
    cancel_token: Optional[CancelToken] = None,
) -> SimResult:
    """Run the full paired-counterfactual simulation.

    Returns the assembled SimResult. Emits streaming events via `emit` if given.
    Wraps the pipeline in a whole-run timeout (mode budget + buffer) so a hung
    LLM call can never strand the client (SYS-02); on timeout/cancel/failure it
    emits a terminal `error` event before raising.
    """
    mode = (req.mode or "quick").lower()
    root_timeout = config.mode_timeout(mode) + _ROOT_TIMEOUT_BUFFER
    try:
        return await asyncio.wait_for(
            _run_simulation_impl(req, emit, sim_id, cancel_token),
            timeout=root_timeout,
        )
    except SimulationCancelled:
        await _safe_emit(emit, "error", {"message": "Simulation cancelled by user"})
        raise
    except asyncio.TimeoutError:
        await _safe_emit(emit, "error", {
            "message": "Simulation exceeded the %s-mode time limit" % mode,
        })
        raise
    except Exception as exc:  # never silent-hang (BE-04)
        await _safe_emit(emit, "error", {"message": "Simulation failed: %s" % type(exc).__name__})
        raise
    finally:
        # Never let one run's budget-shedding degrade the next run's LLM path.
        config.set_force_stub(False)


def _check_cancel(cancel_token: Optional[CancelToken]) -> None:
    if cancel_token is not None and cancel_token.cancelled:
        raise SimulationCancelled()


async def _run_simulation_impl(
    req: SimRequest,
    emit: Optional[EmitFn],
    sim_id: str,
    cancel_token: Optional[CancelToken],
) -> SimResult:
    """Core pipeline. Wrapped by run_simulation for timeout/cancel handling."""
    seed = stable_seed(req.decision, req.seed)
    mode = (req.mode or "quick").lower()
    horizon = horizon_for_mode(mode)
    loop = asyncio.get_event_loop()
    start = loop.time()
    budget = config.mode_timeout(mode)
    # Start each run with the LLM path available; we may degrade it mid-run.
    config.set_force_stub(False)
    _escalated = False

    async def _escalate_if_over_budget(fraction: float = 0.8) -> None:
        """Past `fraction` of the mode budget, force all remaining LLM calls to
        the deterministic stub so latency can never accumulate further (BE-04 /
        NFR-04). Idempotent; emits one status note when it first fires."""
        nonlocal _escalated
        if _escalated:
            return
        if (loop.time() - start) > (budget * fraction):
            _escalated = True
            config.set_force_stub(True)
            await _safe_emit(emit, "status", {
                "phase": "scoring",
                "message": "Time budget nearly spent; finishing with fast estimates",
                "progress": 0.68,
            })

    # --- Phase: clarify ---
    _check_cancel(cancel_token)
    await _safe_emit(emit, "status", {
        "phase": "clarify", "message": "Reading the decision and options", "progress": 0.05,
    })

    # --- Phase: personas (built ONCE, shared by both branches) ---
    await _safe_emit(emit, "status", {
        "phase": "personas", "message": "Building digital-twin personas", "progress": 0.15,
    })
    personas: List[Persona] = await asyncio.to_thread(
        personas_mod.build_personas,
        req.decision, req.options, req.affected_people, seed, mode,
    )
    for p in personas:
        await _safe_emit(emit, "persona", p.model_dump())

    # --- Phase: backbone (deterministic, shared) ---
    _check_cancel(cancel_token)
    await _safe_emit(emit, "status", {
        "phase": "backbone", "message": "Drawing the shared exogenous backbone", "progress": 0.3,
    })
    backbone = backbone_mod.build_backbone(req.decision, seed, mode)

    # --- Phase: dimensions (generated ONCE, shared by both branches; M-c) ---
    # Emitted BEFORE any metric so the client can lay out N dynamic curves.
    _check_cancel(cancel_token)
    await _safe_emit(emit, "status", {
        "phase": "dimensions", "message": "Choosing the decision's outcome dimensions",
        "progress": 0.35,
    })
    dims: List[Dimension] = await asyncio.to_thread(
        dimensions_mod.generate_dimensions, req.decision, seed,
    )
    await _safe_emit(emit, "dimensions", {"dimensions": [d.model_dump() for d in dims]})

    # --- Phases: branchA & branchB concurrently (BE-03) ---
    await _safe_emit(emit, "status", {
        "phase": "branchA", "message": "Simulating branch A", "progress": 0.4,
    })
    await _safe_emit(emit, "status", {
        "phase": "branchB", "message": "Simulating branch B", "progress": 0.4,
    })

    stats = sim_mod.make_stats()

    # Cross-thread bridge: generate_branch_events runs in a worker thread and
    # fires early_emit(skeleton) synchronously from that thread. We hand those
    # events back to the event loop via call_soon_threadsafe -> an asyncio.Queue
    # that the loop drains and streams, so skeletons surface in near-realtime as
    # each branch finishes — before the other branch or scoring (BE-04 / FE-21).
    skeleton_q: "asyncio.Queue[Optional[TimelineEvent]]" = asyncio.Queue()

    def _make_early_emit() -> sim_mod.EarlyEmitFn:
        def _early(ev: TimelineEvent) -> None:
            loop.call_soon_threadsafe(skeleton_q.put_nowait, ev)
        return _early

    async def _gen(branch: str, option_text: str) -> List[TimelineEvent]:
        return await asyncio.to_thread(
            sim_mod.generate_branch_events,
            branch, option_text, req.decision, personas, backbone, seed, mode, stats,
            None, _make_early_emit(),
        )

    task_a = asyncio.ensure_future(_gen("A", req.options[0]))
    task_b = asyncio.ensure_future(_gen("B", req.options[1]))
    branch_tasks = [task_a, task_b]
    gather_task = asyncio.gather(*branch_tasks)

    # Drain skeleton events as they arrive while the branches are still running,
    # emitting a granular progress status every few events so the longest phase
    # is never a frozen 40% bar (NFR-02). We stop draining once both branches
    # are done AND the queue is empty. The denominator grows as we discover how
    # many skeletons each branch produces, so progress is monotonic and never
    # exceeds the 0.4 -> 0.65 branch window.
    streamed_skeletons = 0
    expected_skeletons = 6  # initial estimate (~3 skeleton milestones x 2 branches)
    emitted_skeleton_ids: set = set()
    while True:
        all_done = all(t.done() for t in branch_tasks)
        try:
            ev = await asyncio.wait_for(skeleton_q.get(), timeout=0.25)
        except asyncio.TimeoutError:
            if all_done and skeleton_q.empty():
                break
            _check_cancel(cancel_token)
            await _escalate_if_over_budget()
            continue
        if ev is None or ev.id in emitted_skeleton_ids:
            continue
        emitted_skeleton_ids.add(ev.id)
        await _safe_emit(emit, "timeline_event", ev.model_dump())
        streamed_skeletons += 1
        # Keep the denominator >= what we have actually streamed (monotonic).
        if streamed_skeletons > expected_skeletons:
            expected_skeletons = streamed_skeletons
        # Granular progress within the 0.4 -> 0.65 branch window (NFR-02).
        frac = min(1.0, streamed_skeletons / float(expected_skeletons))
        await _safe_emit(emit, "status", {
            "phase": "branchA" if ev.branch == "A" else "branchB",
            "message": "Streaming branch %s skeleton" % ev.branch,
            "progress": round(0.4 + 0.25 * frac, 3),
        })

    # Branches are done; surface any propagated error.
    events_a, events_b = await gather_task
    all_events: List[TimelineEvent] = list(events_a) + list(events_b)

    # Emit the remaining events: any late/undelivered skeleton first, then
    # perturbation, then exogenous. Skeletons already streamed above are skipped
    # to avoid duplicates.
    _check_cancel(cancel_token)
    kind_rank = {"skeleton": 0, "perturbation": 1, "exogenous": 2}
    remaining = [e for e in all_events if e.id not in emitted_skeleton_ids]
    for ev in sorted(remaining, key=lambda e: (kind_rank.get(e.kind, 3), e.month, e.branch, e.id)):
        emitted_skeleton_ids.add(ev.id)
        await _safe_emit(emit, "timeline_event", ev.model_dump())

    # --- Phase: scoring ---
    _check_cancel(cancel_token)
    await _escalate_if_over_budget()
    await _safe_emit(emit, "status", {
        "phase": "scoring", "message": "Scoring monthly outcomes", "progress": 0.7,
    })

    def _score(branch: str, option_text: str, events: List[TimelineEvent]) -> List[MetricPoint]:
        return scoring_mod.score_branch(branch, option_text, personas, events, seed, mode, dims)

    metrics_a, metrics_b = await asyncio.gather(
        asyncio.to_thread(_score, "A", req.options[0], all_events),
        asyncio.to_thread(_score, "B", req.options[1], all_events),
    )
    metrics: List[MetricPoint] = list(metrics_a) + list(metrics_b)
    for mp in sorted(metrics, key=lambda m: (m.month, m.branch)):
        await _safe_emit(emit, "metric", mp.model_dump())

    # --- Branch points ---
    _check_cancel(cancel_token)
    branch_points = bp_mod.detect_branch_points(metrics, all_events, dims)
    for bp in branch_points:
        await _safe_emit(emit, "branch_point", bp.model_dump())

    # --- Credibility ---
    credibility = cred_mod.build_credibility(
        personas, all_events, branch_points, stats.rejection_rate
    )
    await _safe_emit(emit, "credibility", credibility.model_dump())

    # --- Recommendation ---
    recommendation = cred_mod.build_recommendation(metrics, req.options, req.values, dims)
    await _safe_emit(emit, "recommendation", recommendation.model_dump())

    result = SimResult(
        sim_id=sim_id,
        decision=req.decision,
        options=req.options,
        mode=mode,
        seed=seed,
        dimensions=dims,
        personas=personas,
        events=all_events,
        metrics=metrics,
        branch_points=branch_points,
        credibility=credibility,
        recommendation=recommendation,
        created_at=_now_iso(),
    )

    await _safe_emit(emit, "status", {
        "phase": "done", "message": "Simulation complete", "progress": 1.0,
    })
    await _safe_emit(emit, "done", {"sim_id": sim_id})
    return result
