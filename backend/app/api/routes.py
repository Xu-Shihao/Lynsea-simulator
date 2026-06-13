"""Lynsea API endpoints (FROZEN contract).

  POST /api/simulate                 -> {"sim_id": "<uuid>"} ; starts bg task
  GET  /api/simulate/{sim_id}/stream -> SSE stream of engine events
  GET  /api/simulate/{sim_id}        -> full SimResult JSON (404 if unknown)
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from ..contracts import SimRequest, SimResult
from ..engine import orchestrator
from .store import STORE, SimRecord

router = APIRouter(prefix="/api")

# SSE event types the engine may emit, in nominal order.
_TERMINAL = {"done", "error"}


async def _run_task(sim_id: str, req: SimRequest, rec: SimRecord) -> None:
    """Background task: run the orchestrator, feeding the record's queue/result."""
    async def emit(event_type: str, payload: dict) -> None:
        await rec.emit(event_type, payload)

    try:
        result: SimResult = await orchestrator.run_simulation(req, emit, sim_id)
        STORE.set_result(sim_id, result)
    except Exception as exc:  # orchestrator already emitted "error"
        if not rec.done:
            await rec.emit("error", {"message": "Simulation failed: %s" % type(exc).__name__})


@router.post("/simulate")
async def create_simulation(req: SimRequest) -> dict:
    """Create a simulation, kick off the background task, return its id."""
    sim_id = uuid.uuid4().hex
    rec = STORE.create(sim_id)
    # Fire-and-forget background task; the queue/store capture all progress.
    asyncio.create_task(_run_task(sim_id, req, rec))
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
