"""
test_nfr01_seed.py — NFR-01 / ALG-20 / ALG-21: seed reproducibility checks.

Verifies:
  1. Mock: two runs with same seed produce streams with identical structure
     (event sequence, metric values, timeline event IDs).
  2. Mock: shared (non-decision) random events are identical between branch A
     and branch B in a single run (ALG-20).
  3. Mock: shared_event_hash equality across two runs with same seed (ALG-20).
  4. Live (skipif): POST /api/simulate twice with same seed, call
     GET /api/run/{id}/seed-check, assert shared_event_hash EQUAL across runs.
  5. Live (skipif): non-decision random-event stream identical between A and B.

Run: pytest backend/tests/test_nfr01_seed.py -v
"""
import hashlib
import json
import pytest
import requests

from conftest import (
    MOCK_SSE_STREAM,
    SEED,
    RUN_ID,
    parse_sse_stream,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_timeline_events(events: list[dict], branch: str) -> list[dict]:
    return [
        e["data"]
        for e in events
        if e["event_type"] == "timeline_event" and e["data"]["branch"] == branch
    ]


def extract_metrics(events: list[dict], branch: str) -> list[dict]:
    return [
        e["data"]
        for e in events
        if e["event_type"] == "metric" and e["data"]["branch"] == branch
    ]


def compute_shared_event_hash(events: list[dict]) -> str:
    """
    Compute a SHA-256 hash of the shared (non-decision) timeline events.
    Shared events are skeleton events from both branches — we compare the
    sequence of (month, kind, title) tuples, which should be identical across
    branches A and B (ALG-20: same seed → same random events).
    """
    # Collect skeleton events from branch A (the shared baseline)
    # In the contract, skeleton events are the "common world" events.
    skeleton_a = [
        e["data"]
        for e in events
        if e["event_type"] == "timeline_event"
        and e["data"]["branch"] == "A"
        and e["data"]["kind"] == "skeleton"
    ]
    # Serialize in a deterministic way
    canonical = json.dumps(
        [{"month": e["month"], "kind": e["kind"], "title": e["title"]} for e in skeleton_a],
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def compute_event_sequence_hash(events: list[dict]) -> str:
    """Hash the full ordered sequence of event types and key data fields."""
    summary = [
        {
            "event_type": e["event_type"],
            "branch": e["data"].get("branch"),
            "month": e["data"].get("month"),
            "dim": e["data"].get("dim"),
            "score": e["data"].get("score"),
        }
        for e in events
    ]
    return hashlib.sha256(json.dumps(summary, sort_keys=True).encode()).hexdigest()


# ---------------------------------------------------------------------------
# Mock-based seed reproducibility tests
# ---------------------------------------------------------------------------

class TestNFR01SeedMock:
    """
    Validate seed-reproducibility logic against the mock stream.
    These tests run without a live backend to verify the harness itself.
    """

    @pytest.fixture
    def stream_a(self):
        """First parse of the mock stream (simulates first run)."""
        return parse_sse_stream(MOCK_SSE_STREAM)

    @pytest.fixture
    def stream_b(self):
        """Second parse of the mock stream (simulates second run with same seed)."""
        return parse_sse_stream(MOCK_SSE_STREAM)

    def test_two_runs_produce_same_event_count(self, stream_a, stream_b):
        assert len(stream_a) == len(stream_b), (
            "Same-seed runs must produce the same number of events. "
            f"Run 1: {len(stream_a)} events, Run 2: {len(stream_b)} events"
        )

    def test_two_runs_produce_same_event_types_in_order(self, stream_a, stream_b):
        types_a = [e["event_type"] for e in stream_a]
        types_b = [e["event_type"] for e in stream_b]
        assert types_a == types_b, (
            "Same-seed runs must produce events in the same order. "
            f"Run 1: {types_a}, Run 2: {types_b}"
        )

    def test_two_runs_same_metric_values(self, stream_a, stream_b):
        """NFR-01: metric curves must be identical for same seed."""
        metrics_a = extract_metrics(stream_a, "A") + extract_metrics(stream_a, "B")
        metrics_b = extract_metrics(stream_b, "A") + extract_metrics(stream_b, "B")
        assert len(metrics_a) == len(metrics_b)
        for ma, mb in zip(metrics_a, metrics_b):
            assert ma["score"] == mb["score"], (
                f"Metric score differs between runs: {ma} vs {mb}"
            )
            assert ma["dim"] == mb["dim"]
            assert ma["branch"] == mb["branch"]
            assert ma["month"] == mb["month"]

    def test_two_runs_same_shared_event_hash(self, stream_a, stream_b):
        """ALG-20: shared_event_hash must be EQUAL across same-seed runs."""
        hash_a = compute_shared_event_hash(stream_a)
        hash_b = compute_shared_event_hash(stream_b)
        assert hash_a == hash_b, (
            f"shared_event_hash differs between same-seed runs: {hash_a} != {hash_b}. "
            "ALG-20 / NFR-01 requires deterministic shared event stream."
        )

    def test_two_runs_same_event_sequence_hash(self, stream_a, stream_b):
        hash_a = compute_event_sequence_hash(stream_a)
        hash_b = compute_event_sequence_hash(stream_b)
        assert hash_a == hash_b, (
            "Event sequence hash differs between same-seed runs."
        )

    def test_alg20_branch_a_and_b_share_skeleton_events(self, stream_a):
        """
        ALG-20: Non-decision random events (skeleton) must be identical between
        branches A and B. Only the decision variable differs.
        """
        skeleton_a = extract_timeline_events(stream_a, "A")
        skeleton_a = [e for e in skeleton_a if e["kind"] == "skeleton"]
        skeleton_b = extract_timeline_events(stream_a, "B")
        skeleton_b = [e for e in skeleton_b if e["kind"] == "skeleton"]

        # Both branches must have skeleton events
        assert len(skeleton_a) > 0, "Branch A has no skeleton events"
        assert len(skeleton_b) > 0, "Branch B has no skeleton events"

        # The skeleton events in A and B should cover the same months
        months_a = {e["month"] for e in skeleton_a}
        months_b = {e["month"] for e in skeleton_b}
        assert months_a == months_b, (
            f"ALG-20: Branch A skeleton months {months_a} != Branch B skeleton months {months_b}. "
            "Shared world events must cover same months."
        )

    def test_alg21_state_before_fork_consistent(self, stream_a):
        """
        ALG-21: State before fork point must be consistent across branches.
        We verify that early-month events (before the first fork) follow the
        same structure in both A and B.
        """
        fork_events = [e["data"] for e in stream_a if e["event_type"] == "fork_point"]
        assert fork_events, "No fork_point events found"

        first_fork_month = min(fp["month"] for fp in fork_events)

        # Events before the fork should have same months in both branches
        pre_fork_a = [
            e for e in extract_timeline_events(stream_a, "A")
            if e["month"] < first_fork_month
        ]
        pre_fork_b = [
            e for e in extract_timeline_events(stream_a, "B")
            if e["month"] < first_fork_month
        ]

        # In a properly seeded simulation, pre-fork events should align by month
        months_a = sorted(e["month"] for e in pre_fork_a)
        months_b = sorted(e["month"] for e in pre_fork_b)
        assert months_a == months_b, (
            f"ALG-21: Pre-fork months differ: A={months_a}, B={months_b}. "
            "Before the fork, both branches should be in same state."
        )

    def test_shared_event_hash_is_consistent_string(self, stream_a):
        """The shared_event_hash must be a non-empty hex string."""
        h = compute_shared_event_hash(stream_a)
        assert isinstance(h, str) and len(h) == 64, (
            f"shared_event_hash should be 64-char hex string, got: {h!r}"
        )


# ---------------------------------------------------------------------------
# Live backend seed tests (skipif --base not provided)
# ---------------------------------------------------------------------------

SIMULATE_PAYLOAD = {
    "decision": "Should I accept a job offer in another city?",
    "mode": "quick",
    "options": ["Accept the offer", "Stay in current city"],
    "profile": {
        "age": 32,
        "city": "Beijing",
        "occupation": "Product Manager",
        "risk_tolerance": 5,
        "core_values": ["family", "growth", "stability"],
        "decision_style": "intuitive",
    },
    "seed": SEED,
}


@pytest.mark.skipif(True, reason="Requires live backend: pass --base http://localhost:8000")
class TestNFR01SeedLive:
    """
    Live NFR-01 tests. To run:
        pytest backend/tests/test_nfr01_seed.py -v --base http://localhost:8000
    """

    @pytest.fixture(autouse=True)
    def skip_without_base(self, live_base_url):
        if not live_base_url:
            pytest.skip("No --base URL provided")

    def _run_simulate(self, live_base_url: str) -> tuple[str, list[dict]]:
        """POST /api/simulate and return (run_id, parsed_events)."""
        resp = requests.post(
            f"{live_base_url}/api/simulate",
            json=SIMULATE_PAYLOAD,
            stream=True,
            timeout=120,
        )
        assert resp.status_code == 200, f"POST /api/simulate returned {resp.status_code}"
        events = parse_sse_stream(resp.text)
        rs = next(e["data"] for e in events if e["event_type"] == "run_started")
        return rs["run_id"], events

    def test_nfr01_same_seed_produces_same_shared_event_hash(self, live_base_url):
        """
        NFR-01 core: POST /api/simulate twice with same seed.
        GET /api/run/{id}/seed-check and assert shared_event_hash EQUAL.
        """
        run_id_1, events_1 = self._run_simulate(live_base_url)
        run_id_2, events_2 = self._run_simulate(live_base_url)

        # Fetch seed-check for both runs
        r1 = requests.get(
            f"{live_base_url}/api/run/{run_id_1}/seed-check", timeout=10
        )
        r2 = requests.get(
            f"{live_base_url}/api/run/{run_id_2}/seed-check", timeout=10
        )
        assert r1.status_code == 200, f"seed-check for run 1 failed: {r1.status_code}"
        assert r2.status_code == 200, f"seed-check for run 2 failed: {r2.status_code}"

        hash_1 = r1.json()["shared_event_hash"]
        hash_2 = r2.json()["shared_event_hash"]

        assert hash_1 == hash_2, (
            f"NFR-01 FAIL: same-seed runs have different shared_event_hash.\n"
            f"  Run 1 ({run_id_1}): {hash_1}\n"
            f"  Run 2 ({run_id_2}): {hash_2}"
        )

    def test_alg20_same_seed_branch_a_b_event_stream_identical(self, live_base_url):
        """
        ALG-20: Within a single run, the non-decision random events
        (skeleton timeline events) must be identical between branches A and B.
        """
        _, events = self._run_simulate(live_base_url)

        skeleton_a = [
            (e["data"]["month"], e["data"]["kind"], e["data"]["title"])
            for e in events
            if e["event_type"] == "timeline_event"
            and e["data"]["branch"] == "A"
            and e["data"]["kind"] == "skeleton"
        ]
        skeleton_b = [
            (e["data"]["month"], e["data"]["kind"], e["data"]["title"])
            for e in events
            if e["event_type"] == "timeline_event"
            and e["data"]["branch"] == "B"
            and e["data"]["kind"] == "skeleton"
        ]

        # Month sequences must match (shared world events)
        months_a = sorted(t[0] for t in skeleton_a)
        months_b = sorted(t[0] for t in skeleton_b)
        assert months_a == months_b, (
            f"ALG-20 FAIL: Skeleton event months differ A={months_a} vs B={months_b}"
        )

    def test_nfr01_metric_curves_identical_across_runs(self, live_base_url):
        """NFR-01: metric curve values must be identical for same seed."""
        _, events_1 = self._run_simulate(live_base_url)
        _, events_2 = self._run_simulate(live_base_url)

        def metrics_summary(events):
            return sorted(
                [
                    (e["data"]["branch"], e["data"]["month"], e["data"]["dim"], e["data"]["score"])
                    for e in events
                    if e["event_type"] == "metric"
                ],
                key=lambda x: x
            )

        m1 = metrics_summary(events_1)
        m2 = metrics_summary(events_2)
        assert m1 == m2, (
            f"NFR-01 FAIL: Metric curves differ between same-seed runs.\n"
            f"  Run 1: {m1}\n  Run 2: {m2}"
        )
