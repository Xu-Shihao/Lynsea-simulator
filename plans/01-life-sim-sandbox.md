# Plan 01 — Lynsea

**One-liner:** Describe a decision you're stuck on, and Lynsea spins up a living world of the people and forces around you, fast-forwards 6 months under each option, and shows you the futures side-by-side — with the human reactions that drive them.

**Idea lane:** Life-sim sandbox — a multi-agent simulated world that ingests a user's situation, spins up agents for the people/forces in their life, simulates forward in time, and predicts the outcomes of different choices.

## 1. Problem & target user
Meet Mara, 29, weighing whether to quit her stable job to join a friend's startup. The hard part isn't the spreadsheet math — it's the *second-order human consequences*: how her partner reacts to the income dip, whether her co-founder friendship survives equity talks, how her manager responds if she hedges. People are bad at simulating other minds across time, so they freeze, ask a few biased friends, or doom-scroll Reddit threads. Anyone facing a high-stakes, multi-stakeholder life decision (career pivots, relocations, going back to school, ending/repairing a relationship) hurts here. It matters now because Claude-class models can finally role-play distinct, persistent personas with memory — making a *simulated social world*, not just advice, newly feasible.

## 2. The product
A web app with one input box: "What are you deciding, and who's involved?"
Core loop (4 steps):
1. **Ingest** — Mara types her situation; Claude extracts the *entities* (partner, co-founder, manager, herself) and the *decision options* (stay / join full-time / join part-time).
2. **Populate** — Lynsea instantiates one persistent agent per person, each with a Claude-authored persona card (goals, fears, communication style) the user can edit.
3. **Simulate** — For each option, the world steps forward in N "weeks." Each step, agents react to events and to each other; an Outcome agent logs concrete events (raise, fight, burnout, breakthrough).
4. **Compare** — A side-by-side timeline of the 2–3 futures, each with a happiness/stress/finance trace and the 3 pivotal moments that bent the outcome.

## 3. Why it's novel (technical innovation)
Not a "what should I do?" chatbot. The novel mechanism is a **multi-agent counterfactual simulator with branching world-state**: the same cast of persistent persona-agents is forked across decision branches and stepped through time, so differences between futures emerge from *agent interactions*, not from a single model's narrated guess. Two hard, interesting pieces: (a) **state divergence control** — keeping personas consistent while letting only the decision variable differ, so the comparison is honest; (b) a **Referee/Outcome agent** that converts free-form social dialogue into structured, scoreable events to prevent narrative drift and runaway optimism.

## 4. Architecture & Claude Code / Multica role
- **Frontend:** single-page app — input → persona cards → "Run simulation" → comparison timeline.
- **Orchestrator (Multica multi-agent):** spawns one sub-agent per persona + a Referee agent + an Outcome/scoring agent. World-state object (shared JSON) holds week number, events, and per-agent memory; the orchestrator forks it per decision branch and runs the step loop.
- **Claude Code is central** two ways: (1) it *builds* the orchestration + tools on build day; (2) at runtime, Claude models *are* the persona/referee agents, each driven by a structured prompt + the running world-state.
- **Tools/skills:** Claude (persona reasoning + extraction), Multica orchestration for the agent fan-out, a deterministic scoring tool for the metric traces.

## 5. Build-day scope (the ~1-day vertical slice)
- **MVP:** one scenario, exactly 2 decision branches, 3 persona agents + referee, 6 weekly steps, rendered side-by-side timeline with one metric line per future and 3 highlighted pivotal moments. Personas editable before run.
- **Out of scope:** real personal-data ingestion, login/persistence, more than 3 branches, fine-grained calibration, mobile polish.
- **Hour cut:** 0–2h orchestrator + world-state schema; 2–5h persona/referee/outcome agent loop running end-to-end in terminal; 5–7h timeline UI + comparison; 7–8h scripted demo scenario + polish.

## 6. The 2-minute demo
1. (0:00) Type Mara's dilemma live; show Claude extracting 3 people + 2 options. (0:25)
2. Click a persona card, tweak the partner's "fear: financial instability" to show it's editable. (0:40)
3. Hit **Run** — the two futures animate week-by-week as agents talk; surface one *surprising* emergent event (e.g. the co-founder friendship fractures in the "join" branch). (1:20)
4. **Wow beat:** the side-by-side timeline lands — "stay" looks safe but flat; "join" spikes then craters at week 4 over an equity fight Mara hadn't considered. (1:45)
5. One line: "These futures came from the *people* in her life simulating each other — not from one model guessing." (2:00)

## 7. Evaluation / proof it works
- **Honesty check:** run the same scenario twice with only the decision variable changed; show persona traits stay stable (diff the persona memory) while outcomes diverge — proving the comparison isn't random.
- **Plausibility:** blind-rate 10 generated pivotal events as "could realistically happen" vs. a single-prompt baseline that just narrates a future; target multi-agent > baseline on plausibility and on *surfacing non-obvious consequences*.
- **Before/after:** show the single-LLM narration (generic, rosy) next to Lynsea's emergent conflict, side by side.

## 8. Risks & unknowns
- **Narrative runaway / unfalsifiable optimism.** Mitigation: Referee + structured Outcome events cap each step; metrics computed by a deterministic tool, not the storytelling agents.
- **Latency from many agent calls.** Mitigation: cap to 3 personas × 6 weeks × 2 branches; pre-run the demo scenario and cache; parallelize per-branch.
- **"It's just role-play" skepticism.** Mitigation: lead the demo with the state-divergence honesty check and the baseline comparison, not the story.

## 9. Self-score (1–5 each, with one line of justification)
- Technical innovation: 5/5 — branching multi-agent counterfactual world with state-divergence control is a genuine mechanism, not a wrapper.
- Implementation quality (demo-ability in 1 day): 3/5 — agent fan-out + timeline is achievable but the moving-parts count and latency are real day-of risks.
- Potential impact: 4/5 — high-stakes life decisions are universal and underserved; clear path beyond demo, though efficacy needs validation.
- **Total: 12/15**
