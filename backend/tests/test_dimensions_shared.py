"""Dimensions are generated ONCE, emitted before metrics, and shared by A/B."""
from __future__ import annotations

import asyncio

from app.contracts import SimRequest
from app.engine import orchestrator


def _collect_run(req: SimRequest):
    events: list = []

    async def emit(etype, payload):
        events.append((etype, payload))

    async def _go():
        return await orchestrator.run_simulation(req, emit, sim_id="t")

    result = asyncio.run(_go())
    return result, events


def test_dimensions_emitted_before_metrics_and_shared():
    req = SimRequest(
        decision="Should I take a higher-paying but stressful job?",
        options=["Take the job", "Stay put"],
        affected_people=["my partner"],
        mode="quick",
    )
    result, events = _collect_run(req)

    etypes = [e for e, _ in events]
    assert "dimensions" in etypes, "a dimensions event was emitted"

    dim_idx = etypes.index("dimensions")
    metric_idxs = [i for i, e in enumerate(etypes) if e == "metric"]
    assert metric_idxs, "metric events emitted"
    assert dim_idx < min(metric_idxs), "dimensions emitted before any metric"

    # The result carries the dimensions and there are 4-8 unique ids.
    assert result.dimensions
    dim_ids = [d.id for d in result.dimensions]
    assert 4 <= len(dim_ids) <= 8
    assert len(set(dim_ids)) == len(dim_ids)

    # The streamed dimensions payload matches the result's dimensions.
    streamed = events[dim_idx][1]["dimensions"]
    assert [d["id"] for d in streamed] == dim_ids

    # Every metric point (both branches) is keyed by exactly the shared dim set.
    shared = set(dim_ids)
    for mp in result.metrics:
        assert set(mp.scores.keys()) == shared
    # Both branches present and share the identical dimension set.
    branch_a = [mp for mp in result.metrics if mp.branch == "A"]
    branch_b = [mp for mp in result.metrics if mp.branch == "B"]
    assert branch_a and branch_b
    assert set(branch_a[0].scores.keys()) == set(branch_b[0].scores.keys()) == shared
