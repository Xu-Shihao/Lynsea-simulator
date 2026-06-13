"""Phase 5: clarification plan generation + /api/clarify (stub path)."""
from __future__ import annotations

import app.config as config
from app.contracts import ClarificationPlan
from app.engine.clarify import generate_clarification
from fastapi.testclient import TestClient

from app.main import app


def test_generate_clarification_stub(monkeypatch):
    monkeypatch.setattr(config, "complete_json", lambda *a, **k: None)
    plan = generate_clarification(
        "Should I quit to start a startup?", prior=None, note=None
    )
    assert isinstance(plan, ClarificationPlan)
    assert len(plan.suggested_options) >= 2
    assert len(plan.key_factors) >= 1
    assert len(plan.value_prompts) >= 1


def test_refine_round_folds_note_into_constraints(monkeypatch):
    monkeypatch.setattr(config, "complete_json", lambda *a, **k: None)
    first = generate_clarification("Should I relocate for my partner?", prior=None, note=None)
    refined = generate_clarification(
        "Should I relocate for my partner?",
        prior=first,
        note="I have a mortgage to consider",
    )
    assert any("mortgage" in c.lower() for c in refined.constraints)
    # Prior suggested options are preserved through a refine round.
    assert refined.suggested_options


def test_clarify_keyword_options_differ(monkeypatch):
    monkeypatch.setattr(config, "complete_json", lambda *a, **k: None)
    plan = generate_clarification("Should I quit my job?", prior=None, note=None)
    assert plan.suggested_options[0] != plan.suggested_options[1]


def test_clarify_route(monkeypatch):
    monkeypatch.setattr(config, "complete_json", lambda *a, **k: None)
    with TestClient(app) as client:
        resp = client.post("/api/clarify", json={"decision": "Should I go back to school?"})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data["suggested_options"]) >= 2
        assert len(data["key_factors"]) >= 1
        assert len(data["value_prompts"]) >= 1


def test_clarify_route_refine(monkeypatch):
    monkeypatch.setattr(config, "complete_json", lambda *a, **k: None)
    with TestClient(app) as client:
        first = client.post("/api/clarify", json={"decision": "Should I move abroad?"}).json()
        resp = client.post(
            "/api/clarify",
            json={"decision": "Should I move abroad?", "prior": first, "note": "visa issues"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert any("visa" in c.lower() for c in data["constraints"])
