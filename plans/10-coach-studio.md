# Plan 10 — Coach Studio

**One-liner:** A no-code studio where a non-engineer drags evidence-based "coaching blocks" onto a canvas and Claude Code compiles them into a real, runnable multi-agent coach — in minutes, not months.
**Idea lane:** Coach Studio — a Claude Code-native, no-code studio to assemble your own evidence-based coaching agent from multi-agent building blocks.

## 1. Problem & target user
Meet **Dr. Lena**, a sleep psychologist at a digital-health clinic. She has a proven CBT-I protocol (sleep restriction, stimulus control, worry-time, relapse plan) living in a Google Doc. She wants a coaching agent that runs *her* protocol with *her* safety rules — but she can't code, and the engineering backlog is 6 weeks deep. Today her only options are (a) a generic chatbot that ignores her protocol, or (b) a hand-built bespoke agent she can't afford. The result: clinical expertise stays trapped in documents while patients get generic advice. Every domain expert in coaching/therapy/health hits this same wall. Why now: Claude Code can author and wire multi-agent systems from natural language, so the *expert*, not the engineer, can finally hold the pen.

## 2. The product
Coach Studio is a visual canvas + chat. The expert builds a coach without writing code:
1. **Describe** the coaching goal in plain language ("CBT-I sleep coach, 4-week arc, escalate self-harm mentions").
2. **Assemble** by dragging blocks from a palette: *Intake*, *Protocol* (CBT/MI/ACT step machines), *Memory*, *Safety Guardrail*, *Homework Tracker*, *Progress Scorer*. Each block is an agent or skill.
3. **Compile** — Claude Code reads the canvas + the expert's protocol doc and generates the actual agent definitions, system prompts, tool wiring, and a Multica multi-agent graph.
4. **Test-drive** in a built-in simulated-patient panel; watch the agents talk, edit a block, recompile.
5. **Publish** a shareable coach others can chat with.

## 3. Why it's novel (technical innovation)
It is not a prompt builder. The canvas is a **typed specification** and Claude Code is the **compiler from spec → running multi-agent system**: it emits agent role files, inter-agent routing, guardrail policies, and the Multica orchestration graph, then *self-tests* by running the simulated-patient panel and patching blocks that misbehave. The hard, interesting parts: (1) a block contract so heterogeneous coaching primitives compose safely (a Safety block can veto any other block's output); (2) Claude Code as code-author *and* QA, closing the build→test→fix loop without a human engineer; (3) protocol grounding — the expert's uploaded doc becomes cited, enforced step logic, not vibes.

## 4. Architecture & Claude Code / Multica role
- **Frontend:** React canvas (drag-drop blocks, JSON spec) + chat test panel.
- **Compiler (Claude Code, central):** takes `spec.json` + protocol doc → generates `agents/*.md`, routing config, guardrail rules; runs the test panel; reads failures and edits files. This is the core agentic loop.
- **Runtime (Multica multi-agent):** Orchestrator routes turns between Protocol-agent, Safety-agent (veto power), Memory, and Scorer. Simulated-patient is itself a Multica agent for test-drive.
- **Models/skills/tools:** Claude (Opus for compile/reasoning, Sonnet for runtime turns); Multica orchestration for the agent graph; file tools for codegen; retrieval over the uploaded protocol doc.

## 5. Build-day scope (the ~1-day vertical slice)
- **MVP:** Canvas with 5 working blocks (Intake, Protocol, Safety, Memory, Scorer); compile one real coach from a CBT-I doc; test-drive against a scripted simulated patient; one recompile-after-edit cycle.
- **Out of scope:** Auth, marketplace/publish, billing, arbitrary block authoring by users, mobile, persistence beyond a session.
- **Hour cut:** 0–2h block schema + spec JSON + canvas stub; 2–5h Claude Code compiler (spec→agents) + Multica runtime graph; 5–7h Safety-veto + simulated-patient test panel + edit→recompile; 7–8h demo polish & scripted run.

## 6. The 2-minute demo
1. (0:00) Empty canvas. Paste a one-line goal + drop a CBT-I protocol PDF. "I'm a sleep psychologist, not a coder."
2. (0:20) Drag Intake → Protocol → Safety → Scorer onto the canvas, connect them. Click **Compile**.
3. (0:35) Split-screen: Claude Code writes the agent files live; toast "Compiled 4 agents + Multica graph."
4. (0:50) Test-drive: type "I can't sleep, I've been awake for 30 hours and feel hopeless." Watch the Safety agent **veto** the Protocol agent and route to a crisis response — the wow beat: guardrails are real, not decorative.
5. (1:25) Edit the Protocol block ("add worry-time step"), click Recompile, re-run — new step appears. "From doc to working, safe, multi-agent coach in two minutes."

## 7. Evaluation / proof it works
- **Protocol fidelity:** scripted 10-turn transcript scored by a rubric agent — does the coach follow the uploaded steps in order? Target ≥ 90% step-coverage vs. a generic chatbot baseline (~30%).
- **Safety:** 8 red-team prompts (self-harm, dosing, off-protocol); measure veto/route rate. Target 8/8 vs. baseline.
- **Build time:** wall-clock from doc → runnable coach (minutes) vs. "engineer sprint" baseline.

## 8. Risks & unknowns
1. **Compile is flaky / slow on stage.** → Pre-warm a cached compile; demo the edit→recompile on a small block so it's fast and deterministic.
2. **Block-composition complexity explodes.** → Ship exactly 5 blocks with a fixed contract; no user-authored blocks day-of.
3. **Safety veto looks staged.** → Use a genuinely live guardrail agent with logged reasoning shown in the UI, plus 2 unscripted red-team prompts from a judge.

## 9. Self-score (1–5 each, with one line of justification)
- Technical innovation: 5/5 — Claude Code as a spec→multi-agent **compiler** with a self-test/fix loop is a genuinely novel mechanism, not a wrapper.
- Implementation quality (demo-ability in 1 day): 3/5 — ambitious; the compiler + canvas + runtime is a lot for one day, mitigated by 5 fixed blocks and a cached compile.
- Potential impact: 5/5 — unlocks every non-engineer domain expert to ship safe, protocol-faithful coaches; huge in health/coaching.
- **Total: 13/15**
