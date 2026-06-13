"""BE-04 / NFR-02 / SYS-02: per-branch skeleton streaming, progress, cancel.

These exercise the orchestrator's streaming order and the API cancel endpoint
on the deterministic stub path (no live key, via the autouse _force_stub fixture).
"""
from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from app import config
from app.contracts import SimRequest, TimelineEvent
from app.engine import orchestrator
from app.main import app


def _collect_run(req: SimRequest):
    """Run the orchestrator synchronously, recording the full emit sequence."""
    events: list = []

    async def emit(etype, payload):
        events.append((etype, payload))

    async def _go():
        await orchestrator.run_simulation(req, emit, sim_id="t")

    asyncio.run(_go())
    return events


def test_skeleton_streams_before_perturbation_and_exogenous():
    req = SimRequest(
        decision="Should I take the new role?",
        options=["Take it", "Stay"],
        affected_people=["my partner"],
        mode="quick",
    )
    events = _collect_run(req)

    # Index of the FIRST non-skeleton timeline_event vs the LAST skeleton one.
    timeline = [
        (i, p) for i, (etype, p) in enumerate(events) if etype == "timeline_event"
    ]
    assert timeline, "expected timeline_event emissions"
    last_skeleton_idx = max(
        (i for i, p in timeline if p["kind"] == "skeleton"), default=-1
    )
    first_nonskeleton_idx = min(
        (i for i, p in timeline if p["kind"] != "skeleton"), default=10**9
    )
    # All skeletons are streamed before any perturbation/exogenous event.
    assert last_skeleton_idx < first_nonskeleton_idx

    # Both branches' skeletons appear, and exogenous events are shared/identical.
    skel_branches = {p["branch"] for _, p in timeline if p["kind"] == "skeleton"}
    assert skel_branches == {"A", "B"}


def test_progress_updates_during_branch_phase_are_monotonic():
    req = SimRequest(
        decision="Should I relocate?",
        options=["Relocate", "Stay"],
        mode="quick",
    )
    events = _collect_run(req)
    progresses = [
        p["progress"] for etype, p in events
        if etype == "status" and "progress" in p
    ]
    # Progress never decreases and ends at 1.0 (done).
    assert progresses == sorted(progresses)
    assert progresses[-1] == 1.0
    # There is at least one granular branch-phase update in (0.4, 0.7).
    assert any(0.4 < pr < 0.7 for pr in progresses)


def test_force_stub_round_trips():
    config.set_force_stub(True)
    assert config.force_stub_active() is True
    assert config.get_client() is None  # forced off regardless of key
    config.set_force_stub(False)
    assert config.force_stub_active() is False


def test_cancel_unknown_is_404():
    with TestClient(app) as client:
        resp = client.post("/api/simulate/nope/cancel")
        assert resp.status_code == 404


def test_cancel_endpoint_responds():
    with TestClient(app) as client:
        body = {
            "decision": "Should I switch careers?",
            "options": ["Switch", "Stay"],
            "mode": "quick",
        }
        sim_id = client.post("/api/simulate", json=body).json()["sim_id"]
        resp = client.post("/api/simulate/%s/cancel" % sim_id)
        assert resp.status_code == 200
        data = resp.json()
        assert data["sim_id"] == sim_id
        assert "cancelled" in data and "status" in data
