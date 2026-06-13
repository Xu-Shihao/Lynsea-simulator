"""Lynsea FastAPI application entrypoint.

Run from inside backend/:  uvicorn app.main:app --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router

app = FastAPI(title="Lynsea", version="0.1.0")

# Permissive CORS for the local frontend (MVP).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health() -> dict:
    """Liveness probe."""
    return {"status": "ok"}
