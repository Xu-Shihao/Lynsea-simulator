# Plan 02 — Coaching Copilot

**One-liner:** A coaching copilot that runs *named, citable* CBT protocols, assigns and tracks weekly homework, and adapts the next session based on what the client actually did — like a therapist who never forgets and always shows their work.

**Idea lane:** Evidence-based coaching copilot that runs CBT/behavioral protocols, cites the intervention it is using, assigns and tracks homework, and adapts week to week.

## 1. Problem & target user

**Maya, 29, knowledge worker with mild-to-moderate anxiety.** Therapy is $150–250/session with 6-week waitlists; self-help apps (Woebot, Wysa, Headspace) feel generic and have no memory of last week. Generic LLM chatbots are worse: they sound supportive but improvise — no protocol fidelity, no homework follow-through, no way to know *why* they said what they said. Maya doesn't need empathy theater; she needs a structured, accountable program between (or instead of) sessions. **Why now:** LLMs are finally good enough to follow a multi-week clinical protocol with fidelity, and regulators/clinicians demand *explainability* — exactly what an agent that cites its intervention can provide.

## 2. The product

A web app that runs a multi-week CBT program as a structured **session → homework → review** loop:

1. **Intake** — client states a goal ("stop catastrophizing about work"). Copilot maps it to a protocol track (e.g. Cognitive Restructuring + Behavioral Activation).
2. **Session** — copilot runs the week's protocol step, and *every therapeutic move shows a citation chip* ("Socratic questioning — Beck, 1979") the client can expand.
3. **Homework** — it assigns a concrete, checkable task (e.g. a 3-column thought record) and schedules it.
4. **Review** — next session opens by reading the *actual* homework data, scoring adherence, and **adapting**: skip ahead, repeat, or branch to a different technique.

## 3. Why it's novel (technical innovation)

Not a chat wrapper. Three hard mechanisms:

- **Protocol fidelity engine.** CBT protocols are encoded as explicit state machines (steps, entry/exit criteria, allowed techniques). A planner agent picks the *next legal move*; the dialogue agent can only speak within that move. This prevents the "drift into generic reassurance" failure mode of raw LLMs.
- **Citation-grounded generation.** Each technique is keyed to a small evidence library; the agent must select an intervention *and* return its citation before it speaks. A critic agent rejects any utterance whose claimed technique doesn't match its actual content (fidelity check).
- **Closed-loop weekly adaptation.** Homework completion data feeds a structured adherence score that *rewrites* the protocol path for next week. The plan is data, not vibes — it's inspectable and replayable.

## 4. Architecture & Claude Code / Multica role

- **Components:** React chat UI with citation chips + homework tracker → orchestrator → protocol state store (JSON) → evidence library (technique→citation) → SQLite for session/homework logs.
- **Multi-agent orchestration (Multica):** four cooperating agents —
  1. **Planner** (selects next protocol step from state + adherence),
  2. **Therapist** (speaks the step in-character, attaches citation),
  3. **Fidelity Critic** (verifies technique↔utterance match; can veto/regenerate),
  4. **Homework Tracker** (parses completed homework, computes adherence, writes back to state).
- **Claude Code is central** as the build engine: it scaffolds the protocol state machines from clinical manuals, generates the agent prompt/tool contracts, and writes the fidelity-critic test suite. The Critic↔Therapist loop is the agentic differentiator judges reward.
- **Models/skills:** Claude (Opus for Planner/Critic reasoning, Sonnet for Therapist turns); tools: `get_protocol_state`, `log_homework`, `score_adherence`, `cite_technique`.

## 5. Build-day scope (the ~1-day vertical slice)

- **MVP that works:** ONE protocol track end-to-end (Cognitive Restructuring) across **2 simulated weeks** — Session 1 → thought-record homework → Session 2 that reads the homework and adapts. Citation chips live. Fidelity critic active on every turn.
- **Out of scope today:** account/auth, multiple protocol tracks, mobile, payments, real clinical validation, crisis-detection routing (stub a safety banner only).
- **Hour cut:** 0–2h protocol state machine + evidence library; 2–5h four-agent loop in Multica + tools; 5–7h React UI with citation chips + homework tracker; 7–8h seed a demo client, polish the "week 2 adapts" beat.

## 6. The 2-minute demo

1. **(0:20)** Maya types her goal; copilot names the protocol on screen: "Cognitive Restructuring (Beck)".
2. **(0:50)** It runs a Socratic exchange — judge **clicks a citation chip**, sees the technique + source. The "wow": *the AI shows its clinical reasoning, not just an answer.*
3. **(1:10)** It assigns a thought-record homework; we fill it in (one entry honest, one skipped).
4. **(1:40)** Click "Start Week 2." Copilot **reads the homework**, says "You completed 1 of 2 records — let's slow down and repeat the skill," and visibly branches the protocol path. The "wow": *it adapted to real behavior.*
5. **(2:00)** Flash the Fidelity Critic log: one therapist turn was vetoed & regenerated for protocol mismatch.

## 7. Evaluation / proof it works

- **Fidelity metric:** % of agent turns whose technique label matches an independent classifier / critic verdict. Target ≥ 90% vs. a raw-LLM baseline (expected ~50–60% drift). Show a side-by-side: same client prompt, baseline GPT-chat vs. ours, scored.
- **Adherence-driven adaptation:** demonstrate two different homework inputs deterministically produce two different Week-2 paths (replayable from logs).

## 8. Risks & unknowns

- **Fidelity critic too strict/loops infinitely.** Mitigation: cap regeneration at 2 retries, fall back to the safest in-protocol template.
- **Protocol state machine takes longer than 2h.** Mitigation: pre-author the single Cognitive Restructuring track as JSON before build day (assets, not code).
- **Safety/clinical liability in a live demo.** Mitigation: explicit "not a medical device / educational demo" banner, hard-coded crisis stub, no real PII.

## 9. Self-score (1–5 each, with one line of justification)

- Technical innovation: 4/5 — protocol-state-machine + fidelity-critic loop is a genuinely novel mechanism, not a wrapper, though CBT chatbots exist.
- Implementation quality (demo-ability in 1 day): 4/5 — single track + 2 weeks is tight but achievable; citation chips and the adapt beat are concrete and visual.
- Potential impact: 4/5 — explainable, accountable coaching addresses a real access gap and the explainability that clinicians/regulators demand; impact capped by it being adjunct, not a replacement.
- **Total: 12/15**
