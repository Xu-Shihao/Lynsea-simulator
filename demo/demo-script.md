# Lynsea — Hackathon Demo Script

> **Submission deliverable:** a demo video highlighting the specific **features, code, and functionality** the team built.
> **Recording surface:** [`walkthrough.html`](walkthrough.html) — a self-playing **~88-second** animation built from the `docs/design/` Stitch design. See [`README.md`](README.md) to produce the MP4.
> **Tagline:** *See your futures before you choose — a seeded, multi-agent decision-outcome simulator.*

- **Project:** Lynsea — Decision Outcome Simulator
- **Wow factor:** two *paired counterfactual* futures stream in side-by-side over SSE — same seed, same random events, only the decision differs — so the comparison is a controlled experiment, not two LLM guesses.
- **wow_moment_timestamp:** `00:26` (the magenta fork point resolves at month 3, then value-weighted scores + credibility land)
- **Voiceover:** yes. Every spoken sentence is under 15 words. All copy is **probabilistic** ("likely", "~60% chance") — never "will/definitely" (`SYS-15`).

---

## Beat sheet (the ~88-second arc)

| Window | Beat | What the audience sees | Feature / code named |
|--------|------|------------------------|----------------------|
| 0:00–0:06 | **Hook** | Decision Console; the real decision types itself in; Quick mode; Run pressed. | Decision Console, Quick mode |
| 0:06–0:16 | **Clarify** | Lynsea pauses and asks 3 follow-up questions; the user's answers type in (runway, partner's stability weight, regret); "Refine & run" pressed. | `clarify` SSE event, low-confidence persona refinement |
| 0:16–0:24 | **World + stream begins** | Dashboard: two A/B columns, persona chips, M1–M2 timeline cards, dimension curves begin drawing, the first dashed shared event. | SSE streaming, paired counterfactual (M-b), state forking (M-c), UserHarness personas |
| 0:24–0:34 | **Fork (payoff)** | Magenta fork point at M3; branches visibly diverge; camera pans the 6-month timeline; 2nd shared event at M4. | Fork detection, seeded shared-event stream |
| 0:34–0:50 | **Scores + credibility** | 6-month trajectory complete (M1–M6); value-weighted scores count up (A 61 / B 67); 5 dimension curves; credibility gauge fills to 62; recommendation + guardrail strip. | Value-weighted scoring (M-d), credibility, probabilistic recommendation + guardrail |
| 0:50–0:56 | **Differentiator + tech** | seed-lock badge "reproducible #7f3ac1"; "Done · 63 events"; stack callouts. | NFR-01 seed-check, FastAPI+Claude+SSE, Next.js+Recharts, MiroFish, EverOS, Multica parallel build |
| 0:56–1:07 | **Closing follow-up** | Lynsea asks back: "What if I negotiate a 3-month sabbatical before deciding?"; a violet **Branch C** what-if forks from M3. | `what-if` Branch C (P1), pressure-test loop |
| 1:07–1:28 | **Close** | Camera settles on the full parallel-futures frame + tagline. | — |

---

## Time-coded script

```yaml
wow_moment_timestamp: 26

script:
  - timestamp_start: 0
    timestamp_end: 6
    narration: "Every big decision is a fork in the road. You only get to walk one."
    on_screen_callout: "Lynsea — See your futures before you choose"

  - timestamp_start: 6
    timestamp_end: 16
    narration: "Lynsea pauses to ask what it needs — runway, who opposes you, your fear."
    on_screen_callout: "clarify event — refine low-confidence personas before simulating"

  - timestamp_start: 16
    timestamp_end: 24
    narration: "Then it simulates both futures side by side, as worlds of belief-driven personas."
    on_screen_callout: "POST /api/simulate → SSE · personas via UserHarness (arXiv:2605.27721)"

  - timestamp_start: 24
    timestamp_end: 34
    narration: "Both branches share the same random events. Only your decision changes — watch them split."
    on_screen_callout: "Seeded paired counterfactual (M-b) — fork point at month 3"

  - timestamp_start: 34
    timestamp_end: 50
    narration: "Six months, five dimensions, scored to your values. It leans B — about 60%."
    on_screen_callout: "Value-weighted scoring (M-d) + credibility + probabilistic recommendation + guardrail"

  - timestamp_start: 50
    timestamp_end: 56
    narration: "Same seed, same result — every time. Built in parallel by agents on Multica."
    on_screen_callout: "NFR-01 seed-check · FastAPI + Claude + SSE · Next.js + Recharts · MiroFish · EverOS"

  - timestamp_start: 56
    timestamp_end: 67
    narration: "Then Lynsea pushes back: what if you negotiated a sabbatical first?"
    on_screen_callout: "What-if Branch C — fork a third future from month 3"

  - timestamp_start: 67
    timestamp_end: 88
    narration: "Lynsea. See your futures before you choose."
    on_screen_callout: "A simulation, not a prediction."
```

---

## Shot list (maps every demo step to a frame of `walkthrough.html`)

```yaml
shot_list:
  - timestamp_start: 0
    timestamp_end: 6
    screen_content: "Decision Console. Decision text types in; 'Quick · 6 mo' selected; Run button presses."
    action: "Hold on the hook; let the typewriter finish, then the Run press."

  - timestamp_start: 6
    timestamp_end: 13
    screen_content: "clarify card: 3 questions appear; answers type in — runway months, partner's stability weight, the regret outcome."
    action: "Let each answer type in; emphasize Lynsea is modelling the user's world, not guessing."

  - timestamp_start: 13
    timestamp_end: 16
    screen_content: "'Refine & run' pressed; transition to dashboard; A=cyan(left)/B=amber(right) legend + seed-locked badge."
    action: "Cut to the dashboard the instant it fades in."

  - timestamp_start: 16
    timestamp_end: 22
    screen_content: "world_ready: 6 persona chips stream in (You·twin, Partner·opposed, Mother·opposed, Mentor, Best friend, Ex-colleague); M1 skeletons; curves begin."
    action: "Let the persona bar and first timeline cards populate."

  - timestamp_start: 22
    timestamp_end: 26
    screen_content: "perturbation: dashed slate shared event at M2 centered between both columns."
    action: "Pause on the dashed shared card; 'same seed in both'."

  - timestamp_start: 26
    timestamp_end: 30
    screen_content: "fork_point: magenta marker + glowing fork line + 'paths diverge most here' at M3; camera pans down."
    action: "Hold on the fork — this is the wow moment."

  - timestamp_start: 30
    timestamp_end: 40
    screen_content: "2nd shared event at M4; M4–M6 timeline cards fill in both columns; camera pans the long 6-month timeline."
    action: "Pan through the extended trajectory; show the futures are long, not a snapshot."

  - timestamp_start: 40
    timestamp_end: 50
    screen_content: "branch_score (A 61 / B 67 counting up, value-weighted) + 5 dimension curves + credibility gauge filling to 62; recommendation + guardrail strip slides up."
    action: "Let the scores count up and the gauge fill; then the recommendation strip."

  - timestamp_start: 50
    timestamp_end: 56
    screen_content: "seed-locked badge flashes 'reproducible #7f3ac1'; stream pill → 'Done · 63 events'."
    action: "Hold on the full frame; VO names the stack and the parallel build."

  - timestamp_start: 56
    timestamp_end: 67
    screen_content: "followup box: 'What if I negotiate a 3-month sabbatical before deciding?' types in; violet Branch C legend + what-if card forks from M3."
    action: "Let the closing question type in; reveal Branch C in violet."

  - timestamp_start: 67
    timestamp_end: 88
    screen_content: "Camera settles back on the full parallel-futures composition. Tagline overlay."
    action: "Freeze on the final frame; loop replays identically from t=0."
```

---

## What was actually built — named explicitly in the video

**Core differentiators (the product's reason to exist):**
- **M-b — seeded paired counterfactual:** branches A & B share an identical seeded random-event stream; only the decision variable differs. Reproducible via `GET /api/run/{id}/seed-check` returning a stable `shared_event_hash` (`ALG-20/21`, **NFR-01**). This is the on-screen "seed-locked · reproducible #7f3ac1" badge and the two dashed shared events (M2, M4).
- **M-c — state forking:** one persistent set of personas is forked into both branches, so personalities stay consistent and differences come from *agent interaction*, not narrative invention.
- **M-d — value-weighted scoring:** "better" means better *for this user* — scores weighted by their calibrated values (Growth, Autonomy), shown on the two composite score cards.
- **Clarify loop:** before simulating, Lynsea asks targeted follow-up questions to refine low-confidence personas (`clarify` SSE event) — and at the end, pushes a what-if back at the user (Branch C).
- **Emergent conflict via UserHarness** ([arXiv:2605.27721](https://arxiv.org/abs/2605.27721)): personas act on **beliefs** (including false/nested beliefs about others), so interpersonal conflict *emerges* from mutual misjudgement rather than being scripted.

**Foundations / references:**
- **MiroFish** (OASIS / CAMEL-AI) — the multi-agent world-simulation base, repurposed from "predict one future" to "compare paired controlled futures."
- **EverOS** — long-term, self-evolving agent memory (Markdown-as-truth, hybrid retrieval) behind the persona memory stream.

**Stack / code shown on screen:**
- **Backend:** FastAPI + uvicorn, Pydantic v2, **SSE streaming** (`run_started → clarify → world_ready → timeline_event → metric → fork_point → branch_score → credibility → recommendation → done`); all model calls through `backend/app/llm.py` (Claude API).
- **Frontend:** Next.js 14 (App Router) + TypeScript, **Recharts** dimension curves, Tailwind design tokens.
- **Build process:** a **parallel multi-agent build** orchestrated on **Multica** against a single shared `BUILD_PLAN.md` integration contract (Wave 1 scaffolds → Wave 2 specialists → Wave 3 integration).

---

## Recording checklist

```yaml
recording_checklist:
  - "OS + browser notifications disabled; Do Not Disturb on."
  - "Screen resolution 1920×1080; record the browser viewport only (walkthrough auto-fits and letterboxes)."
  - "Open walkthrough.html in Chrome; hard-refresh so the animation starts at t=0."
  - "Confirm fonts loaded (Space Grotesk headings / Inter body) before hitting record."
  - "Confirm Branch A is cyan on the LEFT and Branch B is amber on the RIGHT — never swapped; Branch C is violet."
  - "Verify all copy reads probabilistic ('likely', '~60%') — no 'will/definitely'."
  - "Run the full ~88s once to confirm: console → clarify Q&A ~0:06–0:14 → fork point ~0:26 → scores/recommendation ~0:40–0:48 → seed flash ~0:52 → Branch C follow-up ~0:57–1:07."
  - "Record one clean ~88s loop; lay the VO over it. Trim to your platform's limit if shorter is required."
```

## Fallback plan

```yaml
fallback_plan:
  - trigger: "Live backend / Claude API is unavailable while filming."
    action: "Record walkthrough.html instead — it is fully self-contained and self-playing; no backend or network needed."
  - trigger: "The animation timing drifts or a beat is missed during capture."
    action: "Use demo/record.mjs (Playwright) to capture deterministic frames/clip; or re-record the single loop — it always replays identically from t=0."
  - trigger: "Voiceover can't be recorded in time."
    action: "Ship with the on_screen_callout text burned in as captions; the walkthrough tells the story visually on its own."
  - trigger: "Submission requires a strict 60-second cut."
    action: "Trim the closing Branch C beat (0:56+) and the camera-settle hold; the core arc (hook → clarify → fork → scores → recommendation) lands inside 0:00–0:50."
```
