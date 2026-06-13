# Plan 09 — RehearseRoom

**One-liner:** A multi-agent household simulator that lets you rehearse a dreaded conversation against a faithful "twin" of the other person, predicts how it actually plays out, and coaches the one line that changes the outcome.

**Idea lane:** #09 — Relationship Sim — a multi-agent simulation of a household/relationship that lets a user rehearse a hard conversation and predicts how it plays out, coaching better communication.

## 1. Problem & target user
The conversation you keep putting off: telling your partner the budget is broken, asking a parent to stop drinking, giving an underperforming teammate hard feedback, setting a boundary with a roommate. The target user is anyone with a specific person and a specific dread — most acutely couples and caregivers. People rehearse these in the shower and still freeze, escalate, or cave in the room. Generic advice ("use I-statements") doesn't help because it isn't *that person*. Why now: agentic models can finally hold a stable, contradictory persona across a multi-turn fight, so the rehearsal can feel real instead of like a fortune cookie.

## 2. The product
1. **Describe the other person and the situation** — a few prompts (their relationship to you, what sets them off, a real quote or two, the thing you need to say).
2. **Rehearse live** — you type or speak your opening; a persona agent replies *in character*, with its own goals, soft spots, and defensiveness.
3. **Predict** — after the rehearsal, the system runs the conversation forward N times and shows the distribution of outcomes (resolved / stalemate / blowup) and the moments that tipped it.
4. **Coach** — it pinpoints the exact turns where you lost the room and rewrites one line, then lets you replay from that fork.
5. **Re-run** — you try the better line and watch the predicted blowup probability drop.

## 3. Why it's novel (technical innovation)
Not a chatbot that "plays your wife." Three mechanisms make it hard and interesting:
- **A persona built from evidence, not vibes.** A *Profiler* agent extracts a structured model — attachment style, hot-button triggers, conflict pattern (avoid/escalate), unmet need — and that struct *constrains* the persona agent so it stays consistently itself across turns instead of drifting agreeable.
- **Monte-Carlo conversation futures.** A *Simulator* runs the dialogue forward many times at higher temperature to produce an outcome distribution, not one canned ending — so the user sees probability, the tipping turns, and variance.
- **Counterfactual fork-and-replay.** A *Coach* agent diffs your line against an evidence-based reframe (NVC, Gottman repair attempts), and the Simulator re-scores the future from that fork — quantified before/after, not just advice.

## 4. Architecture & Claude Code / Multica role
- **Components:** Profiler agent → Persona agent (the twin) → Simulator (Monte-Carlo runner) → Judge (classifies each rollout outcome + tipping turns) → Coach (reframe + fork). A thin web UI (chat + an outcome bar chart + a "try the better line" button).
- **Multi-agent orchestration (Multica):** the five roles are distinct agents with separate prompts and memory; the Simulator fans out parallel persona⇄user rollouts and the Judge aggregates — exactly the multi-agent-world pattern the brief rewards, and the parallelism is the demo's "wow."
- **Claude Code role:** used to build the orchestration glue, the rollout fan-out/aggregate, and the eval harness; Claude is the reasoning engine for every agent. **Models:** Sonnet for persona + simulation rollouts (fast, parallel), Opus for the Coach reframe and the Judge rubric.

## 5. Build-day scope (the ~1-day vertical slice)
- **MVP that works:** one scenario (partner / money), real-time rehearsal chat, a working Monte-Carlo of ~8 rollouts with a 3-bucket outcome bar, one Coach reframe with fork-and-replay showing a numeric drop in blowup probability.
- **Out of scope:** voice, accounts, persistence beyond a session, more than one relationship type, mobile, fine-tuning.
- **Hour cut:** 0–2h persona struct + Persona agent loop; 2–5h Simulator fan-out + Judge buckets + bar chart; 5–7h Coach reframe + fork-and-replay + before/after number; 7–8h scripted demo + seed data polish.

## 6. The 2-minute demo
"This is a conversation I've been dreading." Type opener to the partner-twin: *"We need to talk about the credit card."* The twin gets defensive, fast. Hit **Predict** — bar chart fills live: **62% blowup, 30% stalemate, 8% resolved**, and the UI highlights the turn where it went sideways. Hit **Coach** — it rewrites the opener as a Gottman soft start-up. Hit **Replay from here** — re-run live, the bar re-animates to **18% blowup, 55% resolved**. Wow beat: same person, same problem, one line changed, watch the odds move.

## 7. Evaluation / proof it works
- **Outcome lift:** average resolved-rate before vs. after the Coach reframe across a fixed seed set of 20 scenarios (target: +25pp resolved, −30pp blowup).
- **Persona fidelity:** blind A/B — does a third agent (or a human) detect persona drift across 10 turns? Score consistency.
- **Calibration:** compare predicted outcome distribution against a small set of human-rated rollouts.

## 8. Risks & unknowns
- **Persona drifts agreeable** (models capitulate) → constrain with the explicit trigger/need struct + a system rule to defend its position; Judge flags drift.
- **Monte-Carlo too slow for live demo** → cap at 8 parallel rollouts on Sonnet, pre-warm, and cache the "before" run so only the "after" runs live.
- **Feels like manipulation / ethically heavy** → frame as *self*-coaching and empathy-building, never "win the argument"; surface the other person's unmet need, not just your win.

## 9. Self-score (1–5 each, with one line of justification)
- Technical innovation: 5/5 — evidence-constrained persona + Monte-Carlo conversation futures + counterfactual fork-and-replay is a genuinely novel mechanism, not a wrapper.
- Implementation quality (demo-ability in 1 day): 4/5 — single scenario with capped/cached rollouts is tight but achievable; the live re-animating bar is the risk.
- Potential impact: 5/5 — nearly everyone has a dreaded conversation; rehearsal that moves the odds is high-value for couples, caregivers, and managers.
- **Total: 14/15**
