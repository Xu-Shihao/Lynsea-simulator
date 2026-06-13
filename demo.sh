#!/usr/bin/env bash
#
# Lynsea P0 end-to-end demo.
#
# Boots the backend (FastAPI, :8000) and, by default, the frontend (Next.js,
# :3000), waits for both to be ready, then drives the API through the four P0
# end-to-end scenarios from plans/Lynsea-验收标准.md section 8:
#
#   E2E-1  Job decision, Quick mode      -> 2 timelines + 5 metrics + branch pts + credibility
#   E2E-2  End a relationship (high-risk) -> probabilistic phrasing + "simulation, not a prophecy"
#   E2E-5  Same decision + same seed x2   -> shared exogenous events hash-equal (reproducible)
#   E2E-6  Cold start, minimal input      -> default personas flagged "information limited"
#
# It also records the BE-04 timing target (first skeleton event <= 20s, Quick),
# prints a human-readable pass/fail report, and tears down the servers.
#
# Usage:
#   ./demo.sh                 backend + frontend, all P0 scenarios
#   ./demo.sh --no-frontend   backend + scenarios only (skip npm/Next.js)
#   ./demo.sh --keep          leave servers running after the report
#
# Exit code: 0 if all P0 scenarios pass, 1 otherwise.

set -u

# ---------------------------------------------------------------------------
# Config / paths (absolute, resolved from this script's location).
# ---------------------------------------------------------------------------
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend"

API_BASE="${API_BASE:-http://localhost:8000}"
FRONTEND_BASE="${FRONTEND_BASE:-http://localhost:3000}"

RUN_FRONTEND=1
KEEP=0
for arg in "$@"; do
  case "$arg" in
    --no-frontend) RUN_FRONTEND=0 ;;
    --keep) KEEP=1 ;;
    -h|--help) grep '^#' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $arg (try --help)"; exit 2 ;;
  esac
done

# Pick the backend's venv python if present, else system python3.
if [ -x "$BACKEND_DIR/.venv/bin/python" ]; then
  PY="$BACKEND_DIR/.venv/bin/python"
  UVICORN="$BACKEND_DIR/.venv/bin/uvicorn"
else
  PY="$(command -v python3 || command -v python)"
  UVICORN=""
fi
if [ -z "${PY:-}" ]; then
  echo "FATAL: no python interpreter found." >&2
  exit 2
fi

LOG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/lynsea-demo.XXXXXX")"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
BACKEND_PID=""
FRONTEND_PID=""

c_green=$'\033[32m'; c_red=$'\033[31m'; c_yellow=$'\033[33m'; c_bold=$'\033[1m'; c_off=$'\033[0m'

say()  { printf '%s\n' "$*"; }
hr()   { printf '%s\n' "------------------------------------------------------------"; }

# ---------------------------------------------------------------------------
# Teardown.
# ---------------------------------------------------------------------------
cleanup() {
  if [ "$KEEP" -eq 1 ]; then
    say ""
    say "${c_yellow}--keep set: leaving servers running.${c_off}"
    [ -n "$BACKEND_PID" ]  && say "  backend  pid=$BACKEND_PID  log=$BACKEND_LOG"
    [ -n "$FRONTEND_PID" ] && say "  frontend pid=$FRONTEND_PID log=$FRONTEND_LOG"
    return
  fi
  say ""
  say "Tearing down servers..."
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
  [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null
  # Give them a moment, then hard-kill any stragglers in our process group.
  sleep 1
  [ -n "$FRONTEND_PID" ] && kill -9 "$FRONTEND_PID" 2>/dev/null
  [ -n "$BACKEND_PID" ]  && kill -9 "$BACKEND_PID"  2>/dev/null
  say "Logs kept at: $LOG_DIR"
}
trap cleanup EXIT INT TERM

# ---------------------------------------------------------------------------
# Wait for an HTTP endpoint to come up (returns 0 when ready).
# ---------------------------------------------------------------------------
wait_for_http() {
  local url="$1" name="$2" tries="${3:-60}" i=0
  while [ "$i" -lt "$tries" ]; do
    if curl -fsS -o /dev/null --max-time 3 "$url" 2>/dev/null; then
      say "  ${c_green}ready${c_off}: $name ($url)"
      return 0
    fi
    i=$((i + 1))
    sleep 1
  done
  say "  ${c_red}TIMEOUT${c_off}: $name did not become ready at $url"
  return 1
}

# ---------------------------------------------------------------------------
# Start servers.
# ---------------------------------------------------------------------------
say "${c_bold}Lynsea P0 demo${c_off}"
say "root:        $ROOT"
say "python:      $PY"
say "api base:    $API_BASE"
say "logs:        $LOG_DIR"
hr

# Pre-flight: refuse to run if something already owns port 8000, otherwise the
# readiness probe would silently pass against a foreign (possibly live-key)
# server and the scenarios would not exercise this checkout.
if command -v lsof >/dev/null 2>&1; then
  if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
    say "${c_red}FATAL${c_off}: port 8000 is already in use. Stop the other server first:"
    say "  lsof -nP -iTCP:8000 -sTCP:LISTEN"
    exit 2
  fi
fi

say "Starting backend (uvicorn app.main:app --port 8000)..."
if [ -n "$UVICORN" ] && [ -x "$UVICORN" ]; then
  ( cd "$BACKEND_DIR" && exec "$UVICORN" app.main:app --port 8000 ) >"$BACKEND_LOG" 2>&1 &
else
  ( cd "$BACKEND_DIR" && exec "$PY" -m uvicorn app.main:app --port 8000 ) >"$BACKEND_LOG" 2>&1 &
fi
BACKEND_PID=$!
say "  backend pid=$BACKEND_PID"

if ! wait_for_http "$API_BASE/health" "backend" 60; then
  say "${c_red}Backend failed to start. Tail of log:${c_off}"
  tail -n 30 "$BACKEND_LOG" 2>/dev/null
  exit 1
fi

if [ "$RUN_FRONTEND" -eq 1 ]; then
  if [ -d "$FRONTEND_DIR/node_modules" ]; then
    say "Starting frontend (npm run dev on :3000)..."
    if [ ! -f "$FRONTEND_DIR/.env.local" ]; then
      printf 'NEXT_PUBLIC_API_BASE=%s\n' "$API_BASE" > "$FRONTEND_DIR/.env.local"
    fi
    ( cd "$FRONTEND_DIR" && exec npm run dev ) >"$FRONTEND_LOG" 2>&1 &
    FRONTEND_PID=$!
    say "  frontend pid=$FRONTEND_PID"
    # Frontend readiness is non-fatal: the P0 scenarios are API-driven.
    if ! wait_for_http "$FRONTEND_BASE" "frontend" 90; then
      say "  ${c_yellow}WARN${c_off}: frontend not ready; continuing with API scenarios."
      tail -n 15 "$FRONTEND_LOG" 2>/dev/null
    fi
  else
    say "${c_yellow}Skipping frontend: $FRONTEND_DIR/node_modules missing (run 'npm install').${c_off}"
  fi
else
  say "Skipping frontend (--no-frontend)."
fi

hr
say "Running P0 end-to-end scenarios against $API_BASE ..."
hr

# ---------------------------------------------------------------------------
# The scenario driver (stdlib-only Python: urllib for HTTP + SSE).
# Prints one PASS/FAIL line per check and a final REPORT line; exits non-zero
# on any P0 failure.
# ---------------------------------------------------------------------------
API_BASE="$API_BASE" LYNSEA_ROOT="$ROOT" "$PY" - <<'PYEOF'
import json
import os
import sys
import time
import urllib.request
import urllib.error

API = os.environ["API_BASE"].rstrip("/")

GREEN = "\033[32m"; RED = "\033[31m"; YELLOW = "\033[33m"; BOLD = "\033[1m"; OFF = "\033[0m"

# BE-04: Quick-mode first skeleton event acceptance line.
BE04_FIRST_EVENT_S = 20.0

results = []  # (scenario_id, passed: bool, lines: [str])


def post_simulate(body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        API + "/api/simulate", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())["sim_id"]


def consume_stream(sim_id, overall_timeout=240.0):
    """Read the SSE stream to completion. Returns (events, first_timeline_dt).

    events: list of (event_type, payload_dict)
    first_timeline_dt: seconds from stream-open to first `timeline_event`, or None.
    """
    url = "%s/api/simulate/%s/stream" % (API, sim_id)
    events = []
    first_timeline_dt = None
    start = time.time()
    req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
    resp = urllib.request.urlopen(req, timeout=overall_timeout)
    cur_event = None
    try:
        for raw in resp:
            line = raw.decode("utf-8", "replace").rstrip("\n")
            if line.startswith("event:"):
                cur_event = line[len("event:"):].strip()
            elif line.startswith("data:"):
                payload_raw = line[len("data:"):].strip()
                try:
                    payload = json.loads(payload_raw) if payload_raw else {}
                except json.JSONDecodeError:
                    payload = {"_raw": payload_raw}
                etype = cur_event or "message"
                events.append((etype, payload))
                if etype == "timeline_event" and first_timeline_dt is None:
                    first_timeline_dt = time.time() - start
                if etype in ("done", "error"):
                    break
            if time.time() - start > overall_timeout:
                break
    finally:
        resp.close()
    return events, first_timeline_dt


def get_result(sim_id):
    url = "%s/api/simulate/%s" % (API, sim_id)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())


def shared_signature(events_list):
    """Hashable, order-independent signature of shared exogenous events."""
    sig = sorted(
        (e.get("shared_event_id"), e.get("month"), e.get("title"), e.get("description"))
        for e in events_list
        if e.get("is_shared_exogenous")
    )
    return sig


def run_scenario(sid):
    """Drives one scenario; returns dict with timing + assembled result data."""
    events, first_dt = consume_stream(sid)
    by_type = {}
    for etype, payload in events:
        by_type.setdefault(etype, []).append(payload)
    # Prefer the assembled SimResult (GET) for final-object assertions.
    full = None
    if "error" not in by_type:
        for _ in range(10):
            try:
                full = get_result(sid)
                break
            except urllib.error.HTTPError as he:
                if he.code == 425:   # not ready yet
                    time.sleep(0.5)
                    continue
                raise
    return {"events": events, "by_type": by_type, "first_dt": first_dt, "full": full}


def record(scenario_id, checks):
    """checks: list of (label, ok_bool). Prints and stores."""
    passed = all(ok for _, ok in checks)
    lines = []
    for label, ok in checks:
        mark = (GREEN + "PASS" + OFF) if ok else (RED + "FAIL" + OFF)
        lines.append("    [%s] %s" % (mark, label))
    results.append((scenario_id, passed, lines))
    head = (GREEN + "PASS" + OFF) if passed else (RED + "FAIL" + OFF)
    print("  %s%s%s  [%s]" % (BOLD, scenario_id, OFF, head))
    for ln in lines:
        print(ln)
    print()


# ---------------------------------------------------------------------------
# E2E-1 — Job decision, Quick mode.
#   2 timelines (A & B) + 5 metric dims + >=1 branch point + credibility card.
# ---------------------------------------------------------------------------
def e2e_1():
    body = {
        "decision": "Should I take the higher-paying but high-stress job?",
        "options": ["Take the new job", "Stay at my current job"],
        "affected_people": ["my partner", "my mother"],
        "mode": "quick",
        "seed": 12345,
    }
    sid = post_simulate(body)
    r = run_scenario(sid)
    by, full = r["by_type"], r["full"]
    checks = []

    branches = {e.get("branch") for e in by.get("timeline_event", [])}
    checks.append(("two parallel timelines (branch A and B present)",
                   {"A", "B"}.issubset(branches)))

    metric_pts = (full or {}).get("metrics", []) or by.get("metric", [])
    dims = ["economic", "career", "relationship", "mental", "autonomy"]
    has_5 = bool(metric_pts) and all(d in metric_pts[0] for d in dims)
    checks.append(("five metric dimensions present (%s)" % ", ".join(dims), has_5))

    every_linked = bool(metric_pts) and all(
        len(m.get("supporting_event_ids", [])) >= 1 for m in metric_pts
    )
    checks.append(("ALG-40: every metric point links >=1 supporting event", every_linked))

    bps = (full or {}).get("branch_points", []) or by.get("branch_point", [])
    checks.append(("at least one branch point with a cause chain",
                   len(bps) >= 1 and bool(bps and bps[0].get("cause_chain"))))

    cred = (full or {}).get("credibility") or (by.get("credibility", [None])[0])
    checks.append(("credibility card present (overall + sub-scores)",
                   bool(cred) and "overall" in cred and "data_sufficiency" in cred))

    # BE-04 timing (Quick first skeleton event <= 20s). Reported either way.
    dt = r["first_dt"]
    if dt is None:
        checks.append(("BE-04: first timeline event received", False))
    else:
        ok = dt <= BE04_FIRST_EVENT_S
        label = "BE-04: first skeleton event in %.1fs (<= %.0fs target)" % (dt, BE04_FIRST_EVENT_S)
        if not ok:
            label += "  " + YELLOW + "[over target]" + OFF
        checks.append((label, ok))

    record("E2E-1 (job decision, Quick)", checks)


# ---------------------------------------------------------------------------
# E2E-2 — End a 3-year relationship (high-risk), Quick mode.
#   Probabilistic phrasing, NO deterministic "will/definitely", and the
#   "simulation, not a prophecy" guardrail (rec text + frontend SafetyBanner).
# ---------------------------------------------------------------------------
def e2e_2():
    body = {
        "decision": "Should I end my 3-year relationship?",
        "options": ["End the relationship", "Stay together"],
        "affected_people": ["my partner"],
        "mode": "quick",
        "seed": 777,
    }
    sid = post_simulate(body)
    r = run_scenario(sid)
    by, full = r["by_type"], r["full"]
    checks = []

    rec = (full or {}).get("recommendation") or (by.get("recommendation", [None])[0])
    rec_text = (rec or {}).get("text", "") if rec else ""
    cred = (full or {}).get("credibility") or (by.get("credibility", [None])[0])
    cred_text = " ".join((cred or {}).get("notes", [])) if cred else ""
    corpus = (rec_text + " " + cred_text).lower()

    checks.append(("recommendation produced", bool(rec_text)))

    # SYS-15: probabilistic phrasing present.
    prob_markers = ["probab", "likely", "~", "%", "not a guarantee", "coin toss", "lean"]
    checks.append(("SYS-15: probabilistic phrasing present",
                   any(m in corpus for m in prob_markers)))

    # SYS-15: NO deterministic / fortune-telling phrasing.
    forbidden = ["will happen", "you will ", "definitely", "certainly", "guaranteed", "is destined"]
    found_forbidden = [w for w in forbidden if w in corpus]
    checks.append(("SYS-15: no deterministic 'will/definitely/guaranteed' phrasing"
                   + ("" if not found_forbidden else "  -> found: %s" % found_forbidden),
                   not found_forbidden))

    # SYS-16: high-risk guardrail wording. Backend adds the "simulation, not a
    # prophecy" caveat when a high-risk dim drops on the favored path; the
    # frontend always renders the SafetyBanner for high-risk results. We accept
    # the caveat in the rec text OR the presence of the frontend banner copy.
    banner_in_rec = "not a prophecy" in corpus or "simulation, not" in corpus
    frontend_banner = _frontend_has_banner()
    checks.append(("SYS-16/FE-24: 'simulation, not a prophecy' guardrail available"
                   + (" (in recommendation)" if banner_in_rec else
                      " (frontend SafetyBanner)" if frontend_banner else ""),
                   banner_in_rec or frontend_banner))

    record("E2E-2 (high-risk relationship, Quick)", checks)


def _frontend_has_banner():
    """Best-effort check that the frontend ships the high-risk banner copy.

    `__file__` is undefined under `python - <<EOF`, so resolve from LYNSEA_ROOT
    (exported by demo.sh) and fall back to cwd.
    """
    root = os.environ.get("LYNSEA_ROOT") or os.getcwd()
    candidate = os.path.join(root, "frontend", "components", "SafetyBanner.tsx")
    try:
        with open(candidate, "r", encoding="utf-8") as fh:
            return "not a prophecy" in fh.read().lower()
    except OSError:
        return False


# ---------------------------------------------------------------------------
# E2E-5 — Reproducibility: same decision + same seed run twice.
#   Shared exogenous event stream must be hash-equal across the two runs.
# ---------------------------------------------------------------------------
def e2e_5():
    body = {
        "decision": "Should I take the higher-paying but high-stress job?",
        "options": ["Take the new job", "Stay at my current job"],
        "affected_people": ["my partner"],
        "mode": "quick",
        "seed": 424242,
    }
    sid1 = post_simulate(body)
    r1 = run_scenario(sid1)
    sid2 = post_simulate(dict(body))
    r2 = run_scenario(sid2)

    ev1 = (r1["full"] or {}).get("events", []) or [p for p in r1["by_type"].get("timeline_event", [])]
    ev2 = (r2["full"] or {}).get("events", []) or [p for p in r2["by_type"].get("timeline_event", [])]

    sig1 = shared_signature(ev1)
    sig2 = shared_signature(ev2)

    checks = []
    checks.append(("both runs produced shared exogenous events", len(sig1) > 0 and len(sig2) > 0))
    checks.append(("ALG-20/NFR-01: shared exogenous events hash-equal across runs"
                   + (" (%d events)" % len(sig1) if sig1 == sig2 else " (%d vs %d)" % (len(sig1), len(sig2))),
                   sig1 == sig2 and len(sig1) > 0))

    # Also: seeds recorded identically on both full results.
    s1 = (r1["full"] or {}).get("seed")
    s2 = (r2["full"] or {}).get("seed")
    checks.append(("identical seed recorded on both runs (%s)" % s1, s1 is not None and s1 == s2))

    record("E2E-5 (same-seed reproducibility)", checks)


# ---------------------------------------------------------------------------
# E2E-6 — Cold start with minimal input.
#   Default-value personas flagged is_default_inferred, surfaced as low-confidence
#   in the credibility card, with a "cold start / information limited" note.
# ---------------------------------------------------------------------------
def e2e_6():
    body = {
        "decision": "Should I move?",
        "options": ["Move", "Stay"],
        "mode": "quick",
        "seed": 999,
    }
    sid = post_simulate(body)
    r = run_scenario(sid)
    by, full = r["by_type"], r["full"]
    checks = []

    personas = (full or {}).get("personas", []) or by.get("persona", [])
    checks.append(("personas built from minimal input", len(personas) >= 1))

    default_flagged = [p for p in personas if p.get("is_default_inferred")]
    checks.append(("ALG-04: at least one persona flagged is_default_inferred (cold start)",
                   len(default_flagged) >= 1))

    cred = (full or {}).get("credibility") or (by.get("credibility", [None])[0])
    low_conf = (cred or {}).get("low_confidence_personas", []) if cred else []
    checks.append(("FE-23: cold-start personas surfaced as low_confidence_personas",
                   len(low_conf) >= 1))

    notes = " ".join((cred or {}).get("notes", [])).lower() if cred else ""
    note_markers = ["cold start", "default", "information limited", "low-confidence", "low confidence"]
    checks.append(("credibility note marks defaults as 'information limited'",
                   any(m in notes for m in note_markers)))

    record("E2E-6 (cold-start minimal input)", checks)


def main():
    for fn in (e2e_1, e2e_2, e2e_5, e2e_6):
        try:
            fn()
        except urllib.error.HTTPError as he:
            results.append((fn.__name__, False, ["    [%sFAIL%s] HTTP %s: %s" % (RED, OFF, he.code, he.reason)]))
            print("  %s%s%s  [%sFAIL%s] HTTP %s\n" % (BOLD, fn.__name__, OFF, RED, OFF, he.code))
        except Exception as exc:  # keep going; report at the end
            results.append((fn.__name__, False, ["    [%sFAIL%s] %s: %s" % (RED, OFF, type(exc).__name__, exc)]))
            print("  %s%s%s  [%sFAIL%s] %s: %s\n" % (BOLD, fn.__name__, OFF, RED, OFF, type(exc).__name__, exc))

    print("------------------------------------------------------------")
    print("%sP0 E2E REPORT%s" % (BOLD, OFF))
    n_pass = sum(1 for _, ok, _ in results if ok)
    for sid, ok, _ in results:
        mark = (GREEN + "PASS" + OFF) if ok else (RED + "FAIL" + OFF)
        print("  [%s] %s" % (mark, sid))
    print("  ----")
    print("  %d/%d scenarios passed" % (n_pass, len(results)))
    print("------------------------------------------------------------")
    sys.exit(0 if n_pass == len(results) else 1)


main()
PYEOF

scenario_rc=$?

hr
if [ "$scenario_rc" -eq 0 ]; then
  say "${c_green}${c_bold}All P0 E2E scenarios passed.${c_off}"
else
  say "${c_red}${c_bold}One or more P0 E2E scenarios FAILED (rc=$scenario_rc).${c_off}"
  say "Backend log tail:"
  tail -n 20 "$BACKEND_LOG" 2>/dev/null
fi

exit "$scenario_rc"
