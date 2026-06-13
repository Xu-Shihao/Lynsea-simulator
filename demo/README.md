# Lynsea — Demo Video Kit

The 1-minute hackathon submission video for **Lynsea — Decision Outcome Simulator**.

> *Submit a short one-minute demo video highlighting the specific features, code, and functionality the team built.*

This folder is everything needed to produce that video:

| File | What it is |
|------|-----------|
| **`walkthrough.html`** | A self-contained, **~60-second self-playing** animated walkthrough built from the `docs/design/` Stitch design. **This is the recording surface** — open it and screen-record 60 seconds. |
| **`demo-script.md`** | The 1-minute video script: time-coded shot list (0:00–1:00), voice-over narration, and on-screen callouts naming the specific features, code, and functionality built. |
| **`record.mjs`** | Optional Playwright capture script — drives the page deterministically and writes PNG frames (and, via ffmpeg, an MP4). |

---

## Quickest path to the MP4 (recommended): screen-record the page

1. Open **`walkthrough.html`** in Chrome (double-click it, or `open demo/walkthrough.html`).
   It is fully self-contained — **no build step, no backend, no network** (fonts fall back gracefully offline).
   The animation auto-runs once on load and then loops.
2. Set the OS to Do Not Disturb; record at **1920×1080** (the stage auto-fits and letterboxes to any window).
3. Start your screen recorder (macOS: <kbd>⌘⇧5</kbd> → record the browser window), hard-refresh the page so it starts at `t=0`, and capture one clean 60-second loop.
4. Trim to exactly `0:00–1:00` and lay the voice-over from `demo-script.md` on top.

The 60-second animation tracks the script beats: console hook → dashboard streams in → **fork point lands ~0:30** → scores + credibility + recommendation by ~0:48 → seed-lock "reproducible" flash ~0:44 → hold.

### Timecode map (script ↔ animation)

| Script window | What the animation does |
|---------------|--------------------------|
| 0:00–0:08 | Decision Console: decision types in, Quick mode, Run pressed |
| 0:08–0:12 | `run_started` — header, streaming pill, A/B legend, seed-locked badge |
| 0:12–0:16 | `world_ready` — persona chips stream in |
| 0:16–0:24 | `timeline_event` skeletons (M1 A/B); dimension curves start drawing |
| 0:24–0:30 | `timeline_event` perturbation — dashed shared event |
| 0:30–0:38 | `fork_point` — magenta marker + explanation (**wow moment**) |
| 0:38–0:48 | `branch_score` (A 61 / B 67), 5 curves, `credibility` gauge → 62 |
| 0:48–0:58 | `recommendation` + guardrail; seed-locked "reproducible #7f3ac1" flash; `done` |
| 0:58–1:00 | Hold on the full parallel-futures frame |

---

## Optional: deterministic capture with Playwright

Useful if you want frame-exact, repeatable output or a CI-rendered clip.

```bash
# from the repo root
npm i -D playwright
npx playwright install chromium     # one-time browser download

# capture the full 60s as PNG frames (demo/frames/frame-XXXX.png)
node demo/record.mjs

# OR just the key script beats as labelled stills (demo/frames/shot-XXs.png)
node demo/record.mjs --shots
```

`record.mjs` runs the page in a 1280×720 viewport (deviceScaleFactor 2 → crisp), captures frames, and **fails loudly if the page throws any JS/console error** — so it doubles as a smoke test.

### Render the MP4 (optional — ffmpeg)

```bash
ffmpeg -framerate 10 -i demo/frames/frame-%04d.png \
       -c:v libx264 -pix_fmt yuv420p -r 30 -y demo/lynsea-demo.mp4
```

MP4 rendering is intentionally optional: the final submission recording may just be a human screen-capture pass over `walkthrough.html`, which is usually smoother than a 10fps frame dump.

---

## Design fidelity (must hold on screen)

The walkthrough lifts the `docs/design/` tokens directly:

- **Branch A = cyan `#22D3EE`, always LEFT. Branch B = amber `#FBBF24`, always RIGHT.** Never swapped; always paired with the A/B label and left/right position (color-blind safe).
- Fork point = magenta `#F472B6`; shared/perturbation events = slate `#94A3B8`, dashed.
- Fonts: **Space Grotesk** (headlines) / **Inter** (body). Canvas `#0B0F1A`, indigo brand `#8B7CF6`.
- **HARD RULE:** all copy is probabilistic ("likely", "~60% chance") — never "will/definitely".
