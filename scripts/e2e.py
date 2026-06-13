#!/usr/bin/env python3
"""
scripts/e2e.py — E2E acceptance drivers for Lynsea P0 scenarios.

Covers:
  E2E-1  Job change: 2 timelines + 5 curves + ≥1 fork + credibility card
  E2E-2  End a relationship (high-risk): guardrail + probabilistic copy
  E2E-5  Paired counterfactual reproducibility (same seed → same shared_event_hash)
  E2E-6  Cold-start: default-value personas tagged "信息有限/limited info"

Usage:
  python scripts/e2e.py --base http://localhost:8000   # against live backend
  python scripts/e2e.py --mock                          # against built-in mock (no server)

Prints a PASS/FAIL table mapped to acceptance IDs.
"""
import argparse
import hashlib
import json
import re
import sys
from typing import Optional
import os

# ---------------------------------------------------------------------------
# Optional: live HTTP requests
# ---------------------------------------------------------------------------
try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# ---------------------------------------------------------------------------
# Shared SSE parsing
# ---------------------------------------------------------------------------

def parse_sse_stream(raw: str) -> list[dict]:
    """Parse raw SSE text into list of {event_type, data} dicts."""
    events = []
    current = {}
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("event:"):
            current["event_type"] = line[len("event:"):].strip()
        elif line.startswith("data:"):
            try:
                current["data"] = json.loads(line[len("data:"):].strip())
            except json.JSONDecodeError:
                current["data"] = line[len("data:"):].strip()
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events


def get_by_type(events: list[dict], etype: str) -> list[dict]:
    return [e for e in events if e.get("event_type") == etype]


# ---------------------------------------------------------------------------
# Mock streams (used when --mock flag or no server available)
# ---------------------------------------------------------------------------

def _mock_simulate(scenario: str, seed: Optional[int] = None) -> list[dict]:
    """Return a mock SSE event list for the given scenario."""
    # Import from test conftest if available, else use inline mocks
    _dir = os.path.dirname(os.path.abspath(__file__))
    _tests_dir = os.path.join(_dir, "..", "backend", "tests")
    sys.path.insert(0, _tests_dir)
    try:
        from conftest import (
            MOCK_SSE_STREAM,
            HIGH_RISK_SSE_STREAM,
            COLD_START_SSE_STREAM,
            parse_sse_stream as _parse,
        )
        if scenario == "high_risk":
            return _parse(HIGH_RISK_SSE_STREAM)
        elif scenario == "cold_start":
            return _parse(COLD_START_SSE_STREAM)
        else:
            return _parse(MOCK_SSE_STREAM)
    finally:
        sys.path.pop(0)


# ---------------------------------------------------------------------------
# Acceptance check helpers
# ---------------------------------------------------------------------------

METRIC_DIMS = {"economic", "career", "relationships", "mental_health", "autonomy"}
DETERMINISTIC_RE = re.compile(r'\b(will|definitely|certainly|guaranteed)\b', re.IGNORECASE)
PROBABILISTIC_RE = re.compile(
    r'\b(likely|probably|around|approximately|may|might|chance|probability)\b', re.IGNORECASE
)
SIMULATION_GUARDRAIL_RE = re.compile(
    r'(simulation|not a prophecy|not a prediction|这是模拟|不是预言)', re.IGNORECASE
)
HOW_TO_CHANGE_RE = re.compile(
    r'(how to change|change this outcome|how to improve|如何改变|counseling|consider)', re.IGNORECASE
)
LOW_CONFIDENCE_RE = re.compile(
    r'(信息有限|limited info|低置信|limited data|仅供参考)', re.IGNORECASE
)


def check_e2e1(events: list[dict]) -> list[tuple[str, bool, str]]:
    """
    E2E-1: Job change — 2 timelines + 5 curves + ≥1 fork + credibility card.
    Coverage: SYS-12, ALG-40, FE-10/11/12
    """
    results = []

    # 2 branches A and B both have timeline events
    te_a = get_by_type(events, "timeline_event")
    branches_in_te = {e["data"]["branch"] for e in te_a}
    results.append((
        "E2E-1 [SYS-12] Two parallel timelines (A and B)",
        {"A", "B"} == branches_in_te,
        f"Branches with timeline events: {branches_in_te}"
    ))

    # 5 metric dimensions for each branch
    for branch in ("A", "B"):
        branch_dims = {e["data"]["dim"] for e in events
                       if e["event_type"] == "metric" and e["data"]["branch"] == branch}
        missing = METRIC_DIMS - branch_dims
        results.append((
            f"E2E-1 [ALG-40] 5 metric dims for branch {branch}",
            not missing,
            f"Found: {branch_dims}. Missing: {missing}"
        ))

    # ≥1 fork point
    forks = get_by_type(events, "fork_point")
    results.append((
        "E2E-1 [SYS-12/FE-12] At least 1 fork point",
        len(forks) >= 1,
        f"Fork count: {len(forks)}"
    ))

    # Credibility card
    creds = get_by_type(events, "credibility")
    results.append((
        "E2E-1 [SYS-17] Credibility card present",
        len(creds) == 1,
        f"Credibility events: {len(creds)}"
    ))

    # Each metric references ≥1 evidence_event_ids (ALG-40)
    bad_metrics = [
        e["data"] for e in events
        if e["event_type"] == "metric"
        and not (isinstance(e["data"].get("evidence_event_ids"), list)
                 and len(e["data"]["evidence_event_ids"]) >= 1)
    ]
    results.append((
        "E2E-1 [ALG-40] All metrics reference ≥1 evidence_event_ids",
        len(bad_metrics) == 0,
        f"Metrics without evidence: {bad_metrics}"
    ))

    return results


def check_e2e2(events: list[dict]) -> list[tuple[str, bool, str]]:
    """
    E2E-2: End a relationship (high-risk).
    Coverage: SYS-15, SYS-16, FE-24/25
    """
    results = []

    # All NL text must be probabilistic (no deterministic language)
    nl_fields = []
    for e in events:
        d = e.get("data", {})
        etype = e.get("event_type", "")
        if etype in ("timeline_event", "fork_point"):
            for field in ("detail", "title", "explanation"):
                if field in d:
                    nl_fields.append(d[field])
        elif etype == "recommendation":
            for field in ("rationale",):
                if field in d:
                    nl_fields.append(d[field])

    det_violations = [(text, DETERMINISTIC_RE.search(text)) for text in nl_fields
                      if DETERMINISTIC_RE.search(text)]
    results.append((
        "E2E-2 [SYS-15] No deterministic language (will/definitely)",
        len(det_violations) == 0,
        f"Violations: {[(t[:80], m.group()) for t, m in det_violations]}"
    ))

    # Probabilistic language present
    prob_found = any(PROBABILISTIC_RE.search(text) for text in nl_fields)
    results.append((
        "E2E-2 [SYS-15] Probabilistic language present",
        prob_found,
        "Found probabilistic language" if prob_found else "No probabilistic language found"
    ))

    # Simulation guardrail present
    all_text = " ".join(
        str(v) for e in events for v in e.get("data", {}).values()
        if isinstance(v, str)
    )
    sim_guardrail = bool(SIMULATION_GUARDRAIL_RE.search(all_text))
    results.append((
        "E2E-2 [SYS-16] 'Simulation not prophecy' guardrail present",
        sim_guardrail,
        "Found simulation guardrail" if sim_guardrail else "Missing simulation guardrail"
    ))

    # How-to-change affordance
    how_to_change = bool(HOW_TO_CHANGE_RE.search(all_text))
    results.append((
        "E2E-2 [SYS-16] 'How to change outcome' affordance present",
        how_to_change,
        "Found how-to-change affordance" if how_to_change else "Missing how-to-change affordance"
    ))

    # recommendation.guardrail non-empty
    recs = get_by_type(events, "recommendation")
    guardrail_ok = (
        len(recs) == 1
        and isinstance(recs[0]["data"].get("guardrail"), str)
        and len(recs[0]["data"]["guardrail"]) > 10
    )
    results.append((
        "E2E-2 [FE-24] recommendation.guardrail field is non-empty",
        guardrail_ok,
        f"guardrail: {recs[0]['data'].get('guardrail', '')[:80]!r}" if recs else "No recommendation event"
    ))

    return results


def check_e2e5(events_run1: list[dict], events_run2: list[dict],
               seed_hash_1: Optional[str] = None,
               seed_hash_2: Optional[str] = None) -> list[tuple[str, bool, str]]:
    """
    E2E-5: Paired counterfactual reproducibility.
    Same seed → same shared_event_hash across 2 runs.
    Coverage: ALG-20, ALG-21, NFR-01
    """
    results = []

    # Compute local shared_event_hash from stream if not provided from API
    def local_hash(events):
        skeleton_a = [
            {"month": e["data"]["month"], "kind": e["data"]["kind"], "title": e["data"]["title"]}
            for e in events
            if e["event_type"] == "timeline_event"
            and e["data"]["branch"] == "A"
            and e["data"]["kind"] == "skeleton"
        ]
        canon = json.dumps(skeleton_a, sort_keys=True)
        return hashlib.sha256(canon.encode()).hexdigest()

    h1 = seed_hash_1 or local_hash(events_run1)
    h2 = seed_hash_2 or local_hash(events_run2)

    results.append((
        "E2E-5 [NFR-01/ALG-20] shared_event_hash EQUAL across same-seed runs",
        h1 == h2,
        f"Run1 hash: {h1[:16]}... Run2 hash: {h2[:16]}..."
    ))

    # Metric values identical across runs
    def metric_summary(events):
        return sorted(
            [(e["data"]["branch"], e["data"]["month"], e["data"]["dim"], e["data"]["score"])
             for e in events if e["event_type"] == "metric"]
        )

    m1 = metric_summary(events_run1)
    m2 = metric_summary(events_run2)
    results.append((
        "E2E-5 [NFR-01] Metric curves identical across same-seed runs",
        m1 == m2,
        f"Run1 metric count: {len(m1)}, Run2 metric count: {len(m2)}, "
        + ("MATCH" if m1 == m2 else "DIFFER")
    ))

    # Event sequence identical
    types_1 = [e["event_type"] for e in events_run1]
    types_2 = [e["event_type"] for e in events_run2]
    results.append((
        "E2E-5 [NFR-01] Event sequence identical across same-seed runs",
        types_1 == types_2,
        f"Run1 event types: {types_1}, Run2: {types_2}" if types_1 != types_2
        else "Event sequences match"
    ))

    # ALG-20: skeleton events same months between A and B in run 1
    sk_a_months = sorted(
        e["data"]["month"] for e in events_run1
        if e["event_type"] == "timeline_event"
        and e["data"]["branch"] == "A"
        and e["data"]["kind"] == "skeleton"
    )
    sk_b_months = sorted(
        e["data"]["month"] for e in events_run1
        if e["event_type"] == "timeline_event"
        and e["data"]["branch"] == "B"
        and e["data"]["kind"] == "skeleton"
    )
    results.append((
        "E2E-5 [ALG-20] Branch A and B share same skeleton event months",
        sk_a_months == sk_b_months,
        f"A months: {sk_a_months}, B months: {sk_b_months}"
    ))

    return results


def check_e2e6(events: list[dict]) -> list[tuple[str, bool, str]]:
    """
    E2E-6: Cold-start — default-value personas tagged "信息有限/limited info".
    Coverage: ALG-04, FE-23
    """
    results = []

    # At least one persona has confidence "low"
    wr_events = get_by_type(events, "world_ready")
    low_conf_personas = []
    all_personas = []
    if wr_events:
        for p in wr_events[0]["data"].get("personas", []):
            all_personas.append(p)
            if p.get("confidence") == "low":
                low_conf_personas.append(p)

    results.append((
        "E2E-6 [ALG-04] At least 1 low-confidence persona in cold-start",
        len(low_conf_personas) >= 1,
        f"Low-conf personas: {[p['role'] for p in low_conf_personas]}, "
        f"All personas: {[p['role'] for p in all_personas]}"
    ))

    # The "limited info" tag appears in NL text
    all_text = " ".join(
        str(v) for e in events for v in e.get("data", {}).values()
        if isinstance(v, str)
    )
    has_limited_info = bool(LOW_CONFIDENCE_RE.search(all_text))
    results.append((
        "E2E-6 [ALG-04/FE-23] '信息有限/limited info' annotation appears in output",
        has_limited_info,
        "Found limited-info annotation" if has_limited_info else "Missing limited-info annotation"
    ))

    # Credibility overall is lower for cold-start (< 70)
    creds = get_by_type(events, "credibility")
    if creds:
        cred_overall = creds[0]["data"].get("overall", 100)
        results.append((
            "E2E-6 [ALG-42] Credibility overall lower for cold-start (< 70)",
            cred_overall < 70,
            f"Credibility overall: {cred_overall}"
        ))
    else:
        results.append((
            "E2E-6 [ALG-42] Credibility card present in cold-start stream",
            False,
            "No credibility event found"
        ))

    # Recommendation leaning is "neither" for cold-start (insufficient info)
    recs = get_by_type(events, "recommendation")
    if recs:
        leaning = recs[0]["data"].get("leaning", "")
        results.append((
            "E2E-6 Recommendation does not confidently pick a branch (limited info)",
            leaning == "neither",
            f"Leaning: {leaning!r} (expected 'neither' for cold-start)"
        ))

    return results


# ---------------------------------------------------------------------------
# Live backend scenario runners
# ---------------------------------------------------------------------------

def _live_simulate(base_url: str, payload: dict, timeout: int = 120) -> list[dict]:
    if not HAS_REQUESTS:
        raise RuntimeError("requests library not available; run: pip install requests")
    resp = _requests.post(
        f"{base_url}/api/simulate",
        json=payload,
        stream=True,
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"POST /api/simulate returned {resp.status_code}: {resp.text[:200]}")
    return parse_sse_stream(resp.text)


def _live_seed_check(base_url: str, run_id: str) -> str:
    resp = _requests.get(f"{base_url}/api/run/{run_id}/seed-check", timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"GET seed-check returned {resp.status_code}: {resp.text[:200]}")
    return resp.json()["shared_event_hash"]


# ---------------------------------------------------------------------------
# Scenario payloads
# ---------------------------------------------------------------------------

E2E1_PAYLOAD = {
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
        {"role": "partner", "influence_weight": 8, "stance_on_decision": "opposed"},
        {"role": "mother", "influence_weight": 6, "stance_on_decision": "opposed"},
    ],
    "seed": 42,
}

E2E2_PAYLOAD = {
    "decision": "Should I end my 3-year relationship?",
    "mode": "quick",
    "options": ["End the relationship", "Stay in the relationship"],
    "profile": {
        "age": 28,
        "city": "Shanghai",
        "occupation": "Designer",
        "risk_tolerance": 4,
        "core_values": ["relationships", "stability", "family"],
        "decision_style": "intuitive",
    },
    "social_circle": [
        {"role": "partner", "influence_weight": 9, "stance_on_decision": "opposed"},
    ],
    "seed": 99,
}

E2E5_PAYLOAD = {
    "decision": "Should I move to a new city for a better job opportunity?",
    "mode": "quick",
    "options": ["Accept the offer and move", "Stay and look for local options"],
    "profile": {
        "age": 30,
        "city": "Chengdu",
        "occupation": "Product Manager",
        "risk_tolerance": 5,
        "core_values": ["growth", "family"],
        "decision_style": "balanced",
    },
    "seed": 7777,
}

E2E6_PAYLOAD = {
    "decision": "Should I start my own business?",
    "mode": "quick",
    # Minimal profile — triggers cold-start defaults
    "profile": {
        "age": 35,
    },
    "seed": 111,
}


# ---------------------------------------------------------------------------
# Main: run scenarios and print PASS/FAIL table
# ---------------------------------------------------------------------------

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"


def print_results(scenario_id: str, check_results: list[tuple]):
    all_pass = all(ok for _, ok, _ in check_results)
    overall = PASS if all_pass else FAIL
    print(f"\n{'='*70}")
    print(f"  {scenario_id}  Overall: {overall}")
    print(f"{'='*70}")
    for name, ok, detail in check_results:
        status = PASS if ok else FAIL
        print(f"  [{status}] {name}")
        if not ok or "--verbose" in sys.argv:
            print(f"         {detail}")
    return all_pass


def run_all(base_url: Optional[str], use_mock: bool) -> dict[str, bool]:
    """Run all E2E scenarios. Returns dict scenario_id -> all_pass."""
    summary = {}
    live = base_url is not None and not use_mock

    print(f"\nLynsea E2E Acceptance Driver")
    print(f"Mode: {'LIVE @ ' + base_url if live else 'MOCK (no server)'}")

    # ---- E2E-1 ----
    print(f"\nRunning E2E-1 (job change)...")
    if live:
        try:
            events = _live_simulate(base_url, E2E1_PAYLOAD)
        except Exception as e:
            print(f"  ERROR running E2E-1: {e}")
            summary["E2E-1"] = False
            events = []
    else:
        events = _mock_simulate("standard")

    if events:
        results = check_e2e1(events)
        summary["E2E-1"] = print_results("E2E-1", results)

    # ---- E2E-2 ----
    print(f"\nRunning E2E-2 (end relationship — high risk)...")
    if live:
        try:
            events2 = _live_simulate(base_url, E2E2_PAYLOAD)
        except Exception as e:
            print(f"  ERROR running E2E-2: {e}")
            summary["E2E-2"] = False
            events2 = []
    else:
        events2 = _mock_simulate("high_risk")

    if events2:
        results2 = check_e2e2(events2)
        summary["E2E-2"] = print_results("E2E-2", results2)

    # ---- E2E-5 ----
    print(f"\nRunning E2E-5 (paired counterfactual reproducibility)...")
    if live:
        try:
            events5a = _live_simulate(base_url, E2E5_PAYLOAD)
            events5b = _live_simulate(base_url, E2E5_PAYLOAD)
            rs_a = next(e["data"] for e in events5a if e["event_type"] == "run_started")
            rs_b = next(e["data"] for e in events5b if e["event_type"] == "run_started")
            hash_a = _live_seed_check(base_url, rs_a["run_id"])
            hash_b = _live_seed_check(base_url, rs_b["run_id"])
        except Exception as e:
            print(f"  ERROR running E2E-5: {e}")
            summary["E2E-5"] = False
            events5a = events5b = []
            hash_a = hash_b = None
    else:
        # For mock, run same mock stream twice
        events5a = _mock_simulate("standard")
        events5b = _mock_simulate("standard")
        hash_a = hash_b = None  # will be computed from stream

    if events5a and events5b:
        results5 = check_e2e5(events5a, events5b, hash_a, hash_b)
        summary["E2E-5"] = print_results("E2E-5", results5)

    # ---- E2E-6 ----
    print(f"\nRunning E2E-6 (cold-start — limited info)...")
    if live:
        try:
            events6 = _live_simulate(base_url, E2E6_PAYLOAD)
        except Exception as e:
            print(f"  ERROR running E2E-6: {e}")
            summary["E2E-6"] = False
            events6 = []
    else:
        events6 = _mock_simulate("cold_start")

    if events6:
        results6 = check_e2e6(events6)
        summary["E2E-6"] = print_results("E2E-6", results6)

    # ---- Summary table ----
    print(f"\n{'='*70}")
    print("  SUMMARY")
    print(f"{'='*70}")
    all_ok = True
    for sid, ok in sorted(summary.items()):
        status = PASS if ok else FAIL
        print(f"  [{status}] {sid}")
        if not ok:
            all_ok = False

    print(f"\n  Overall: {'ALL PASS' if all_ok else 'SOME FAIL'}")
    print(f"{'='*70}\n")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Lynsea E2E acceptance driver for E2E-1/2/5/6"
    )
    parser.add_argument(
        "--base",
        default=None,
        help="Base URL of live backend, e.g. http://localhost:8000",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock streams (no live server required)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detail for all checks (not just failures)",
    )
    args = parser.parse_args()

    if not args.base and not args.mock:
        # Default to mock if no --base given
        print("No --base provided; running in mock mode (use --base http://localhost:8000 for live).")
        args.mock = True

    results = run_all(args.base, args.mock)

    # Exit with non-zero if any scenario failed
    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
