# Lynsea — Two 30-Second Demo Scripts

Two self-playing, screen-recordable pages on branch `feat/claude-code-implement`, each
completing one loop in **~30 s (±2 s)**:

| Page | Arc | What it proves |
|------|-----|----------------|
| **`pitch.html`** | 痛点 → 目标 → 技术 (Pain → Goal → Tech) | The *why* and the *how* in three 10-second beats |
| **`workflow.html`** | Console → clarify → parallel-futures dashboard | The full product, streamed in SSE order |

Both lift the `design/stitch/` tokens directly: **Branch A = cyan `#22D3EE`, always LEFT;
Branch B = amber `#FBBF24`, always RIGHT** (never swapped); fork = magenta `#F472B6`;
shared events = dashed slate `#94A3B8`; canvas `#0B0F1A`; brand indigo `#8B7CF6`;
fonts Space Grotesk / Inter. **All copy is probabilistic** ("likely", "~60% chance") — never
"will/definitely" (SYS-15).

Recording: open the page in Chrome at **1920×1080**, Do-Not-Disturb on, hard-refresh so it
starts at `t=0`, capture one clean ~30 s loop. Lay the VO on top. No build step, no backend —
fully self-contained, auto-runs on load and loops.

---

## Script A — `pitch.html` (痛点 / 目标 / 技术)

**Arc:** state the pain, show the goal, then prove the technique.
**Wow moment:** ~0:11 — the two parallel futures snap up side-by-side (well before the 60 % mark).

```yaml
wow_moment_timestamp: 11

script:
  - timestamp_start: 0
    timestamp_end: 5
    narration: "A high-stakes life decision is one-shot. And irreversible."
  - timestamp_start: 5
    timestamp_end: 10
    narration: "You only live one branch. The road not taken stays invisible."
  - timestamp_start: 10
    timestamp_end: 15
    narration: "Lynsea shows both futures side-by-side — before you choose."
  - timestamp_start: 15
    timestamp_end: 20
    narration: "Probabilistic. Value-weighted to you. And fully reproducible."
  - timestamp_start: 20
    timestamp_end: 27
    narration: "How? A fixed-seed paired counterfactual over digital-twin personas."
  - timestamp_start: 27
    timestamp_end: 30
    narration: "FastAPI, Claude, and SSE — built by nine agents on Multica."

shot_list:
  - timestamp_start: 0
    timestamp_end: 5
    screen_content: "Beat 01 · 痛点. Decision node draws a single solid 'life you live' road."
    action: "Headline: 'A high-stakes life decision is one-shot — and irreversible.'"
    callouts: ["痛点 · The Pain"]
  - timestamp_start: 5
    timestamp_end: 10
    screen_content: "A dashed, greyed 'road not taken — you never see it' branches below; gut-feel 🎲 and spreadsheet 📊 cards get struck through."
    action: "Ghost path fades in; two 'how people decide today' cards cross out."
    callouts: ["The road not taken", "Gut feel", "A spreadsheet"]
  - timestamp_start: 10
    timestamp_end: 15
    screen_content: "Beat 02 · 目标. A/B parallel-futures board: A=cyan Stay (left) vs B=amber Join (right), divergent month cards."
    action: "Column headers + M1 cards snap in; dashed shared event between them."
    callouts: ["Branch A · Stay (cyan, left)", "Branch B · Join (amber, right)", "Shared event · same seed in both"]
  - timestamp_start: 15
    timestamp_end: 20
    screen_content: "Magenta fork-point spine draws; composite scores count up (A 61 / B 67); chips: Probabilistic · Value-weighted · Reproducible; recommendation + guardrail."
    action: "Fork line scales in; score cards tick up; guardrail line appears."
    callouts: ["Paths diverge most here · month 3", "Leans B — ~60% chance higher for you", "⚠ Guardrail: keep ~6 months runway"]
  - timestamp_start: 20
    timestamp_end: 27
    screen_content: "Beat 03 · 技术. Four technique cards build in."
    action: "Cards reveal in sequence, each tagged with its acceptance unit."
    callouts:
      - "Fixed-seed paired counterfactual (M-b) — branches differ only by the decision; shared events byte-identical; reproducible seed hash (NFR-01)"
      - "Digital-twin personas (M-c) — UserHarness, arXiv:2605.27721; state-forking keeps personas consistent across branches"
      - "5-dim value-weighted scoring (M-d) — economic · career · relationships · mental · autonomy"
      - "Credibility card — data · causal · plausibility; directional, never prophecy"
  - timestamp_start: 27
    timestamp_end: 30
    screen_content: "Stack badges + build badge + seed-lock flash."
    action: "Seed badge flashes 'reproducible #7f3ac1'; closing tagline."
    callouts: ["FastAPI · Claude API · SSE streaming", "Next.js · Recharts", "9-agent parallel build on Multica", "See your futures before you choose."]
```

---

## Script B — `workflow.html` (full product workflow)

**Arc:** drive the real product end-to-end — ask, clarify, then watch the two futures stream in.
**Wow moment:** ~0:14 — the magenta **fork point** lands and the branches visibly split (before the 60 % mark).

The dashboard fills in **SSE order** mirroring the live contract on this branch:
`status` (run_started) → `persona` → `timeline_event` (skeleton, then shared perturbation) →
`metric` → `branch_point` (fork) → `branch_score` → `credibility` → `recommendation` → `done`.

```yaml
wow_moment_timestamp: 14

script:
  - timestamp_start: 0
    timestamp_end: 5
    narration: "Describe one hard decision. Here: quit a stable job for a startup."
  - timestamp_start: 5
    timestamp_end: 8
    narration: "Lynsea clarifies first — runway, and your partner's stability weight."
  - timestamp_start: 8
    timestamp_end: 12
    narration: "It builds your world: you, plus five digital-twin personas."
  - timestamp_start: 12
    timestamp_end: 17
    narration: "Two futures stream in — sharing the exact same seeded events."
  - timestamp_start: 17
    timestamp_end: 22
    narration: "The magenta fork point shows where the paths diverge most."
  - timestamp_start: 22
    timestamp_end: 27
    narration: "Value-weighted scores, five curves, and a credibility card resolve."
  - timestamp_start: 27
    timestamp_end: 30
    narration: "It even asks a follow-up — forking a third what-if future."

shot_list:
  - timestamp_start: 0
    timestamp_end: 4
    screen_content: "Decision Console. Decision auto-types into the input; Quick mode selected; Run pressed."
    action: "Caret types the decision; 'Run simulation' ripples."
    callouts: ["Quick · 4 mo", "FastAPI + Claude API + SSE streaming"]
  - timestamp_start: 4
    timestamp_end: 8
    screen_content: "clarify card (SSE status: clarify): Q1 runway answer types in; Q2 partner-weight chip selected; 'Refine & run' pressed."
    action: "Answers fill; refine button ripples; transition to dashboard."
    callouts: ["clarify — dynamic per-decision questions", "~8 months runway", "Stability-leaning · 7/10"]
  - timestamp_start: 8
    timestamp_end: 12
    screen_content: "Dashboard run_started: title, Streaming badge, seed-locked badge, A/B legend; five persona chips stream into the World bar."
    action: "Header + legend reveal; persona chips pop in one by one."
    callouts: ["seed-locked · reproducible", "You · digital twin (UserHarness, arXiv:2605.27721)", "Partner/Mother opposed · Mentor neutral · Best friend supportive"]
  - timestamp_start: 12
    timestamp_end: 17
    screen_content: "timeline_event skeletons: M1 A/B cards; dashed 'Shared event · same seed in both' at M2; metric curves draw. Magenta fork-point at M3."
    action: "M1 cards + shared event in; 5 dimension curves draw; fork line scales in (WOW)."
    callouts: ["Shared event · same seed in both (M-b)", "Paths diverge most here — fork point / branch_point", "MiroFish world-sim base · EverOS memory"]
  - timestamp_start: 17
    timestamp_end: 22
    screen_content: "M3/M4 divergent A/B cards; composite scores count up A 61 / B 67; value-weighted note."
    action: "Remaining month cards reveal; score numbers tick up."
    callouts: ["branch_score — value-weighted (M-d)", "Economic · career · relationships · mental · autonomy", "Recharts curves"]
  - timestamp_start: 22
    timestamp_end: 27
    screen_content: "Credibility gauge fills to 62 (data/causal/plausibility sub-bars); recommendation strip slides up with guardrail; 'Done · 41 events'; seed flashes '#7f3ac1'."
    action: "Gauge + sub-bars fill; recstrip rises; seed badge flashes."
    callouts: ["credibility card", "Leans B — ~60% chance higher for you", "⚠ Guardrail: keep ~6 months runway", "A simulation, not a prediction"]
  - timestamp_start: 27
    timestamp_end: 30
    screen_content: "Closing follow-up question types into the violet box; Branch C = what-if legend appears."
    action: "Follow-up types in; C legend chip fades in; loop replays from t=0."
    callouts: ["Lynsea asks — pressure-test it", "Branch C forks a third future from M3 (M-c state forking)"]
```

---

## Recording checklist (both pages)

```yaml
recording_checklist:
  - "OS + browser notifications disabled (Do Not Disturb)"
  - "No test data / backend needed — pages are fully self-contained (no network, fonts fall back offline)"
  - "Screen resolution 1920×1080; the 1280×720 stage auto-fits and letterboxes"
  - "Hard-refresh the page so the loop starts exactly at t=0 before recording"
  - "Confirm A=cyan/left and B=amber/right render correctly (never swapped)"
  - "Run `node demo/record.mjs` once as a smoke test — must report no page/console errors and ~30s per page"
```

## Fallback plan (both pages)

```yaml
fallback_plan:
  trigger: "Live screen-capture stutters, fonts fail to load, or a loop boundary is caught mid-frame"
  action: "Use the deterministic Playwright capture (`node demo/record.mjs --frames pitch` / `--frames workflow`) and stitch the PNG frames to MP4 with ffmpeg — a clean, repeatable render that never depends on a live demo."
```
