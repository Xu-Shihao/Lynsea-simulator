"""Shared pytest fixtures.

Force the deterministic stub path everywhere by monkeypatching config.complete
to return None. Tests must NOT call the real API or spend tokens.
"""
from __future__ import annotations

import pytest

from app import config


@pytest.fixture(autouse=True)
def _force_stub(monkeypatch):
    """Make every LLM call return None so the engine uses deterministic stubs."""
    monkeypatch.setattr(config, "complete", lambda *a, **k: None)
    # complete_json calls complete internally, but patch it too for safety.
    monkeypatch.setattr(config, "complete_json", lambda *a, **k: None)
    yield
