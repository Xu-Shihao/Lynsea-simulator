# Plan 05 — Keel (Habit Engine)

**One-liner:** A digital twin of your willpower that simulates tomorrow's you against five science-based nudges, then sends only the one most likely to keep you on course.
**Idea lane:** #05 Habit engine — predictive behavior-change engine that simulates adherence and picks nudges, grounded in behavioral science.

## 1. Problem & target user
Maya, 31, has restarted a 7am-run habit four times this year. Generic habit apps fire the *same* reminder at the same time and she's tuned them out — "notification fatigue." The hard truth in behavior science: the optimal nudge is **state-dependent**. On a low-sleep night before a 7am meeting, an aggressive "Keep your streak alive!" push triggers avoidance; a gentle implementation-intention prompt works. No consumer tool reasons about *which* nudge fits *tonight's* state before sending. People who most need adherence support — chronic-condition self-management, mental-health routines, fitness — get one-size-fits-all pressure and quit.

## 2. The product
Keel is a closed-loop controller for one habit. Core loop:
1. **Sense** — pull tonight's context (calendar, last few outcomes, self-reported energy/sleep) into a latent state: Motivation, Ability/friction, Prompt-responsiveness (Fogg's B=MAP).
2. **Simulate** — an "inner council" of agents role-plays tomorrow's Maya and predicts baseline follow-through probability.
3. **Optimize** — a Nudge Strategist proposes 5 candidate nudges (each tied to a named technique); Keel re-runs the simulation for each and ranks them by *predicted* follow-through.
4. **Act** — send the single winning nudge with a one-line rationale.
5. **Learn** — when the real outcome arrives, the twin updates its beliefs about what works for *this* user.

## 3. Why it's novel (technical innovation)
This is **model-predictive control for behavior change**: simulate-then-act, not react. The non-obvious mechanism is *forward-simulating candidate nudges before any is sent* and choosing by predicted outcome — A/B testing in a twin instead of on the user. The simulator is a multi-agent "inner council" where each agent embodies a behavioral force (Motivation, Friction, a present-bias Saboteur, Context), so the prediction is decomposable and *explainable*, not a black-box score. The learning loop closes it: predicted vs. actual outcomes recalibrate the twin. That's a real control system, not a chatbot that says "you've got this."

## 4. Architecture & Claude Code / Multica role
- **Components:** State Estimator → **Council** (Motivation, Friction, Saboteur, Context agents) → Predictor (emits a calibrated follow-through probability + reasons) → Nudge Strategist (5 candidates) → **Optimizer** (fans the K nudges back through the Council in parallel, picks argmax) → Outcome Updater.
- **Multica is central:** the Council is a literal multi-agent workflow; the Optimizer is a parallel fan-out (K simulations) → barrier → pick-best — exactly Multica's structured orchestration. This is the differentiator a generic single-prompt app can't claim.
- **Claude Code is central:** builds the harness, agent prompts, schemas, and dashboard in a day, and Claude models *are* the runtime brain — Opus for council deliberation/strategy, Haiku for the cheap parallel nudge simulations.
- **Models/skills:** Claude structured outputs for the probability schema; behavioral library (Fogg B=MAP, COM-B, implementation intentions, temptation bundling, fresh-start effect).

## 5. Build-day scope (the ~1-day vertical slice)
- **MVP that works:** one habit; a seeded *synthetic* user with known behavioral parameters (lets us prove calibration); Council→Predictor; Strategist with 5 techniques; Optimizer fan-out; learning update; web dashboard showing the adherence curve, the nudge leaderboard, and the chosen rationale.
- **Out of scope:** real wearable/calendar APIs (mock context), mobile push/native app, multi-habit, accounts, long-term retention study.
- **Hours:** 0–2h scaffold + state model + schemas; 2–5h Multica Council + Predictor + calibrate on synthetic cohort; 5–7h Strategist + Optimizer fan-out + learning update + dashboard; 7–8h backtest numbers + demo polish.

## 6. The 2-minute demo
Tuesday 9pm, Maya's dashboard. (0:00) Show her plan + predicted adherence curve. (0:20) Keel pulls context (7am meeting, skipped yesterday, low sleep); the Council deliberates live (stream the Multica run) → baseline follow-through **38%**. (0:55) Strategist proposes 5 nudges; Optimizer fans them out; leaderboard fills in: aggressive streak-pressure **31% (backfires!)**, implementation-intention + temptation-bundle **71%**. Keel sends the winner with its one-line reason. (1:30) Fast-forward: Maya ran — the twin updates, the curve bends up, and its belief "pressure fails Maya on low-sleep mornings" sharpens. **Wow beat:** Keel predicted the obvious nudge would *backfire* — and was right.

## 7. Evaluation / proof it works
Backtest on a held-out synthetic cohort with ground-truth behavioral params. Metric: simulated adherence rate / days-to-habit-formation for **Keel (MPC) vs. random nudge vs. fixed nudge vs. naive "just encourage them" LLM**. Report calibration: predicted vs. actual follow-through (reliability curve, Brier score improving as the twin learns). Ablation: drop the simulator (send the LLM's first idea) and show the loop wins.

## 8. Risks & unknowns
1. **Predictions look arbitrary / uncalibrated.** → Seed a synthetic user with *known* params; show the twin recovers them and report Brier score so it's grounded, not hand-wavy.
2. **Multi-agent latency in a live demo** (K sims × council). → Haiku for parallel sims, pre-warm/cache, and keep a recorded fallback run.
3. **"It's just an LLM guessing probabilities."** → Anchor every agent and nudge to a named, cited mechanism; let the ablation vs. naive LLM carry the argument.

## 9. Self-score (1–5 each, with one line of justification)
- Technical innovation: 5/5 — closed-loop MPC over an explainable multi-agent behavioral twin that simulates nudges *before* sending and learns from outcomes; not a wrapper.
- Implementation quality (demo-ability in 1 day): 4/5 — fully synthetic data means zero integrations and the fan-out is Multica's wheelhouse; the only hard part is convincing calibration in a day.
- Potential impact: 4/5 — adherence is a massive cross-domain problem (chronic care, mental health, fitness); "simulate before nudge" could cut notification fatigue, but it's still early/unproven.
- **Total: 13/15**
