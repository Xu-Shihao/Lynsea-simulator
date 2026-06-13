# Plan 06 — Health Persona

**One-liner:** Drop in your wearable + lab + journal exports and get a *queryable digital twin of your body* you can ask "what if I slept one more hour?" — and watch a multi-agent simulation play out the next 30 days.
**Idea lane:** #06 — Health Persona: ingest personal health data (wearables, journals, labs) and build a queryable, simulatable "life model" the user can ask what-if questions of.

## 1. Problem & target user

Meet **Dana, 34, knowledge worker with a Garmin, an Oura ring, and an annual blood panel.** She has *more* health data than any human in history and *zero* answers. Apps show her last night's sleep score but never tell her the thing she actually wants: "If I move my last coffee 3 hours earlier, will my resting heart rate and HRV actually recover, and how long until it shows up?" Her data is siloed (CSV from Garmin, JSON from Oura, a PDF lab, a Notes-app journal), and her doctor sees her for 12 minutes a year. The result: she gathers data she can't act on. This matters **now** because wearable penetration crossed ~1-in-3 adults and labs are going direct-to-consumer, so the input data finally exists — but no consumer tool turns it into a *causal, personal* model she can interrogate.

## 2. The product

A **personal health twin** built from the user's own exports.

Core loop (3–5 steps):
1. **Ingest** — drop in Garmin/Oura/Apple Health exports, a lab PDF, and free-text journal entries.
2. **Build the twin** — Claude Code agents normalize the messy files into a unified per-day timeline and fit a small personal model (sleep → HRV → mood → adherence) with documented coefficients.
3. **Ask a what-if** — Dana types "what if I sleep 1h more on weeknights?" in plain English.
4. **Simulate** — a multi-agent world rolls the twin forward 30 days under the intervention vs. a baseline, surfacing the divergence with uncertainty bands.
5. **Act** — she gets a ranked, *evidence-tagged* set of changes and a one-line "why" she can take to her doctor.

## 3. Why it's novel (technical innovation)

Not a chatbot over a CSV. The novel mechanism is a **fit-then-simulate twin**: Claude Code agents *write the personal model* (a transparent system of difference equations / regressions over the user's own days), so coefficients are individualized and inspectable — not a generic LLM guess. We then run **counterfactual rollouts**: identical stochastic seeds for baseline vs. intervention, so the *difference* is attributable to the change, not noise. The hard, interesting part is **causal hygiene on tiny, messy, auto-correlated personal data** (handling missingness, confounds like "she sleeps more *because* she's already sick"), which the agents handle with explicit assumption logging and confidence downgrades the judge can read.

## 4. Architecture & Claude Code / Multica role

- **Ingest agents** (Claude Code): one sub-agent per source format → emit a normalized daily-feature table + a data-quality report.
- **Modeler agent**: fits the personal sleep→HRV→mood model, writes the coefficients + assumptions to a versioned `twin.json`.
- **Simulator**: deterministic-seeded Monte Carlo rollout engine (plain Python) the agents call as a tool.
- **Critic agent** (Multica): independently reviews the model for leakage/over-claiming and stamps a confidence label — the multi-agent *check* is the trust mechanism, not decoration.
- **Orchestration:** Multica runs ingest agents in parallel, then serial modeler → simulator → critic. Claude Code is central to authoring the per-user model and the data-cleaning code on the fly.
- **Models/skills/tools:** Claude (reasoning + code-gen), Python sim tool, the twin schema.

## 5. Build-day scope (the ~1-day vertical slice)

- **MVP that works:** one real bundled dataset (Oura/Garmin sample + a synthetic lab + 10 journal days), the sleep→HRV→mood model, ONE what-if ("+1h sleep"), and a side-by-side 30-day chart with confidence bands + the critic's confidence stamp.
- **Out of scope:** live device OAuth, medical-grade validation, more than ~3 features, mobile UI, accounts.
- **Hour cut:** 0–2h ingest + normalize sample data; 2–5h modeler agent + twin.json + sim engine; 5–7h what-if UI + baseline-vs-intervention chart + critic agent; 7–8h demo polish + scripted query.

## 6. The 2-minute demo

1. (0:15) Show the *mess*: a Garmin CSV, an Oura JSON, a lab PDF, journal text on screen.
2. (0:30) One command — Claude Code agents fan out, normalize, and a `twin.json` appears with **real coefficients** ("your HRV gains ~4ms per +1h sleep, conf: medium").
3. (1:00) Dana types **"what if I sleep 1h more on weeknights?"** — the two-line chart animates baseline vs. intervention over 30 days; HRV diverges, mood lifts day ~9.
4. (1:30) The **critic agent** flashes: "⚠ confound: 3 of those nights you were ill — confidence downgraded to medium." → **the wow beat: it argues with itself and is honest.**
5. (2:00) Ranked actions + "tell your doctor" one-liner.

## 7. Evaluation / proof it works

- **Held-out backtest:** fit the twin on days 1–20, predict days 21–30, report MAE vs. a naive "tomorrow = today" baseline — show the twin beats persistence.
- **Counterfactual sanity:** known-direction checks (more sleep ⇒ higher HRV) pass; effect sizes within published literature ranges.
- **Before/after:** generic LLM answer ("sleep is good for you") vs. our quantified, person-specific, confidence-tagged answer.

## 8. Risks & unknowns

1. **Data wrangling eats the day** → ship with ONE pre-cleaned bundled dataset; live import is a stretch goal, not the demo path.
2. **Overfitting / spurious causal claims** → keep the model tiny, log assumptions, and let the critic agent visibly downgrade confidence (turns a weakness into the wow).
3. **Sim looks like a toy** → anchor coefficients to published effect sizes and show the backtest number so the curve is credible, not hand-drawn.

## 9. Self-score (1–5 each, with one line of justification)

- Technical innovation: 4/5 — fit-then-simulate personal twin + adversarial critic is a real mechanism, not a wrapper; bounded by simple model class in 1 day.
- Implementation quality (demo-ability in 1 day): 4/5 — bundled dataset + one what-if + one chart is a tight, achievable, genuinely-working slice.
- Potential impact: 4/5 — turns the dormant wearable+lab data of millions into actionable, doctor-ready answers; consumer-health timing is right.
- **Total: 12/15**
