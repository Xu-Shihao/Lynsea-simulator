"""Lynsea API endpoints (FROZEN contract).

  POST   /api/clarify                  -> ClarificationPlan (refine-your-world)
  POST   /api/simulate                 -> {"sim_id": "<uuid>"} ; starts bg task
  GET    /api/simulate/{sim_id}/stream -> SSE stream of engine events
  GET    /api/simulate/{sim_id}        -> full SimResult JSON (404 if unknown)
  POST   /api/simulate/{sim_id}/cancel -> request cancellation of a running sim
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from ..contracts import ClarificationPlan, ClarifyRequest, SimRequest, SimResult
from ..engine import clarify as clarify_mod
from ..engine import orchestrator
from .store import STORE, SimRecord

router = APIRouter(prefix="/api")

# SSE event types the engine may emit, in nominal order.
_NON_TERMINAL = {
    "status", "persona", "dimensions", "timeline_event", "metric",
    "branch_point", "credibility", "recommendation",
}
_TERMINAL = {"done", "error"}
_ALLOWED_EVENTS = _NON_TERMINAL | _TERMINAL


async def _run_task(sim_id: str, req: SimRequest, rec: SimRecord) -> None:
    """Background task: run the orchestrator, feeding the record's queue/result."""
    async def emit(event_type: str, payload: dict) -> None:
        await rec.emit(event_type, payload)

    try:
        result: SimResult = await orchestrator.run_simulation(
            req, emit, sim_id, cancel_token=rec.cancel_token
        )
        STORE.set_result(sim_id, result)
    except orchestrator.SimulationCancelled:
        # The orchestrator already emitted a terminal "error" event.
        pass
    except asyncio.CancelledError:
        # Hard task cancellation (best-effort). Ensure the client sees a terminal.
        if not rec.done:
            await rec.emit("error", {"message": "Simulation cancelled by user"})
        raise
    except Exception as exc:  # orchestrator already emitted "error"
        if not rec.done:
            await rec.emit("error", {"message": "Simulation failed: %s" % type(exc).__name__})


@router.post("/clarify")
async def clarify(req: ClarifyRequest) -> dict:
    """Generate (or refine) a "Refine your world" ClarificationPlan for a decision.

    Body: { decision, prior?: ClarificationPlan, note?: str }. The LLM call is
    offloaded to a worker thread and falls back to a deterministic stub when no
    key is configured, so this endpoint always returns a valid plan.
    """
    plan: ClarificationPlan = await asyncio.to_thread(
        clarify_mod.generate_clarification, req.decision, req.prior, req.note,
    )
    return plan.model_dump()


@router.post("/simulate")
async def create_simulation(req: SimRequest) -> dict:
    """Create a simulation, kick off the background task, return its id."""
    sim_id = uuid.uuid4().hex
    rec = STORE.create(sim_id)
    rec.cancel_token = orchestrator.CancelToken()
    # Fire-and-forget background task; the queue/store capture all progress.
    rec.task = asyncio.create_task(_run_task(sim_id, req, rec))
    return {"sim_id": sim_id}


@router.get("/simulate/{sim_id}/stream")
async def stream_simulation(sim_id: str) -> EventSourceResponse:
    """Stream engine events as SSE. Replays already-emitted history, then live."""
    rec = STORE.get(sim_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="unknown sim_id")

    async def event_gen() -> AsyncIterator[dict]:
        sent = 0
        while True:
            # Replay any buffered history not yet sent (covers late subscribers).
            while sent < len(rec.history):
                etype, payload = rec.history[sent]
                sent += 1
                if etype not in _ALLOWED_EVENTS:
                    continue
                yield {"event": etype, "data": json.dumps(payload)}
                if etype in _TERMINAL:
                    return
            if rec.done and sent >= len(rec.history):
                return
            # Wait for the next live event; time out to re-check history/done.
            try:
                etype, payload = await asyncio.wait_for(rec.queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            # The history loop above will emit it (keeps ordering single-sourced).

    return EventSourceResponse(event_gen())


@router.get("/simulate/{sim_id}")
async def get_simulation(sim_id: str) -> dict:
    """Return the full SimResult JSON, or 404 if unknown / not yet ready."""
    rec = STORE.get(sim_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="unknown sim_id")
    if rec.error and rec.result is None:
        raise HTTPException(status_code=500, detail=rec.error)
    if rec.result is None:
        # Known id but the background task has not finished assembling the result.
        raise HTTPException(status_code=425, detail="simulation not ready")
    return rec.result.model_dump()


@router.post("/simulate/{sim_id}/cancel")
async def cancel_simulation(sim_id: str) -> dict:
    """Request cancellation of a running simulation (SYS-02).

    Sets the cooperative cancel flag so the orchestrator stops at its next phase
    boundary and emits a terminal error event. If the run already finished this
    is a no-op. Returns the observed cancellation state.
    """
    rec = STORE.get(sim_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="unknown sim_id")
    if rec.done:
        return {"sim_id": sim_id, "cancelled": False, "status": "already_finished"}
    rec.cancelled = True
    if rec.cancel_token is not None:
        rec.cancel_token.cancel()
    return {"sim_id": sim_id, "cancelled": True, "status": "cancelling"}
