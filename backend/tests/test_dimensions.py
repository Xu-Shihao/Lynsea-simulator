"""Phase 2: per-decision dimension generation (stub path forced)."""
from __future__ import annotations

import app.config as config
from app.contracts import DEFAULT_DIMENSIONS, Dimension
from app.engine.dimensions import generate_dimensions


def test_generates_4_to_8_unique(monkeypatch):
    monkeypatch.setattr(config, "complete_json", lambda *a, **k: None)  # stub path
    dims = generate_dimensions("Should I take a higher-paying but stressful job?", seed=123)
    assert 4 <= len(dims) <= 8
    assert len({d.id for d in dims}) == len(dims)
    assert all(isinstance(d, Dimension) for d in dims)


def test_deterministic_for_seed(monkeypatch):
    monkeypatch.setattr(config, "complete_json", lambda *a, **k: None)
    a = generate_dimensions("X decision", seed=7)
    b = generate_dimensions("X decision", seed=7)
    assert [d.id for d in a] == [d.id for d in b]


def test_stub_returns_default_set(monkeypatch):
    monkeypatch.setattr(config, "complete_json", lambda *a, **k: None)
    dims = generate_dimensions("anything", seed=1)
    assert {d.id for d in dims} == {d.id for d in DEFAULT_DIMENSIONS}


def test_llm_dims_validated_and_clamped(monkeypatch):
    # LLM returns more than 8 dims with a duplicate + a bad polarity; expect
    # dedupe, slugified ids, clamp to 8.
    raw = [
        {"id": "Work Life", "label": "Work/Life", "description": "balance", "polarity": "lower_is_better"},
        {"id": "work life", "label": "dup", "description": "", "polarity": "higher_is_better"},
    ] + [
        {"id": "dim%d" % i, "label": "D%d" % i, "description": "", "polarity": "higher_is_better"}
        for i in range(10)
    ]
    monkeypatch.setattr(config, "complete_json", lambda *a, **k: raw)
    dims = generate_dimensions("balance my life", seed=2)
    assert 4 <= len(dims) <= 8
    ids = [d.id for d in dims]
    assert len(set(ids)) == len(ids)  # deduped
    assert "work_life" in ids  # slugified
    # polarity preserved for first occurrence
    wl = next(d for d in dims if d.id == "work_life")
    assert wl.polarity == "lower_is_better"


def test_invalid_llm_falls_back_to_default(monkeypatch):
    monkeypatch.setattr(config, "complete_json", lambda *a, **k: {"not": "a list"})
    dims = generate_dimensions("x", seed=3)
    assert {d.id for d in dims} == {d.id for d in DEFAULT_DIMENSIONS}


def test_too_few_llm_dims_falls_back(monkeypatch):
    monkeypatch.setattr(
        config, "complete_json",
        lambda *a, **k: [{"id": "a", "label": "A", "polarity": "higher_is_better"}],
    )
    dims = generate_dimensions("x", seed=4)
    # Only 1 valid dim < 4 minimum => fall back to default set.
    assert {d.id for d in dims} == {d.id for d in DEFAULT_DIMENSIONS}
