# Plan 03 — Decision Twin

**One-liner:** Point it at one fork-in-the-road decision and it spins up a digital twin of *you* that lives out each branch for 5 simulated years — so you watch your alternate futures play out before you choose.
**Idea lane:** Decision twin — counterfactual "digital twin" that simulates branching what-if futures for a single big decision, with outcome scores.

## 1. Problem & target user
Maya, 29, has a concrete offer: stay in her stable Boston job, or take a 30%-pay-cut role at a Seattle startup. The decision is *high-stakes, low-frequency, irreversible* — exactly the kind humans are worst at. She can't A/B test her own life. Friends give anecdotes, ChatGPT gives generic pros/cons, and a spreadsheet can't model that the Seattle move strains her relationship in year 2 but pays off in year 4. People facing job moves, relocations, grad-school, and relationship decisions overweight the vivid near-term and ignore the compounding downstream — and then ruminate for months. They don't need advice; they need to *see the trajectory*.

## 2. The product
A counterfactual simulator for a single decision.
1. **Frame the fork** — user states the decision and the 2–3 options in plain language ("stay vs. move to Seattle").
2. **Build the twin** — a short structured interview extracts the variables that actually drive *this* person's outcomes: finances, relationships, health, career trajectory, risk tolerance, values weights.
3. **Simulate each branch** — for every option, run a multi-agent monthly simulation over a 3–5 year horizon; life-domain agents update state and inject realistic events (a layoff, a breakup, a promotion).
4. **Score & contrast** — each branch yields a trajectory across domains plus a values-weighted Life Outcome Score, with the divergence points called out.
5. **Interrogate** — user asks "what if the startup folds in year 1?" and that counterfactual re-runs in seconds.

## 3. Why it's novel (technical innovation)
Not a pros/cons generator. Three non-obvious mechanisms: (a) a **shared world-state object** the agents mutate month-by-month, so effects *compound and interact* across domains rather than being independently hallucinated — the move hurts the relationship which later hurts career focus; (b) **paired counterfactual rollouts under a fixed random seed** so branches differ only by the decision, isolating *causal* effect the way a controlled trial would; (c) a **values-weighted scoring function** the user calibrates, so "better" means better *for them*, not a generic optimum. The hard part is keeping multi-year, multi-agent trajectories coherent and comparable — that's the engineering, and Claude Code's agent orchestration is what makes it tractable in a day.

## 4. Architecture & Claude Code / Multica role
- **Components:** (1) Twin-Builder agent (interview → structured `UserModel` JSON); (2) Orchestrator that forks N branches and steps a shared `WorldState`; (3) per-domain agents — Career, Finance, Relationships, Health — each proposing monthly state deltas + events; (4) Scorer that folds trajectories into the values-weighted outcome; (5) thin React timeline UI.
- **Claude Code / Multica is central:** Multica orchestrates the parallel branch rollouts and the per-domain sub-agents; Claude Code authored the simulation loop, the `UserModel`/`WorldState` schemas, and the agent prompts, and is used live to re-run counterfactuals. The multi-agent world *is* the product, not a wrapper.
- **Models/skills/tools:** Claude (Sonnet for domain agents, Opus for the Twin-Builder and Scorer), seeded sampling for reproducibility, JSON-schema-constrained outputs, simple SQLite/JSON state store.

## 5. Build-day scope (the ~1-day vertical slice)
- **MVP:** one decision (job stay-vs-move), 2 branches, 36 monthly steps, 4 domain agents, the values-weighted score, a side-by-side trajectory chart, and ONE live counterfactual re-run.
- **Out of scope:** account/auth, importing real bank/health data (use guided interview), >2 branches, mobile, persistence beyond a session.
- **Hour cut:** 0–2h schemas + Twin-Builder interview; 2–5h orchestrator + domain agents + shared WorldState stepping; 5–7h scorer + timeline UI + counterfactual re-run; 7–8h seed-lock for a reliable demo, polish the "wow" beat.

## 6. The 2-minute demo
"This is Maya. One decision: stay, or move to Seattle." Type it in. 30-second interview auto-fills her twin. Hit **Simulate** — two timelines animate out across 3 years side by side: Stay is flat-comfortable; Move dips hard in year 1 (relationship strain, money tight) then climbs past Stay by year 3. Outcome scores: Stay 71, Move 78. **Wow beat:** judge picks the fear — "what if the startup folds?" — we re-run that one counterfactual live; Move collapses to 48 and the UI highlights the exact month it diverges. "Now she's not guessing — she's seen it."

## 7. Evaluation / proof it works
- **Causal sanity:** with a fixed seed, flipping only the decision changes the trajectory while shared random events stay identical — shown by a diff view (demonstrates it's a controlled counterfactual, not noise).
- **Face validity:** a panel rates whether the simulated trajectories are plausible vs. a single-prompt GPT "pros/cons" baseline (target: judges find paired rollouts markedly more concrete/decision-useful).
- **Before/after:** user's stated confidence in the decision, pre- vs. post-simulation.

## 8. Risks & unknowns
- **Incoherent long trajectories** (agents drift/contradict). *Mitigation:* enforce the shared WorldState as single source of truth; cap deltas per step; schema-validate every agent output.
- **"Fake-precision" credibility** — a 78 vs 71 score looks like false certainty. *Mitigation:* present ranges/bands and frame as "directional, not destiny"; emphasize the divergence point over the absolute number.
- **Demo flakiness from live LLM calls.** *Mitigation:* seed-locked deterministic run for the main path; pre-warmed cache; the single counterfactual is the only live call on stage.

## 9. Self-score (1–5 each, with one line of justification)
- Technical innovation: 5/5 — shared-state compounding sim + seeded paired counterfactuals + values-weighted scoring is a genuinely novel mechanism, not a wrapper.
- Implementation quality (demo-ability in 1 day): 3/5 — multi-agent multi-year coherence is the riskiest slice; seed-locking makes it demo-able but the build is ambitious for a day.
- Potential impact: 4/5 — high-stakes irreversible decisions are universal and underserved; the "see your alternate future" hook is memorable and broadly applicable.
- **Total: 12/15**
