# Lynsea — 1-Minute Hackathon Demo Script

> **Submission deliverable:** a one-minute video highlighting the specific **features, code, and functionality** the team built.
> **Recording surface:** [`walkthrough.html`](walkthrough.html) — a self-playing 60-second animation built from the `docs/design/` Stitch design. See [`README.md`](README.md) to produce the MP4.
> **Tagline:** *See your futures before you choose — a seeded, multi-agent decision-outcome simulator.*

- **Project:** Lynsea — Decision Outcome Simulator
- **Wow factor:** two *paired counterfactual* futures stream in side-by-side over SSE — same seed, same random events, only the decision differs — so the comparison is a controlled experiment, not two LLM guesses.
- **wow_moment_timestamp:** `00:30` (the magenta fork point + value-weighted scores resolve — well before the 60% mark)
- **Voiceover:** yes. Every spoken sentence is under 15 words. All copy is **probabilistic** ("likely", "~60% chance") — never "will/definitely" (`SYS-15`).

---

## Beat sheet (the 60-second arc)

| Window | Beat | What the audience sees | Feature / code named |
|--------|------|------------------------|----------------------|
| 0:00–0:08 | **Hook** | Decision Console; the real decision types itself in; Quick mode; Run. | Decision Console, Quick mode |
| 0:08–0:30 | **Core demo** | Dashboard streams: two A/B columns, personas, timeline cards, the shared event, curves drawing in. | SSE streaming, paired counterfactual (M-b), state forking (M-c), UserHarness personas |
| 0:30–0:48 | **Payoff** | Magenta fork point; 5 dimension curves; value-weighted scores; credibility gauge; recommendation + guardrail. | Fork detection, value-weighted scoring (M-d), credibility, probabilistic recommendation |
| 0:48–0:58 | **Differentiator + tech** | seed-lock badge flashes "reproducible #7f3ac1"; stack callouts. | NFR-01 seed-check, FastAPI+Claude+SSE, Next.js+Recharts, MiroFish, EverOS, 9-agent Multica build |
| 0:58–1:00 | **Close** | Hold on the full parallel-futures frame + tagline. | — |

---

## Time-coded script

```yaml
wow_moment_timestamp: 30

script:
  - timestamp_start: 0
    timestamp_end: 8
    narration: "Every big decision is a fork in the road. You only get to walk one."
    on_screen_callout: "Lynsea — See your futures before you choose"

  - timestamp_start: 8
    timestamp_end: 16
    narration: "Type one hard choice. Lynsea simulates both futures, side by side."
    on_screen_callout: "POST /api/simulate → SSE stream"

  - timestamp_start: 16
    timestamp_end: 24
    narration: "Each future is a world of belief-driven personas — your partner, your mentor."
    on_screen_callout: "Personas via UserHarness (arXiv:2605.27721) — conflict is emergent"

  - timestamp_start: 24
    timestamp_end: 30
    narration: "Both branches share the exact same random events. Only your decision changes."
    on_screen_callout: "Seeded paired counterfactual (M-b) — a controlled experiment"

  - timestamp_start: 30
    timestamp_end: 38
    narration: "Watch where the paths split: the magenta fork point — month three."
    on_screen_callout: "Fork detection — income stability vs. growth"

  - timestamp_start: 38
    timestamp_end: 48
    narration: "Five dimensions, scored to your values. It leans B — about a 60% chance, for you."
    on_screen_callout: "Value-weighted scoring (M-d) + probabilistic recommendation + guardrail"

  - timestamp_start: 48
    timestamp_end: 58
    narration: "Same seed, same result — every time. Built in parallel by nine agents on Multica."
    on_screen_callout: "NFR-01 seed-check · FastAPI + Claude + SSE · Next.js + Recharts · MiroFish · EverOS"

  - timestamp_start: 58
    timestamp_end: 60
    narration: "Lynsea. See your futures before you choose."
    on_screen_callout: "A simulation, not a prediction."
```

---

## Shot list (maps every demo step to a frame of `walkthrough.html`)

```yaml
shot_list:
  - timestamp_start: 0
    timestamp_end: 8
    screen_content: "Decision Console. Decision text types in; 'Quick · 6 mo' selected; Run button glows."
    action: "Hold on the hook; let the typewriter finish, then the Run press + ripple."

  - timestamp_start: 8
    timestamp_end: 12
    screen_content: "run_started: header + 'Streaming…' pill + A=cyan(left)/B=amber(right) legend + seed-locked badge."
    action: "Cut to the dashboard the instant it fades in."

  - timestamp_start: 12
    timestamp_end: 16
    screen_content: "world_ready: persona chips stream in (You·twin, Partner·opposed, Mother·opposed, Mentor, Best friend)."
    action: "Let the persona bar populate left-to-right."

  - timestamp_start: 16
    timestamp_end: 24
    screen_content: "timeline_event skeletons: M1 'Steady sprint' (A) vs 'Onboarding chaos' (B); dimension curves begin drawing."
    action: "Pan/hold on the two aligned columns filling in."

  - timestamp_start: 24
    timestamp_end: 30
    screen_content: "timeline_event perturbation: dashed slate 'Shared event — Partner receives a job offer' centered between both columns."
    action: "Pause on the dashed shared card; emphasize 'same seed in both'."

  - timestamp_start: 30
    timestamp_end: 38
    screen_content: "fork_point: magenta marker + glowing fork line + 'Paths diverge most here' explanation at M3."
    action: "Hold on the fork — this is the wow moment."

  - timestamp_start: 38
    timestamp_end: 48
    screen_content: "branch_score (A 61 / B 67 counting up, value-weighted note) + 5 dimension curves + credibility gauge filling to 62."
    action: "Let the scores count up and the gauge fill; then the recommendation strip slides up."

  - timestamp_start: 48
    timestamp_end: 58
    screen_content: "recommendation + guardrail strip; seed-locked badge flashes 'reproducible #7f3ac1'; stream pill → 'Done · 47 events'."
    action: "Hold on the full frame; this is where the VO names the stack and the 9-agent build."

  - timestamp_start: 58
    timestamp_end: 60
    screen_content: "Full parallel-futures composition, settled. Tagline overlay."
    action: "Freeze on the final frame."
```

---

## What was actually built — named explicitly in the video

**Core differentiators (the product's reason to exist):**
- **M-b — seeded paired counterfactual:** branches A & B share an identical seeded random-event stream; only the decision variable differs. Reproducible via `GET /api/run/{id}/seed-check` returning a stable `shared_event_hash` (`ALG-20/21`, **NFR-01**). This is the on-screen "seed-locked · reproducible #7f3ac1" badge.
- **M-c — state forking:** one persistent set of personas is forked into both branches, so personalities stay consistent and differences come from *agent interaction*, not narrative invention.
- **M-d — value-weighted scoring:** "better" means better *for this user* — scores weighted by their calibrated values (Growth, Autonomy), shown on the two composite score cards.
- **Emergent conflict via UserHarness** ([arXiv:2605.27721](https://arxiv.org/abs/2605.27721)): personas act on **beliefs** (including false/nested beliefs about others), so interpersonal conflict *emerges* from mutual misjudgement rather than being scripted.

**Foundations / references:**
- **MiroFish** (OASIS / CAMEL-AI) — the multi-agent world-simulation base, repurposed from "predict one future" to "compare paired controlled futures."
- **EverOS** — long-term, self-evolving agent memory (Markdown-as-truth, hybrid retrieval) behind the persona memory stream.

**Stack / code shown on screen:**
- **Backend:** FastAPI + uvicorn, Pydantic v2, **SSE streaming** (`run_started → world_ready → timeline_event → metric → fork_point → branch_score → credibility → recommendation → done`); all model calls through `backend/app/llm.py` (Claude API).
- **Frontend:** Next.js 14 (App Router) + TypeScript, **Recharts** dimension curves, Tailwind design tokens.
- **Build process:** a **9-agent parallel build** orchestrated on **Multica** against a single shared `BUILD_PLAN.md` integration contract (Wave 1 scaffolds → Wave 2 specialists → Wave 3 integration).

---

## Recording checklist

```yaml
recording_checklist:
  - "OS + browser notifications disabled; Do Not Disturb on."
  - "Screen resolution 1920×1080; record the browser viewport only (walkthrough auto-fits and letterboxes)."
  - "Open walkthrough.html in Chrome; hard-refresh so the animation starts at t=0."
  - "Confirm fonts loaded (Space Grotesk headings / Inter body) before hitting record."
  - "Confirm Branch A is cyan on the LEFT and Branch B is amber on the RIGHT — never swapped."
  - "Verify all copy reads probabilistic ('likely', '~60%') — no 'will/definitely'."
  - "Run the full 60s once to confirm: console → fork point lands ~0:30 → recommendation strip ~0:39 → seed flash ~0:44."
  - "Record one clean 60s loop; trim to exactly 0:00–1:00; lay the VO over it."
```

## Fallback plan

```yaml
fallback_plan:
  - trigger: "Live backend / Claude API is unavailable while filming."
    action: "Record walkthrough.html instead — it is fully self-contained and self-playing; no backend or network needed."
  - trigger: "The animation timing drifts or a beat is missed during capture."
    action: "Use demo/record.mjs (Playwright) to capture deterministic frames/clip; or re-record the single 60s loop — it always replays identically from t=0."
  - trigger: "Voiceover can't be recorded in time."
    action: "Ship with the on_screen_callout text burned in as captions; the walkthrough tells the story visually on its own."
```
