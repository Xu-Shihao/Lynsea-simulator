"""End-to-end API test (FastAPI TestClient), no live key / no network."""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.main import app


def _poll_result(client, sim_id, timeout=10.0):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        resp = client.get("/api/simulate/%s" % sim_id)
        last = resp
        if resp.status_code == 200:
            return resp
        if resp.status_code == 500:
            return resp
        time.sleep(0.05)
    return last


def test_api_end_to_end():
    with TestClient(app) as client:
        body = {
            "decision": "Should I relocate to another city for a job?",
            "options": ["Relocate for the job", "Stay in my current city"],
            "affected_people": ["my partner", "my close friend"],
            "mode": "quick",
        }
        resp = client.post("/api/simulate", json=body)
        assert resp.status_code == 200
        sim_id = resp.json()["sim_id"]
        assert sim_id

        result = _poll_result(client, sim_id)
        assert result is not None
        assert result.status_code == 200, result.text
        data = result.json()

        assert data["sim_id"] == sim_id
        assert data["personas"], "personas non-empty"
        assert data["events"], "events non-empty"
        assert data["metrics"], "metrics non-empty"
        assert data["credibility"] is not None
        assert data["recommendation"] is not None
        assert data["recommendation"]["favored_branch"] in ("A", "B", "tie")

        # SYS-15: probabilistic phrasing, never "will" / "definitely".
        text = data["recommendation"]["text"].lower()
        assert " will " not in text
        assert "definitely" not in text


def test_get_unknown_sim_is_404():
    with TestClient(app) as client:
        resp = client.get("/api/simulate/does-not-exist")
        assert resp.status_code == 404


def test_options_must_be_two():
    with TestClient(app) as client:
        resp = client.post(
            "/api/simulate",
            json={"decision": "x", "options": ["only one"]},
        )
        assert resp.status_code == 422
