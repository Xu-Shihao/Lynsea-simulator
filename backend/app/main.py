"""FastAPI application entry point.

Endpoints (api-contract):

* ``GET  /api/health``                  — readiness probe.
* ``POST /api/simulate``                — SSE stream of the full contract.
* ``GET  /api/run/{run_id}/seed-check`` — ``{shared_event_hash}`` (reproducibility).
* ``POST /api/whatif``                  — SSE stream (P1; recoverable error now).

CORS allows the Next.js dev server (``http://localhost:3000``). Run with::

    cd backend && uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from app.config import get_settings
from app.orchestrator import get_seed_check, simulate_stream, whatif_stream
from app.schemas import SimulateRequest, WhatIfRequest

logging.basicConfig(level=logging.INFO)

settings = get_settings()

app = FastAPI(title="Lynsea Simulator API", version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Headers that keep SSE flowing through dev proxies and disable buffering.
_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Readiness check (api-contract §1)."""
    return {"status": "ok", "version": settings.app_version}


@app.post("/api/simulate")
async def simulate(req: SimulateRequest) -> StreamingResponse:
    """Kick off a simulation and stream the full SSE contract."""
    return StreamingResponse(
        simulate_stream(req),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@app.get("/api/run/{run_id}/seed-check")
async def seed_check(run_id: str) -> JSONResponse:
    """Return the shared random-event hash for a completed/started run.

    Lets QA assert branches A and B share the same random-event stream and that
    the same seed reproduces (`ALG-20/21`, `NFR-01`).
    """
    result = get_seed_check(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="unknown run_id")
    return JSONResponse(result)


@app.post("/api/whatif")
async def whatif(req: WhatIfRequest) -> StreamingResponse:
    """What-if branching (P1). Streams a recoverable error for now."""
    return StreamingResponse(
        whatif_stream(req),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
