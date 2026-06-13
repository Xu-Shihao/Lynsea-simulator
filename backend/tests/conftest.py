"""
Shared fixtures and mock SSE stream for the Lynsea QA harness.

This module provides:
- MOCK_SSE_STREAM: a minimal valid SSE event sequence matching docs/api-contract.md
- parse_sse_stream(): helper to turn raw SSE text into list of dicts
- live_base_url(): fixture for --base CLI override (skipif not provided)
"""
import json
import re
import pytest

# ---------------------------------------------------------------------------
# Canonical example SSE stream (recorded from contract, not from a live server)
# Used by contract-shape tests that must pass without a running backend.
# ---------------------------------------------------------------------------

RUN_ID = "00000000-0000-0000-0000-000000000001"
SEED = 42

# A minimal but structurally complete mock SSE stream.
# Ordered: run_started → world_ready → timeline_event(s) → metric(s)
#          → fork_point → branch_score(s) → credibility → recommendation → done
MOCK_SSE_LINES = [
    f'event: run_started\ndata: {{"run_id": "{RUN_ID}", "mode": "quick", "branches": ["A", "B"]}}\n',
    f'event: world_ready\ndata: {{"personas": [{{"id": "p1", "role": "partner", "influence_weight": 8, "confidence": "high"}}, {{"id": "p2", "role": "mother", "influence_weight": 6, "confidence": "low"}}], "options": {{"A": "Stay at current job", "B": "Join the startup"}}}}\n',

    # Branch A events
    f'event: timeline_event\ndata: {{"branch": "A", "event_id": "A-m1-1", "month": 1, "kind": "skeleton", "title": "First month at current job", "detail": "Settled into routine; around a 70% chance of stable performance.", "personas": ["p1"]}}\n',
    f'event: timeline_event\ndata: {{"branch": "A", "event_id": "A-m2-1", "month": 2, "kind": "perturbation", "title": "Project delay", "detail": "Likely a delay occurs; likely around 60% probability.", "personas": ["p1", "p2"]}}\n',
    f'event: timeline_event\ndata: {{"branch": "A", "event_id": "A-m3-1", "month": 3, "kind": "skeleton", "title": "Mid-year review", "detail": "Performance review indicates around a 65% chance of promotion.", "personas": ["p1"]}}\n',

    # Branch B events
    f'event: timeline_event\ndata: {{"branch": "B", "event_id": "B-m1-1", "month": 1, "kind": "skeleton", "title": "First month at startup", "detail": "Likely adapting to fast-paced environment; around 75% chance of onboarding success.", "personas": ["p1"]}}\n',
    f'event: timeline_event\ndata: {{"branch": "B", "event_id": "B-m2-1", "month": 2, "kind": "perturbation", "title": "Funding uncertainty", "detail": "Around 40% chance of Series A delay; likely impacts runway.", "personas": ["p1", "p2"]}}\n',
    f'event: timeline_event\ndata: {{"branch": "B", "event_id": "B-m3-1", "month": 3, "kind": "skeleton", "title": "Product launch", "detail": "Likely launch in month 3; around 55% chance of hitting initial targets.", "personas": ["p1"]}}\n',

    # Metrics for A
    f'event: metric\ndata: {{"branch": "A", "month": 1, "dim": "economic", "score": 70, "evidence_event_ids": ["A-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "A", "month": 1, "dim": "career", "score": 65, "evidence_event_ids": ["A-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "A", "month": 1, "dim": "relationships", "score": 75, "evidence_event_ids": ["A-m1-1", "A-m2-1"]}}\n',
    f'event: metric\ndata: {{"branch": "A", "month": 1, "dim": "mental_health", "score": 68, "evidence_event_ids": ["A-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "A", "month": 1, "dim": "autonomy", "score": 55, "evidence_event_ids": ["A-m1-1"]}}\n',

    # Metrics for B
    f'event: metric\ndata: {{"branch": "B", "month": 1, "dim": "economic", "score": 50, "evidence_event_ids": ["B-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "B", "month": 1, "dim": "career", "score": 80, "evidence_event_ids": ["B-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "B", "month": 1, "dim": "relationships", "score": 60, "evidence_event_ids": ["B-m1-1", "B-m2-1"]}}\n',
    f'event: metric\ndata: {{"branch": "B", "month": 1, "dim": "mental_health", "score": 55, "evidence_event_ids": ["B-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "B", "month": 1, "dim": "autonomy", "score": 85, "evidence_event_ids": ["B-m1-1"]}}\n',

    # Fork point
    f'event: fork_point\ndata: {{"month": 2, "magnitude": 72, "title": "Career trajectory diverges", "explanation": "Likely income gap emerges; around 60% probability the startup path diverges from stable employment.", "dims": ["economic", "career"]}}\n',

    # Branch scores
    f'event: branch_score\ndata: {{"branch": "A", "total": 67, "breakdown": {{"economic": 70, "career": 65, "relationships": 75, "mental_health": 68, "autonomy": 55}}, "weighted": true}}\n',
    f'event: branch_score\ndata: {{"branch": "B", "total": 66, "breakdown": {{"economic": 50, "career": 80, "relationships": 60, "mental_health": 55, "autonomy": 85}}, "weighted": true}}\n',

    # Credibility
    f'event: credibility\ndata: {{"overall": 72, "breakdown": {{"data_sufficiency": 68, "causal_confidence": 75, "event_plausibility": 73}}, "notes": "Likely direction is reliable; specific scores are approximate."}}\n',

    # Recommendation
    f'event: recommendation\ndata: {{"leaning": "A", "rationale": "Around a 55% likelihood that staying provides better stability given the profile.", "guardrail": "This is a simulation, not a prophecy. Around a 45% chance the outcome differs. See how to change this outcome below."}}\n',

    # Done
    f'event: done\ndata: {{"run_id": "{RUN_ID}"}}\n',
]

MOCK_SSE_STREAM = "\n".join(MOCK_SSE_LINES)

# High-risk mock stream (for E2E-2 / guardrail tests)
HIGH_RISK_SSE_LINES = [
    f'event: run_started\ndata: {{"run_id": "risk-run-001", "mode": "quick", "branches": ["A", "B"]}}\n',
    f'event: world_ready\ndata: {{"personas": [{{"id": "p1", "role": "partner", "influence_weight": 9, "confidence": "high"}}], "options": {{"A": "End the relationship", "B": "Stay in relationship"}}}}\n',
    f'event: timeline_event\ndata: {{"branch": "A", "event_id": "A-m1-1", "month": 1, "kind": "skeleton", "title": "Breakup finalized", "detail": "Around a 70% chance of initial emotional distress.", "personas": ["p1"]}}\n',
    f'event: timeline_event\ndata: {{"branch": "B", "event_id": "B-m1-1", "month": 1, "kind": "skeleton", "title": "Relationship continues", "detail": "Likely ongoing tension; around 60% chance of gradual improvement.", "personas": ["p1"]}}\n',
    f'event: metric\ndata: {{"branch": "A", "month": 1, "dim": "economic", "score": 60, "evidence_event_ids": ["A-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "A", "month": 1, "dim": "career", "score": 65, "evidence_event_ids": ["A-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "A", "month": 1, "dim": "relationships", "score": 20, "evidence_event_ids": ["A-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "A", "month": 1, "dim": "mental_health", "score": 30, "evidence_event_ids": ["A-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "A", "month": 1, "dim": "autonomy", "score": 75, "evidence_event_ids": ["A-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "B", "month": 1, "dim": "economic", "score": 60, "evidence_event_ids": ["B-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "B", "month": 1, "dim": "career", "score": 60, "evidence_event_ids": ["B-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "B", "month": 1, "dim": "relationships", "score": 50, "evidence_event_ids": ["B-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "B", "month": 1, "dim": "mental_health", "score": 45, "evidence_event_ids": ["B-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "B", "month": 1, "dim": "autonomy", "score": 40, "evidence_event_ids": ["B-m1-1"]}}\n',
    f'event: fork_point\ndata: {{"month": 1, "magnitude": 85, "title": "Relationship status diverges sharply", "explanation": "Around 85% probability this is the critical fork in emotional wellbeing.", "dims": ["relationships", "mental_health"]}}\n',
    f'event: branch_score\ndata: {{"branch": "A", "total": 50, "breakdown": {{"economic": 60, "career": 65, "relationships": 20, "mental_health": 30, "autonomy": 75}}, "weighted": true}}\n',
    f'event: branch_score\ndata: {{"branch": "B", "total": 51, "breakdown": {{"economic": 60, "career": 60, "relationships": 50, "mental_health": 45, "autonomy": 40}}, "weighted": true}}\n',
    f'event: credibility\ndata: {{"overall": 65, "breakdown": {{"data_sufficiency": 60, "causal_confidence": 65, "event_plausibility": 70}}, "notes": "Emotional outcomes are highly individual; this is an approximate direction."}}\n',
    f'event: recommendation\ndata: {{"leaning": "neither", "rationale": "Around a 50% chance either path leads to better outcomes depending on individual circumstances.", "guardrail": "This is a simulation, not a prophecy. How to change this outcome: consider couples counseling, communication improvements."}}\n',
    f'event: done\ndata: {{"run_id": "risk-run-001"}}\n',
]

HIGH_RISK_SSE_STREAM = "\n".join(HIGH_RISK_SSE_LINES)

# Cold-start mock stream (for E2E-6, ALG-04)
COLD_START_SSE_LINES = [
    f'event: run_started\ndata: {{"run_id": "cold-run-001", "mode": "quick", "branches": ["A", "B"]}}\n',
    f'event: world_ready\ndata: {{"personas": [{{"id": "p1", "role": "partner", "influence_weight": 5, "confidence": "low"}}, {{"id": "p2", "role": "colleague", "influence_weight": 3, "confidence": "low"}}], "options": {{"A": "Option A", "B": "Option B"}}}}\n',
    f'event: timeline_event\ndata: {{"branch": "A", "event_id": "A-m1-1", "month": 1, "kind": "skeleton", "title": "First month", "detail": "该角色信息有限，仅供参考 — around a 60% chance of typical outcome.", "personas": ["p1"]}}\n',
    f'event: timeline_event\ndata: {{"branch": "B", "event_id": "B-m1-1", "month": 1, "kind": "skeleton", "title": "First month alt", "detail": "该角色信息有限，仅供参考 — around a 55% chance of typical outcome.", "personas": ["p2"]}}\n',
    f'event: metric\ndata: {{"branch": "A", "month": 1, "dim": "economic", "score": 55, "evidence_event_ids": ["A-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "A", "month": 1, "dim": "career", "score": 55, "evidence_event_ids": ["A-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "A", "month": 1, "dim": "relationships", "score": 55, "evidence_event_ids": ["A-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "A", "month": 1, "dim": "mental_health", "score": 55, "evidence_event_ids": ["A-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "A", "month": 1, "dim": "autonomy", "score": 55, "evidence_event_ids": ["A-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "B", "month": 1, "dim": "economic", "score": 50, "evidence_event_ids": ["B-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "B", "month": 1, "dim": "career", "score": 50, "evidence_event_ids": ["B-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "B", "month": 1, "dim": "relationships", "score": 50, "evidence_event_ids": ["B-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "B", "month": 1, "dim": "mental_health", "score": 50, "evidence_event_ids": ["B-m1-1"]}}\n',
    f'event: metric\ndata: {{"branch": "B", "month": 1, "dim": "autonomy", "score": 50, "evidence_event_ids": ["B-m1-1"]}}\n',
    f'event: fork_point\ndata: {{"month": 1, "magnitude": 40, "title": "Uncertainty diverges with limited data", "explanation": "Around 40% probability that outcomes differ; limited info reduces confidence.", "dims": ["economic", "career"]}}\n',
    f'event: branch_score\ndata: {{"branch": "A", "total": 53, "breakdown": {{"economic": 55, "career": 55, "relationships": 55, "mental_health": 55, "autonomy": 55}}, "weighted": true}}\n',
    f'event: branch_score\ndata: {{"branch": "B", "total": 50, "breakdown": {{"economic": 50, "career": 50, "relationships": 50, "mental_health": 50, "autonomy": 50}}, "weighted": true}}\n',
    f'event: credibility\ndata: {{"overall": 45, "breakdown": {{"data_sufficiency": 35, "causal_confidence": 50, "event_plausibility": 50}}, "notes": "Limited persona data reduces confidence. 该角色信息有限，仅供参考."}}\n',
    f'event: recommendation\ndata: {{"leaning": "neither", "rationale": "Around a 50% chance either path is better; insufficient persona data to distinguish outcomes confidently.", "guardrail": "This is a simulation, not a prophecy. How to change this outcome: provide more detail about the people involved."}}\n',
    f'event: done\ndata: {{"run_id": "cold-run-001"}}\n',
]

COLD_START_SSE_STREAM = "\n".join(COLD_START_SSE_LINES)


def parse_sse_stream(raw: str) -> list[dict]:
    """Parse raw SSE text into a list of {event_type, data} dicts."""
    events = []
    current_event = {}
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("event:"):
            current_event["event_type"] = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_str = line[len("data:"):].strip()
            try:
                current_event["data"] = json.loads(data_str)
            except json.JSONDecodeError:
                current_event["data"] = data_str
        elif line == "" and current_event:
            events.append(current_event)
            current_event = {}
    if current_event:
        events.append(current_event)
    return events


def pytest_addoption(parser):
    parser.addoption(
        "--base",
        action="store",
        default=None,
        help="Base URL of a live backend, e.g. http://localhost:8000",
    )


@pytest.fixture
def live_base_url(request):
    return request.config.getoption("--base")


@pytest.fixture
def parsed_mock_stream():
    return parse_sse_stream(MOCK_SSE_STREAM)


@pytest.fixture
def parsed_high_risk_stream():
    return parse_sse_stream(HIGH_RISK_SSE_STREAM)


@pytest.fixture
def parsed_cold_start_stream():
    return parse_sse_stream(COLD_START_SSE_STREAM)
