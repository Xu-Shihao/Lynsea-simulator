# Plan 07 — CoachArena

**One-liner:** A reproducible benchmark where coaching LLMs are graded not on what they *say* but on whether a population of simulated users actually *changes their life* over a 30-day simulated horizon.

**Idea lane:** Coach benchmark — agentic harness that scores life-coaching LLMs against simulated users with measurable coaching-outcome metrics (beat the baseline).

## 1. Problem & target user
Today every "AI life coach" claims to work, and there is no way to compare two of them. Existing LLM evals score single-turn helpfulness or politeness — they reward a model that *sounds* like a good coach, not one that produces behavior change. The buyer who hurts: an AI/health PM (e.g. Shanda Health) about to ship a coaching agent who must answer "is our coach better than GPT-4o, and by how much?" and has no defensible number. Today they ship on vibes. CoachArena gives them an outcome-grounded leaderboard.

## 2. The product
A CLI + web leaderboard that pits any coaching agent against a standardized population of **simulated users** and reports outcome metrics.

Core loop:
1. **Pick a cohort** — e.g. "50 users trying to build a running habit; varied motivation, life chaos, and adherence traits."
2. **Run the arena** — each simulated user holds a multi-day coaching dialogue with the coach-under-test; between sessions a *Life simulator* advances their world (work stress, a skipped week, a setback).
3. **Score outcomes** — judge agents extract goal-attainment, adherence trajectory, relapse recovery, and alliance, not transcript niceness.
4. **Read the leaderboard** — Coach A vs. Coach B vs. a scripted baseline, with confidence intervals and the single transcripts that explain the gap.

## 3. Why it's novel (technical innovation)
The novelty is **outcome-based, simulation-in-the-loop evaluation**, not LLM-as-judge of one reply. Three hard, interesting parts:
- **Persistent simulated users with hidden state.** Each user has a latent profile (motivation, self-efficacy, life-volatility) the coach can't see and a behavior model that updates between sessions — so the only way to score well is to actually move that hidden state, which a flattering wrapper cannot fake.
- **Adversarial life events.** A simulator injects setbacks (illness, a bad week) mid-engagement; we measure *relapse recovery*, the thing real coaching is judged on.
- **Counterfactual delta.** Every cohort also runs against a no-coach control and a scripted-baseline coach, so the headline number is a causal-style **lift over baseline**, not an absolute score that's easy to game.

## 4. Architecture & Claude Code / Multica role
- **Components:** `arena-runner` (orchestrator) → N **User agents** (persona + hidden behavior model) ↔ **Coach-under-test** (pluggable endpoint) → **Life-sim tick** (advances user state) → **Judge panel** (3 scorer agents: goal, adherence, alliance) → **Aggregator** (stats + leaderboard).
- **Multi-agent orchestration (central):** Multica fans out one isolated run per simulated user in parallel, then collects results — this is what makes a 50-user, multi-day benchmark finish in minutes instead of hours. The User/Coach/Judge separation is the core multi-agent mechanism.
- **Claude Code (central):** drives the build and is the runtime for User and Judge agents; the coach-under-test is swappable (Claude, GPT, or the team's own agent) so the harness stays model-neutral.
- **Models/skills/tools:** Claude for user-simulation + judging; a small structured "behavior-update" function (deterministic, seeded) for reproducibility; SQLite for runs; a static leaderboard page.

## 5. Build-day scope (the ~1-day vertical slice)
- **MVP that works:** one cohort (habit-formation, 8 users, 5 simulated days), two coaches (Claude-coach vs. scripted baseline), full pipeline → real leaderboard with lift-over-baseline + drill-into-transcript.
- **OUT of scope:** auth, multi-domain cohorts, fancy UI, human validation study, >1 metric family beyond the 3 judges.
- **Hour cut:** 0–2h user-agent + hidden-state model & seeds; 2–5h arena-runner + Multica fan-out + coach plug-in; 5–7h judge panel + aggregator + leaderboard page; 7–8h demo polish, pick the killer transcript.

## 6. The 2-minute demo
1. (0:15) "Which coach actually works? Watch us measure it." Show the empty leaderboard.
2. (0:45) Run `coacharena run habit --coaches claude,baseline` — terminal shows 8 simulated users coaching in parallel (Multica fan-out), life-events firing ("User 4 got sick on day 3").
3. (1:20) Leaderboard fills: Claude-coach **+38% goal attainment, +0.6 adherence** over baseline, with CIs.
4. (1:45) Click the gap → side-by-side transcript: baseline lectures after the setback; the winning coach re-plans and the user resumes. **Wow beat:** the number is grounded in a visible behavior change, not a judge's opinion.

## 7. Evaluation / proof it works
Headline metric is **lift over a no-coach control and a scripted baseline** on goal-attainment and adherence trajectory, with bootstrap confidence intervals across the cohort. Sanity checks that the bench discriminates: the scripted baseline must lose, the no-coach control must lose hardest, and a deliberately-sycophantic coach must NOT top the board (proving we score outcomes, not flattery). Reproducibility: fixed seeds → identical user trajectories across reruns.

## 8. Risks & unknowns
- **Simulated users may be unrealistic → numbers meaningless.** Mitigation: ground personas/behavior-update in published adherence base-rates; demo focuses on *relative* lift, which is robust to absolute miscalibration.
- **Judge agents are noisy/biased.** Mitigation: 3-judge panel + seeded users + report CIs; show the gap is larger than the noise band.
- **Multi-day, multi-user runs are slow/expensive on stage.** Mitigation: pre-bake a cached run for the live demo; live-run only a tiny 3-user cohort as proof it's real.

## 9. Self-score (1–5 each, with one line of justification)
- Technical innovation: 5/5 — outcome- and simulation-in-the-loop evaluation with lift-over-baseline is a genuinely new eval paradigm, not LLM-as-judge of one turn.
- Implementation quality (demo-ability in 1 day): 4/5 — pipeline is real and end-to-end, but a believable behavior model and clean leaderboard in one day is tight; cached run de-risks the stage.
- Potential impact: 4/5 — gives every coaching-AI team a defensible "are we better?" number; narrower buyer audience than a consumer app keeps it from 5.
- **Total: 13/15**
