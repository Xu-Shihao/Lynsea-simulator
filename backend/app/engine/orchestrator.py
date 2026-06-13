"""Simulation orchestration (BE-03 concurrent branches, BE-04 streaming).

run_simulation(req, emit) drives the full pipeline, calling emit(event_type,
payload) at each step so the API layer can stream Server-Sent Events, and returns
the fully-assembled SimResult for storage/reload.

Emit order:
  status(phase) -> persona(each) -> timeline_event(skeleton, perturbation, then
  shared exogenous in BOTH branches) -> metric(per branch per month) ->
  branch_point -> credibility -> recommendation -> done {sim_id}
On failure: error {message}. Never hangs silently.

The two branches are generated concurrently via asyncio.to_thread so total time
~= single-branch time even though the per-branch LLM calls are blocking.
"""
from __future__ import annotations

import asyncio
import datetime
from typing import Awaitable, Callable, Dict, List, Optional, Tuple

from ..contracts import (
    MetricPoint,
    Persona,
    SimRequest,
    SimResult,
    TimelineEvent,
)
from . import backbone as backbone_mod
from . import branchpoints as bp_mod
from . import credibility as cred_mod
from . import personas as personas_mod
from . import scoring as scoring_mod
from . import simulate as sim_mod
from .common import horizon_for_mode, stable_seed

# emit may be sync or async; we normalize via _safe_emit.
EmitFn = Callable[[str, Dict[str, object]], object]


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
) -> SimResult:
    """Run the full paired-counterfactual simulation.

    Returns the assembled SimResult. Emits streaming events via `emit` if given.
    """
    seed = stable_seed(req.decision, req.seed)
    mode = (req.mode or "quick").lower()
    horizon = horizon_for_mode(mode)

    try:
        # --- Phase: clarify ---
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
        await _safe_emit(emit, "status", {
            "phase": "backbone", "message": "Drawing the shared exogenous backbone", "progress": 0.3,
        })
        backbone = backbone_mod.build_backbone(req.decision, seed, mode)

        # --- Phases: branchA & branchB concurrently (BE-03) ---
        await _safe_emit(emit, "status", {
            "phase": "branchA", "message": "Simulating branch A", "progress": 0.4,
        })
        await _safe_emit(emit, "status", {
            "phase": "branchB", "message": "Simulating branch B", "progress": 0.4,
        })

        stats = sim_mod.make_stats()

        async def _gen(branch: str, option_text: str) -> List[TimelineEvent]:
            return await asyncio.to_thread(
                sim_mod.generate_branch_events,
                branch, option_text, req.decision, personas, backbone, seed, mode, stats,
            )

        events_a, events_b = await asyncio.gather(
            _gen("A", req.options[0]),
            _gen("B", req.options[1]),
        )
        all_events: List[TimelineEvent] = list(events_a) + list(events_b)

        # Stream events: skeleton first, then perturbation, then exogenous.
        kind_rank = {"skeleton": 0, "perturbation": 1, "exogenous": 2}
        for ev in sorted(all_events, key=lambda e: (kind_rank.get(e.kind, 3), e.month, e.branch, e.id)):
            await _safe_emit(emit, "timeline_event", ev.model_dump())

        # --- Phase: scoring ---
        await _safe_emit(emit, "status", {
            "phase": "scoring", "message": "Scoring monthly outcomes", "progress": 0.7,
        })

        def _score(branch: str, option_text: str, events: List[TimelineEvent]) -> List[MetricPoint]:
            return scoring_mod.score_branch(branch, option_text, personas, events, seed, mode)

        metrics_a, metrics_b = await asyncio.gather(
            asyncio.to_thread(_score, "A", req.options[0], all_events),
            asyncio.to_thread(_score, "B", req.options[1], all_events),
        )
        metrics: List[MetricPoint] = list(metrics_a) + list(metrics_b)
        for mp in sorted(metrics, key=lambda m: (m.month, m.branch)):
            await _safe_emit(emit, "metric", mp.model_dump())

        # --- Branch points ---
        branch_points = bp_mod.detect_branch_points(metrics, all_events)
        for bp in branch_points:
            await _safe_emit(emit, "branch_point", bp.model_dump())

        # --- Credibility ---
        credibility = cred_mod.build_credibility(
            personas, all_events, branch_points, stats.rejection_rate
        )
        await _safe_emit(emit, "credibility", credibility.model_dump())

        # --- Recommendation ---
        recommendation = cred_mod.build_recommendation(metrics, req.options, req.values)
        await _safe_emit(emit, "recommendation", recommendation.model_dump())

        result = SimResult(
            sim_id=sim_id,
            decision=req.decision,
            options=req.options,
            mode=mode,
            seed=seed,
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

    except Exception as exc:  # never silent-hang (BE-04)
        await _safe_emit(emit, "error", {"message": "Simulation failed: %s" % type(exc).__name__})
        raise
