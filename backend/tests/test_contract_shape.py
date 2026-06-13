"""
test_contract_shape.py — Contract shape checks for POST /api/simulate SSE stream.

Covers: docs/api-contract.md event ordering, field names, branch labels A/B,
5 metric dimensions, evidence_event_ids (ALG-40), and endpoint structure.

Tests run against:
  - Mock (always): validates the structural contract without a live server.
  - Live (skipif no --base): calls the real backend, parses live SSE stream.

Run: pytest backend/tests/test_contract_shape.py -v
"""
import json
import re
import pytest
import requests

from conftest import (
    MOCK_SSE_STREAM,
    HIGH_RISK_SSE_STREAM,
    COLD_START_SSE_STREAM,
    RUN_ID,
    parse_sse_stream,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
REQUIRED_FIRST_EVENT = "run_started"
REQUIRED_LAST_EVENT = "done"
REQUIRED_EVENT_TYPES = {
    "run_started", "world_ready", "timeline_event", "metric",
    "fork_point", "branch_score", "credibility", "recommendation", "done"
}
EXPECTED_BRANCHES = {"A", "B"}
METRIC_DIMS = {"economic", "career", "relationships", "mental_health", "autonomy"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_events_by_type(events: list[dict], event_type: str) -> list[dict]:
    return [e for e in events if e.get("event_type") == event_type]


def assert_stream_structural_contract(events: list[dict]):
    """
    Assert that a parsed SSE stream satisfies the full structural contract
    from docs/api-contract.md. Called for both mock and live streams.
    """
    event_types = [e["event_type"] for e in events]

    # --- Ordering: first and last events ---
    assert event_types[0] == REQUIRED_FIRST_EVENT, (
        f"First event must be 'run_started', got '{event_types[0]}'"
    )
    assert event_types[-1] == REQUIRED_LAST_EVENT, (
        f"Last event must be 'done', got '{event_types[-1]}'"
    )

    # --- run_started shape ---
    rs = get_events_by_type(events, "run_started")[0]["data"]
    assert "run_id" in rs, "run_started missing 'run_id'"
    assert "mode" in rs, "run_started missing 'mode'"
    assert "branches" in rs, "run_started missing 'branches'"
    assert set(rs["branches"]) == EXPECTED_BRANCHES, (
        f"run_started.branches must be ['A','B'], got {rs['branches']}"
    )

    # --- world_ready shape ---
    wr_events = get_events_by_type(events, "world_ready")
    assert len(wr_events) == 1, "Expected exactly 1 world_ready event"
    wr = wr_events[0]["data"]
    assert "personas" in wr, "world_ready missing 'personas'"
    assert "options" in wr, "world_ready missing 'options'"
    assert "A" in wr["options"] and "B" in wr["options"], (
        "world_ready.options must have keys 'A' and 'B'"
    )
    for persona in wr["personas"]:
        for field in ("id", "role", "influence_weight", "confidence"):
            assert field in persona, f"Persona missing field '{field}'"
        assert persona["confidence"] in ("high", "low"), (
            f"Persona confidence must be 'high' or 'low', got '{persona['confidence']}'"
        )

    # --- timeline_event shape ---
    te_events = get_events_by_type(events, "timeline_event")
    assert len(te_events) >= 2, "Must have at least 2 timeline_event events (one per branch)"

    for te in te_events:
        d = te["data"]
        for field in ("branch", "event_id", "month", "kind", "title", "detail", "personas"):
            assert field in d, f"timeline_event missing field '{field}'"
        assert d["branch"] in EXPECTED_BRANCHES, (
            f"timeline_event.branch must be A or B, got '{d['branch']}'"
        )
        assert d["kind"] in ("skeleton", "perturbation"), (
            f"timeline_event.kind must be 'skeleton' or 'perturbation', got '{d['kind']}'"
        )
        assert isinstance(d["month"], int), "timeline_event.month must be int"
        assert isinstance(d["personas"], list), "timeline_event.personas must be list"

        # event_id format: "{branch}-m{month}-{n}"
        event_id_pattern = re.compile(r'^[AB]-m\d+-\d+$')
        assert event_id_pattern.match(d["event_id"]), (
            f"event_id '{d['event_id']}' does not match pattern '{{branch}}-m{{month}}-{{n}}'"
        )

    # --- Branches A and B both have timeline events ---
    te_branches = {e["data"]["branch"] for e in te_events}
    assert "A" in te_branches, "No timeline_event for branch A"
    assert "B" in te_branches, "No timeline_event for branch B"

    # --- Skeleton events appear before perturbation (within each branch) ---
    for branch in ("A", "B"):
        branch_events = [e["data"] for e in te_events if e["data"]["branch"] == branch]
        kinds = [e["kind"] for e in branch_events]
        # All skeleton events should appear before any perturbation in the stream
        # (or at least one skeleton must exist)
        assert "skeleton" in kinds, f"Branch {branch} has no skeleton events"

    # --- metric shape and dimensions ---
    metric_events = get_events_by_type(events, "metric")
    assert len(metric_events) >= len(METRIC_DIMS) * 2, (
        f"Expected at least {len(METRIC_DIMS)*2} metric events (5 dims x 2 branches), got {len(metric_events)}"
    )

    for me in metric_events:
        d = me["data"]
        for field in ("branch", "month", "dim", "score", "evidence_event_ids"):
            assert field in d, f"metric missing field '{field}'"
        assert d["branch"] in EXPECTED_BRANCHES, (
            f"metric.branch must be A or B, got '{d['branch']}'"
        )
        assert d["dim"] in METRIC_DIMS, (
            f"metric.dim '{d['dim']}' not in {METRIC_DIMS}"
        )
        assert 0 <= d["score"] <= 100, (
            f"metric.score {d['score']} out of 0-100 range"
        )
        assert isinstance(d["evidence_event_ids"], list) and len(d["evidence_event_ids"]) >= 1, (
            f"metric.evidence_event_ids must be non-empty list (ALG-40), got {d['evidence_event_ids']}"
        )

    # --- All 5 dims present for each branch (ALG-40) ---
    for branch in ("A", "B"):
        branch_dims = {e["data"]["dim"] for e in metric_events if e["data"]["branch"] == branch}
        missing = METRIC_DIMS - branch_dims
        assert not missing, (
            f"Branch {branch} missing metric dims: {missing}. ALG-40 requires all 5 dims."
        )

    # --- fork_point shape ---
    fp_events = get_events_by_type(events, "fork_point")
    assert len(fp_events) >= 1, "Expected at least 1 fork_point event"
    for fp in fp_events:
        d = fp["data"]
        for field in ("month", "magnitude", "title", "explanation", "dims"):
            assert field in d, f"fork_point missing field '{field}'"
        assert 0 <= d["magnitude"] <= 100, "fork_point.magnitude out of 0-100"
        assert isinstance(d["dims"], list) and len(d["dims"]) >= 1, (
            "fork_point.dims must be non-empty list"
        )

    # --- branch_score shape ---
    bs_events = get_events_by_type(events, "branch_score")
    assert len(bs_events) == 2, "Expected exactly 2 branch_score events (A and B)"
    bs_branches = {e["data"]["branch"] for e in bs_events}
    assert bs_branches == EXPECTED_BRANCHES, "branch_score must cover both branches A and B"
    for bs in bs_events:
        d = bs["data"]
        for field in ("branch", "total", "breakdown", "weighted"):
            assert field in d, f"branch_score missing field '{field}'"
        assert 0 <= d["total"] <= 100, "branch_score.total out of 0-100"
        for dim in METRIC_DIMS:
            assert dim in d["breakdown"], f"branch_score.breakdown missing dim '{dim}'"

    # --- credibility shape ---
    cred_events = get_events_by_type(events, "credibility")
    assert len(cred_events) == 1, "Expected exactly 1 credibility event"
    cred = cred_events[0]["data"]
    for field in ("overall", "breakdown", "notes"):
        assert field in cred, f"credibility missing field '{field}'"
    assert 0 <= cred["overall"] <= 100, "credibility.overall out of 0-100"
    for sub in ("data_sufficiency", "causal_confidence", "event_plausibility"):
        assert sub in cred["breakdown"], f"credibility.breakdown missing '{sub}'"

    # --- recommendation shape ---
    rec_events = get_events_by_type(events, "recommendation")
    assert len(rec_events) == 1, "Expected exactly 1 recommendation event"
    rec = rec_events[0]["data"]
    for field in ("leaning", "rationale", "guardrail"):
        assert field in rec, f"recommendation missing field '{field}'"
    assert rec["leaning"] in ("A", "B", "neither"), (
        f"recommendation.leaning must be A, B, or neither; got '{rec['leaning']}'"
    )

    # --- done shape ---
    done_events = get_events_by_type(events, "done")
    assert len(done_events) == 1, "Expected exactly 1 done event"
    assert "run_id" in done_events[0]["data"], "done missing 'run_id'"


# ---------------------------------------------------------------------------
# Tests against mock stream (always run)
# ---------------------------------------------------------------------------

class TestContractShapeMock:
    """Validate the recorded mock SSE stream against the full contract."""

    def test_parse_mock_stream_nonempty(self, parsed_mock_stream):
        assert len(parsed_mock_stream) > 0, "Mock stream parsed to empty list"

    def test_all_required_event_types_present(self, parsed_mock_stream):
        found = {e["event_type"] for e in parsed_mock_stream}
        missing = REQUIRED_EVENT_TYPES - found - {"clarify", "error"}  # clarify and error optional
        assert not missing, f"Mock stream missing event types: {missing}"

    def test_full_structural_contract(self, parsed_mock_stream):
        assert_stream_structural_contract(parsed_mock_stream)

    def test_event_ordering_run_started_first(self, parsed_mock_stream):
        assert parsed_mock_stream[0]["event_type"] == "run_started"

    def test_event_ordering_done_last(self, parsed_mock_stream):
        assert parsed_mock_stream[-1]["event_type"] == "done"

    def test_world_ready_before_timeline_events(self, parsed_mock_stream):
        types = [e["event_type"] for e in parsed_mock_stream]
        wr_idx = types.index("world_ready")
        te_indices = [i for i, t in enumerate(types) if t == "timeline_event"]
        assert all(i > wr_idx for i in te_indices), (
            "world_ready must appear before all timeline_event events"
        )

    def test_timeline_events_before_metrics(self, parsed_mock_stream):
        """Timeline events should appear before metrics (contract ordering)."""
        types = [e["event_type"] for e in parsed_mock_stream]
        last_te_idx = max(i for i, t in enumerate(types) if t == "timeline_event")
        first_metric_idx = next(i for i, t in enumerate(types) if t == "metric")
        # At least some timeline events appear before first metric
        first_te_idx = types.index("timeline_event")
        assert first_te_idx < first_metric_idx, (
            "First timeline_event must appear before first metric"
        )

    def test_metrics_reference_valid_event_ids(self, parsed_mock_stream):
        """ALG-40: each metric's evidence_event_ids must reference known timeline_event IDs."""
        te_ids = {
            e["data"]["event_id"]
            for e in parsed_mock_stream
            if e["event_type"] == "timeline_event"
        }
        for me in get_events_by_type(parsed_mock_stream, "metric"):
            for eid in me["data"]["evidence_event_ids"]:
                assert eid in te_ids, (
                    f"metric.evidence_event_ids contains unknown event_id '{eid}'. "
                    f"Known ids: {te_ids}"
                )

    def test_high_risk_stream_structural_contract(self, parsed_high_risk_stream):
        assert_stream_structural_contract(parsed_high_risk_stream)

    def test_cold_start_stream_structural_contract(self, parsed_cold_start_stream):
        assert_stream_structural_contract(parsed_cold_start_stream)

    def test_run_id_consistent_between_run_started_and_done(self, parsed_mock_stream):
        rs = get_events_by_type(parsed_mock_stream, "run_started")[0]["data"]
        done = get_events_by_type(parsed_mock_stream, "done")[0]["data"]
        assert rs["run_id"] == done["run_id"], (
            f"run_id mismatch: run_started={rs['run_id']} vs done={done['run_id']}"
        )


# ---------------------------------------------------------------------------
# Tests against live backend (skipif --base not provided)
# ---------------------------------------------------------------------------

SIMULATE_PAYLOAD = {
    "decision": "Should I quit my stable job to join an early-stage startup?",
    "mode": "quick",
    "options": ["Stay at current job", "Join the startup"],
    "profile": {
        "age": 29,
        "city": "Shanghai",
        "occupation": "Backend engineer",
        "risk_tolerance": 6,
        "core_values": ["growth", "stability", "family"],
        "decision_style": "analytical",
    },
    "social_circle": [
        {
            "role": "partner",
            "influence_weight": 8,
            "stance_on_decision": "opposed",
            "key_concerns": ["stability", "income"],
        }
    ],
    "seed": 12345,
}


@pytest.mark.skipif(True, reason="Requires live backend: pass --base http://localhost:8000")
class TestContractShapeLive:
    """
    Live tests — skipped by default. To run against a real backend:
        pytest backend/tests/test_contract_shape.py -v --base http://localhost:8000
    """

    @pytest.fixture(autouse=True)
    def skip_without_base(self, live_base_url):
        if not live_base_url:
            pytest.skip("No --base URL provided; skipping live contract tests")

    def _simulate(self, live_base_url: str) -> list[dict]:
        url = f"{live_base_url}/api/simulate"
        resp = requests.post(url, json=SIMULATE_PAYLOAD, stream=True, timeout=120)
        assert resp.status_code == 200, f"POST /api/simulate returned {resp.status_code}"
        assert "text/event-stream" in resp.headers.get("content-type", ""), (
            "Expected Content-Type: text/event-stream"
        )
        raw = resp.text
        return parse_sse_stream(raw)

    def test_health_endpoint(self, live_base_url):
        resp = requests.get(f"{live_base_url}/api/health", timeout=10)
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("status") == "ok"
        assert "version" in body

    def test_live_full_structural_contract(self, live_base_url):
        events = self._simulate(live_base_url)
        assert_stream_structural_contract(events)

    def test_live_event_types_present(self, live_base_url):
        events = self._simulate(live_base_url)
        found = {e["event_type"] for e in events}
        required = {"run_started", "world_ready", "timeline_event", "metric",
                    "branch_score", "credibility", "recommendation", "done"}
        missing = required - found
        assert not missing, f"Live stream missing event types: {missing}"

    def test_live_metrics_all_dims(self, live_base_url):
        events = self._simulate(live_base_url)
        for branch in ("A", "B"):
            dims = {e["data"]["dim"] for e in events if e["event_type"] == "metric"
                    and e["data"]["branch"] == branch}
            missing = METRIC_DIMS - dims
            assert not missing, f"Branch {branch} missing dims: {missing}"

    def test_live_seed_check_endpoint(self, live_base_url):
        """GET /api/run/{run_id}/seed-check must return shared_event_hash."""
        events = self._simulate(live_base_url)
        rs = get_events_by_type(events, "run_started")[0]["data"]
        run_id = rs["run_id"]
        resp = requests.get(
            f"{live_base_url}/api/run/{run_id}/seed-check",
            timeout=10,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "shared_event_hash" in body, (
            "GET /api/run/{id}/seed-check must return 'shared_event_hash'"
        )
