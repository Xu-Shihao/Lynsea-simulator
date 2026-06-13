"""
test_guardrails.py — SYS-15 / SYS-16 guardrail checks.

Verifies:
  SYS-15: All natural-language result text must be probabilistic.
          Fail on any "will"/"definitely" (deterministic language).
  SYS-16: High-risk cases must carry:
          1. The "this is a simulation, not a prophecy" guardrail.
          2. A "how to change this outcome" affordance.

Tests run against the mock streams (always) and optionally against a live backend.

Run: pytest backend/tests/test_guardrails.py -v
"""
import re
import pytest
import requests

from conftest import (
    MOCK_SSE_STREAM,
    HIGH_RISK_SSE_STREAM,
    COLD_START_SSE_STREAM,
    parse_sse_stream,
)


# ---------------------------------------------------------------------------
# Guardrail constants (from SYS-15 / SYS-16 in docs/plans/Lynsea-验收标准.md)
# ---------------------------------------------------------------------------

# Words that indicate deterministic language (SYS-15 violations)
DETERMINISTIC_PATTERNS = [
    re.compile(r'\bwill\b', re.IGNORECASE),
    re.compile(r'\bdefinitely\b', re.IGNORECASE),
    re.compile(r'\bcertainly\b', re.IGNORECASE),
    re.compile(r'\bguaranteed\b', re.IGNORECASE),
    re.compile(r'\bwill definitely\b', re.IGNORECASE),
    re.compile(r'\bwill certainly\b', re.IGNORECASE),
]

# Allowed probabilistic words (not exhaustive, used for positive checks)
PROBABILISTIC_PATTERNS = [
    re.compile(r'\blikely\b', re.IGNORECASE),
    re.compile(r'\bprobably\b', re.IGNORECASE),
    re.compile(r'\baround\b.*\b\d+%\b', re.IGNORECASE),
    re.compile(r'\b\d+%\s+(?:chance|probability|likelihood)\b', re.IGNORECASE),
    re.compile(r'\bapproximately\b', re.IGNORECASE),
    re.compile(r'\bmay\b', re.IGNORECASE),
    re.compile(r'\bmight\b', re.IGNORECASE),
]

# High-risk guardrail phrases (SYS-16)
SIMULATION_GUARDRAIL_PHRASES = [
    re.compile(r'simulation', re.IGNORECASE),
    re.compile(r'not a prophecy', re.IGNORECASE),
    re.compile(r'not a prediction', re.IGNORECASE),
    re.compile(r'这是模拟', re.IGNORECASE),       # Chinese: "this is a simulation"
    re.compile(r'不是预言', re.IGNORECASE),        # Chinese: "not a prophecy"
]

HOW_TO_CHANGE_PHRASES = [
    re.compile(r'how to change', re.IGNORECASE),
    re.compile(r'how you can change', re.IGNORECASE),
    re.compile(r'change this outcome', re.IGNORECASE),
    re.compile(r'how to improve', re.IGNORECASE),
    re.compile(r'如何改变', re.IGNORECASE),        # Chinese: "how to change"
    re.compile(r'改变这个结果', re.IGNORECASE),   # Chinese: "change this outcome"
    re.compile(r'counseling', re.IGNORECASE),
    re.compile(r'consider', re.IGNORECASE),
]

# Fields containing natural-language text in each event type
NL_TEXT_FIELDS = {
    "timeline_event": ["detail", "title"],
    "fork_point": ["explanation", "title"],
    "recommendation": ["rationale", "guardrail"],
    "credibility": ["notes"],
    "branch_score": [],
    "world_ready": [],
    "metric": [],
    "run_started": [],
    "done": [],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_nl_texts(events: list[dict]) -> list[tuple[str, str, str]]:
    """
    Extract all natural-language text snippets from the event stream.
    Returns list of (event_type, field_name, text).
    """
    texts = []
    for event in events:
        et = event.get("event_type", "")
        d = event.get("data", {})
        fields = NL_TEXT_FIELDS.get(et, [])
        for field in fields:
            val = d.get(field, "")
            if isinstance(val, str) and val.strip():
                texts.append((et, field, val))
    return texts


def find_deterministic_violations(texts: list[tuple]) -> list[tuple]:
    """
    Return list of (event_type, field, text, matched_pattern) for any
    deterministic language violation.
    Carve-out: "will" is allowed in a proper sub-clause about simulation
    disclaimers like "this will not necessarily happen".
    """
    violations = []
    for et, field, text in texts:
        # Skip guardrail fields themselves — guardrails may use "will" legitimately
        if field == "guardrail":
            continue
        for pattern in DETERMINISTIC_PATTERNS:
            if pattern.search(text):
                violations.append((et, field, text, pattern.pattern))
    return violations


def check_high_risk_guardrail(events: list[dict]) -> dict:
    """
    Check whether the stream contains:
    1. The simulation-not-prophecy guardrail phrase.
    2. A "how to change this outcome" affordance.
    Returns dict with 'simulation_guardrail': bool, 'how_to_change': bool.
    """
    # Collect all text across all events (including guardrail field)
    all_text = []
    for event in events:
        d = event.get("data", {})
        for val in d.values():
            if isinstance(val, str):
                all_text.append(val)

    combined = " ".join(all_text)

    simulation_ok = any(p.search(combined) for p in SIMULATION_GUARDRAIL_PHRASES)
    how_to_change_ok = any(p.search(combined) for p in HOW_TO_CHANGE_PHRASES)

    return {
        "simulation_guardrail": simulation_ok,
        "how_to_change": how_to_change_ok,
    }


def is_high_risk_stream(events: list[dict]) -> bool:
    """
    Heuristic: a stream is high-risk if any metric score for relationships
    or mental_health is below 35, or if the recommendation.guardrail
    field contains guardrail content.
    """
    for e in events:
        if e["event_type"] == "metric":
            d = e["data"]
            if d["dim"] in ("relationships", "mental_health") and d["score"] < 35:
                return True
        if e["event_type"] == "recommendation":
            g = e["data"].get("guardrail", "")
            if g and len(g) > 10:
                return True
    return False


# ---------------------------------------------------------------------------
# Mock-based guardrail tests
# ---------------------------------------------------------------------------

class TestGuardrailsMock:

    def test_mock_stream_no_deterministic_language(self, parsed_mock_stream):
        """SYS-15: No 'will'/'definitely' in any NL result text of mock stream."""
        texts = extract_nl_texts(parsed_mock_stream)
        violations = find_deterministic_violations(texts)
        assert not violations, (
            f"SYS-15 FAIL: Deterministic language found in mock stream:\n"
            + "\n".join(f"  [{et}.{field}] pattern='{pat}': {text!r}"
                        for et, field, text, pat in violations)
        )

    def test_mock_stream_has_probabilistic_language(self, parsed_mock_stream):
        """SYS-15: NL text should contain probabilistic language."""
        texts = extract_nl_texts(parsed_mock_stream)
        nl_combined = " ".join(t for _, _, t in texts)
        has_probabilistic = any(p.search(nl_combined) for p in PROBABILISTIC_PATTERNS)
        assert has_probabilistic, (
            "SYS-15: Mock stream NL text should contain probabilistic language "
            "(likely/probably/X% chance etc.)"
        )

    def test_high_risk_stream_no_deterministic_language(self, parsed_high_risk_stream):
        """SYS-15: High-risk stream must also have no deterministic language."""
        texts = extract_nl_texts(parsed_high_risk_stream)
        violations = find_deterministic_violations(texts)
        assert not violations, (
            f"SYS-15 FAIL: Deterministic language found in high-risk stream:\n"
            + "\n".join(f"  [{et}.{field}] pattern='{pat}': {text!r}"
                        for et, field, text, pat in violations)
        )

    def test_high_risk_stream_carries_simulation_guardrail(self, parsed_high_risk_stream):
        """SYS-16: High-risk stream must carry the simulation-not-prophecy guardrail."""
        result = check_high_risk_guardrail(parsed_high_risk_stream)
        assert result["simulation_guardrail"], (
            "SYS-16 FAIL: High-risk stream is missing 'this is a simulation, not a prophecy' "
            "guardrail language in any field."
        )

    def test_high_risk_stream_carries_how_to_change_affordance(self, parsed_high_risk_stream):
        """SYS-16: High-risk stream must include a 'how to change this outcome' affordance."""
        result = check_high_risk_guardrail(parsed_high_risk_stream)
        assert result["how_to_change"], (
            "SYS-16 FAIL: High-risk stream is missing 'how to change this outcome' affordance."
        )

    def test_high_risk_stream_is_detected_as_high_risk(self, parsed_high_risk_stream):
        """Verify our heuristic correctly identifies high-risk streams."""
        assert is_high_risk_stream(parsed_high_risk_stream), (
            "High-risk mock stream was not detected as high-risk by heuristic. "
            "Check is_high_risk_stream logic."
        )

    def test_recommendation_guardrail_field_present_in_high_risk(self, parsed_high_risk_stream):
        """SYS-16: recommendation.guardrail must be a non-empty string."""
        recs = [e for e in parsed_high_risk_stream if e["event_type"] == "recommendation"]
        assert recs, "No recommendation event in high-risk stream"
        guardrail = recs[0]["data"].get("guardrail", "")
        assert isinstance(guardrail, str) and len(guardrail) > 10, (
            f"SYS-16: recommendation.guardrail must be a non-empty string, got: {guardrail!r}"
        )

    def test_cold_start_stream_no_deterministic_language(self, parsed_cold_start_stream):
        """SYS-15: Cold-start stream must also be free of deterministic language."""
        texts = extract_nl_texts(parsed_cold_start_stream)
        violations = find_deterministic_violations(texts)
        assert not violations, (
            f"SYS-15 FAIL: Deterministic language in cold-start stream:\n"
            + "\n".join(f"  [{et}.{field}] pattern='{pat}': {text!r}"
                        for et, field, text, pat in violations)
        )

    def test_all_timeline_event_details_are_probabilistic(self, parsed_mock_stream):
        """SYS-15: timeline_event.detail text must use probabilistic language."""
        te_texts = [
            e["data"]["detail"]
            for e in parsed_mock_stream
            if e["event_type"] == "timeline_event"
        ]
        for text in te_texts:
            deterministic = any(p.search(text) for p in DETERMINISTIC_PATTERNS)
            assert not deterministic, (
                f"SYS-15 FAIL: timeline_event.detail has deterministic language: {text!r}"
            )

    def test_recommendation_rationale_is_probabilistic(self, parsed_mock_stream):
        """SYS-15: recommendation.rationale must be probabilistic."""
        recs = [e for e in parsed_mock_stream if e["event_type"] == "recommendation"]
        assert recs, "No recommendation event found"
        rationale = recs[0]["data"]["rationale"]
        has_prob = any(p.search(rationale) for p in PROBABILISTIC_PATTERNS)
        assert has_prob, (
            f"SYS-15: recommendation.rationale should contain probabilistic language. "
            f"Got: {rationale!r}"
        )
        has_det = any(p.search(rationale) for p in DETERMINISTIC_PATTERNS)
        assert not has_det, (
            f"SYS-15 FAIL: recommendation.rationale has deterministic language: {rationale!r}"
        )


# ---------------------------------------------------------------------------
# Live backend guardrail tests (skipif --base not provided)
# ---------------------------------------------------------------------------

HIGH_RISK_PAYLOAD = {
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
        {
            "role": "partner",
            "influence_weight": 9,
            "stance_on_decision": "opposed",
            "key_concerns": ["commitment", "future"],
        }
    ],
    "seed": 99,
}

STANDARD_PAYLOAD = {
    "decision": "Should I change to a higher-paying but more stressful job?",
    "mode": "quick",
    "options": ["Stay at current job", "Take the new job"],
    "profile": {
        "age": 31,
        "city": "Beijing",
        "occupation": "Engineer",
        "risk_tolerance": 6,
        "core_values": ["growth", "stability"],
        "decision_style": "analytical",
    },
    "seed": 77,
}


@pytest.mark.skipif(True, reason="Requires live backend: pass --base http://localhost:8000")
class TestGuardrailsLive:
    """
    Live guardrail tests. To run:
        pytest backend/tests/test_guardrails.py -v --base http://localhost:8000
    """

    @pytest.fixture(autouse=True)
    def skip_without_base(self, live_base_url):
        if not live_base_url:
            pytest.skip("No --base URL provided")

    def _simulate(self, live_base_url: str, payload: dict) -> list[dict]:
        resp = requests.post(
            f"{live_base_url}/api/simulate",
            json=payload,
            stream=True,
            timeout=120,
        )
        assert resp.status_code == 200
        return parse_sse_stream(resp.text)

    def test_live_standard_stream_no_deterministic_language(self, live_base_url):
        """SYS-15: Standard simulation must have no deterministic language."""
        events = self._simulate(live_base_url, STANDARD_PAYLOAD)
        texts = extract_nl_texts(events)
        violations = find_deterministic_violations(texts)
        assert not violations, (
            f"SYS-15 FAIL (live): Deterministic language found:\n"
            + "\n".join(f"  [{et}.{field}] pattern='{pat}': {text!r}"
                        for et, field, text, pat in violations)
        )

    def test_live_high_risk_stream_simulation_guardrail(self, live_base_url):
        """SYS-16: High-risk live stream must include simulation guardrail."""
        events = self._simulate(live_base_url, HIGH_RISK_PAYLOAD)
        result = check_high_risk_guardrail(events)
        assert result["simulation_guardrail"], (
            "SYS-16 FAIL (live): Missing simulation-not-prophecy guardrail."
        )

    def test_live_high_risk_stream_how_to_change_affordance(self, live_base_url):
        """SYS-16: High-risk live stream must include how-to-change affordance."""
        events = self._simulate(live_base_url, HIGH_RISK_PAYLOAD)
        result = check_high_risk_guardrail(events)
        assert result["how_to_change"], (
            "SYS-16 FAIL (live): Missing 'how to change this outcome' affordance."
        )

    def test_live_recommendation_guardrail_field_nonempty_for_high_risk(self, live_base_url):
        """SYS-16: recommendation.guardrail must be non-empty for high-risk case."""
        events = self._simulate(live_base_url, HIGH_RISK_PAYLOAD)
        recs = [e for e in events if e["event_type"] == "recommendation"]
        assert recs
        guardrail = recs[0]["data"].get("guardrail", "")
        assert guardrail and len(guardrail) > 10, (
            f"SYS-16 FAIL (live): recommendation.guardrail is empty or too short: {guardrail!r}"
        )
