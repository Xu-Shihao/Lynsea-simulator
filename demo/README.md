# Lynsea — Demo Video Kit

The hackathon submission video for **Lynsea — Decision Outcome Simulator**.

> *Submit a short demo video highlighting the specific features, code, and functionality the team built.*

This folder is everything needed to produce that video:

| File | What it is |
|------|-----------|
| **`walkthrough.html`** | A self-contained, **~88-second self-playing** animated walkthrough built from the `docs/design/` Stitch design. **This is the main recording surface** — open it and screen-record one loop. |
| **`teaser.html`** | A self-contained, **15-second single-screen teaser** — the whole system on one frame (parallel-futures board + scores + credibility + recommendation + a 4-feature ticker) that builds in fast. Use it as a sizzle/intro clip or social cut. No scrolling, no scene changes — one screen. |
| **`pitch.html`** | A self-contained, **~30-second self-playing** pitch in three beats — **痛点 → 目标 → 技术** (Pain → Goal → Tech). The *why* and the *how* on one stage. See the **30s demos** section below. |
| **`workflow.html`** | A self-contained, **~30-second self-playing** condensed end-to-end workflow — Decision Console → clarify → parallel-futures dashboard streaming in SSE order. The full product, compressed. See the **30s demos** section below. |
| **`demo-script.md`** | The 1-min/15s video script: time-coded shot list (0:00–1:28), voice-over narration, and on-screen callouts naming the specific features, code, and functionality built. Includes a 60-second trim path and the 15-second teaser beat block. |
| **`demo-script-30s.md`** | The two **0:00–0:30** scripts (one per 30s page): shot list + VO + on-screen callouts naming the specific features/code (M-b/M-c/M-d, UserHarness, MiroFish, EverOS, FastAPI+Claude+SSE, Next.js+Recharts, the 9-agent Multica build). |
| **`record.mjs`** | Playwright driver + **smoke test**: by default loads every page, runs one full loop, and fails loudly on any page/console error or missing final beat. Also captures PNG frames / beat stills for any page (and, via ffmpeg, an MP4). |

---

## Quickest path to the MP4 (recommended): screen-record the page

1. Open **`walkthrough.html`** in Chrome (double-click it, or `open demo/walkthrough.html`).
   It is fully self-contained — **no build step, no backend, no network** (fonts fall back gracefully offline).
   The animation auto-runs once on load and then loops.
2. Set the OS to Do Not Disturb; record at **1920×1080** (the stage auto-fits and letterboxes to any window).
3. Start your screen recorder (macOS: <kbd>⌘⇧5</kbd> → record the browser window), hard-refresh the page so it starts at `t=0`, and capture one clean ~88-second loop.
4. Lay the voice-over from `demo-script.md` on top. If your platform caps at 60 seconds, use the trim path at the bottom of `demo-script.md` (drop the closing Branch C beat).

The animation tracks the script beats: console hook → **clarify Q&A ~0:06–0:14** → dashboard streams in → **fork point lands ~0:26** → 6-month trajectory + scores + credibility + recommendation by ~0:48 → seed-lock "reproducible" flash ~0:52 → **closing Branch C what-if ~0:57–1:07** → hold.

### Timecode map (script ↔ animation)

| Script window | What the animation does |
|---------------|--------------------------|
| 0:00–0:06 | Decision Console: decision types in, Quick mode, Run pressed |
| 0:06–0:13 | `clarify` — 3 follow-up questions; answers type in (runway, partner's stability weight, regret) |
| 0:13–0:16 | "Refine & run" pressed; transition to dashboard, A/B legend, seed-locked badge |
| 0:16–0:22 | `world_ready` — 6 persona chips stream in; M1 skeletons; curves start drawing |
| 0:22–0:26 | `timeline_event` perturbation — dashed shared event at M2 |
| 0:26–0:30 | `fork_point` — magenta marker + explanation at M3 (**wow moment**); camera pans |
| 0:30–0:40 | 2nd shared event at M4; M4–M6 cards fill in; camera pans the 6-month timeline |
| 0:40–0:50 | `branch_score` (A 61 / B 67), 5 curves, `credibility` gauge → 62, `recommendation` + guardrail |
| 0:50–0:56 | seed-locked "reproducible #7f3ac1" flash; `done · 63 events` |
| 0:56–1:07 | closing follow-up types in; violet **Branch C** what-if forks from M3 |
| 1:07–1:28 | Camera settles on the full parallel-futures frame; hold (loop replays from t=0) |

---

## The 15-second teaser (`teaser.html`) — one screen, whole system

A separate, **single-screen** clip that introduces the system's characteristics all at once — no scene changes, no scrolling. Record it the same way: open `teaser.html` in Chrome, hard-refresh to start at `t=0`, and capture one 15-second loop. Everything is laid out on one 1280×720 frame and builds in fast.

| Window | What the animation does |
|--------|--------------------------|
| 0:00–0:02 | Brand + decision query + seed-locked badge; A=cyan(left)/B=amber(right) legend; 6 personas |
| 0:02–0:04 | Parallel-futures board: divergent cards, dashed "shared event", magenta **fork point** spine draws |
| 0:04–0:07 | Value-weighted scores count up (A 61 / B 67) + 5 dimension sparklines draw |
| 0:07–0:10 | Credibility gauge fills to 62; probabilistic **recommendation + guardrail** appear |
| 0:10–0:12 | seed-locked badge flashes "reproducible #7f3ac1" |
| 0:12–0:15 | Hold; closing tagline overlay: *See your futures before you choose.* |

A persistent **feature ticker** along the bottom highlights the four differentiators in turn: **seeded paired counterfactual → belief-driven personas → value-weighted scoring → streamed & credibility-scored**. It loops identically from `t=0`, and like the walkthrough it is fully self-contained (no build, no backend).

---

## The 30s demos (`pitch.html` + `workflow.html`)

Two **~30-second** self-playing pages (each completes one loop in **~30 s ±2 s**), built for
`feat/claude-code-implement`. Record them exactly like the others: open in Chrome at 1920×1080,
Do-Not-Disturb on, hard-refresh to start at `t=0`, capture one loop. Both are fully
self-contained — **no build step, no backend** — and auto-run & loop. Full beat sheets,
voice-over, and on-screen callouts live in **`demo-script-30s.md`**.

### `pitch.html` — 痛点 → 目标 → 技术 (Pain → Goal → Tech)

Three 10-second beats cross-fade on one stage; a top-bar progress strip tracks 痛点 · 目标 · 技术.

| Window | Beat | What the animation does |
|--------|------|--------------------------|
| 0:00–0:10 | **痛点 · Pain** | A decision node draws one solid *"life you live"* road; a dashed, greyed *"road not taken — you never see it"* branches below. Gut-feel 🎲 and spreadsheet 📊 cards strike through. |
| 0:10–0:20 | **目标 · Goal** | The A/B parallel-futures board: A=cyan **Stay** (left) vs B=amber **Join** (right), dashed *"shared event · same seed"*, magenta **fork point**, scores count up (A 61 / B 67), chips *Probabilistic · Value-weighted · Reproducible*, recommendation + guardrail. **(wow ~0:11)** |
| 0:20–0:30 | **技术 · Tech** | Four technique cards build in — **fixed-seed paired counterfactual (M-b)**, **digital-twin personas (M-c · UserHarness, arXiv:2605.27721)**, **5-dim value-weighted scoring (M-d)**, **credibility card** — then stack badges (FastAPI · Claude API · SSE · Next.js · Recharts), the **9-agent Multica build** badge, and a seed-lock *reproducible #7f3ac1* flash. |

### `workflow.html` — full product, compressed

The ~88s walkthrough condensed to ~30s: **4 months instead of 6**, faster pacing, no camera pan.
The dashboard fills in **SSE order** mirroring the live contract on this branch.

| Window | What the animation does |
|--------|--------------------------|
| 0:00–0:04 | Decision Console: decision auto-types, **Quick · 4 mo**, *Run simulation* pressed |
| 0:04–0:08 | `clarify` — 2 condensed Q&A (runway types in; partner stability-weight chip picked); *Refine & run* |
| 0:08–0:12 | `status` run_started + `persona` — title, **Streaming** + **seed-locked** badges, A/B legend, 5 persona chips stream in |
| 0:12–0:17 | `timeline_event` skeletons (M1 A/B), dashed **shared event** at M2, `metric` curves draw, magenta **fork point** at M3 lands **(wow ~0:14)** |
| 0:17–0:22 | M3/M4 divergent cards; `branch_score` count-up (A 61 / B 67); value-weighted note |
| 0:22–0:27 | `credibility` gauge → 62 (data/causal/plausibility); `recommendation` + guardrail slide up; `done · 41 events`; seed flashes *#7f3ac1* |
| 0:27–0:30 | Closing follow-up question types in; violet **Branch C** what-if legend appears (loop replays from t=0) |

**HARD RULES held on screen (both):** A=cyan `#22D3EE` always LEFT, B=amber `#FBBF24` always RIGHT (never swapped); fork = magenta `#F472B6`; shared events = dashed slate `#94A3B8`; all copy probabilistic ("likely", "~60% chance") — never "will/definitely" (SYS-15); Space Grotesk / Inter on canvas `#0B0F1A`.

---

## Optional: deterministic capture with Playwright

Useful if you want frame-exact, repeatable output or a CI-rendered clip.

```bash
# from the repo root
npm i -D playwright
npx playwright install chromium     # one-time browser download

# DEFAULT — smoke-test ALL pages: load each, run one full loop, fail loudly
# on any JS/console error or a missing final beat. No files written.
node demo/record.mjs

# capture frames for one page (→ demo/frames/<page>/frame-XXXX.png)
node demo/record.mjs --frames pitch
node demo/record.mjs --frames workflow

# OR just the key beats as labelled stills (→ demo/frames/<page>/shot-XXs.png)
node demo/record.mjs --shots workflow
```

`record.mjs` runs each page in a 1280×720 viewport (deviceScaleFactor 2 → crisp). With no
flags it **smoke-tests all four pages** (`walkthrough`, `teaser`, `pitch`, `workflow`) and
**fails loudly (exit 1) on any JS/console error or if a page's final beat never lands** — so
it doubles as a render check for the two 30s pages. `--frames <page>` / `--shots <page>`
capture stills for one page (`pitch`, `workflow`, `teaser`, or `walkthrough`).

### Render the MP4 (optional — ffmpeg)

```bash
# e.g. the 30s pitch, from its captured frames
ffmpeg -framerate 10 -i demo/frames/pitch/frame-%04d.png \
       -c:v libx264 -pix_fmt yuv420p -r 30 -y demo/lynsea-pitch.mp4
```

MP4 rendering is intentionally optional: the final submission recording may just be a human screen-capture pass over the page, which is usually smoother than a 10fps frame dump.

---

## Design fidelity (must hold on screen)

The walkthrough lifts the `docs/design/` tokens directly:

- **Branch A = cyan `#22D3EE`, always LEFT. Branch B = amber `#FBBF24`, always RIGHT.** Never swapped; always paired with the A/B label and left/right position (color-blind safe).
- Fork point = magenta `#F472B6`; shared/perturbation events = slate `#94A3B8`, dashed.
- Fonts: **Space Grotesk** (headlines) / **Inter** (body). Canvas `#0B0F1A`, indigo brand `#8B7CF6`.
- **HARD RULE:** all copy is probabilistic ("likely", "~60% chance") — never "will/definitely".
