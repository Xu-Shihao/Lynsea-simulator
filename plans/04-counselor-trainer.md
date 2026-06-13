# Plan 04 — Praxis: the Standardized-Patient Trainer for Counselors

**One-liner:** A multi-agent "standardized patient" that role-plays a realistic, emotionally consistent client so a human counselor can practice a real session and get rubric-scored, evidence-cited feedback in minutes.
**Idea lane:** Counselor trainer — multi-agent standardized "patients" that role-play realistic clients so human counselors can practice and get scored feedback.

## 1. Problem & target user
Counseling skill is built through deliberate practice, but practice is the scarcest resource in the field. A second-year MSW or psychology trainee gets a handful of supervised "standardized patient" (SP) sessions per term: human actors are expensive (~$30–60/hr), scheduling is brittle, and supervisor feedback arrives days later as vague prose ("be more empathic"). New crisis-line and coaching staff face the same wall. The target user is **a counseling trainee or supervisor** who needs *reps* — a safe client to fail against at 11pm — plus **objective, immediate, teachable feedback** mapped to the skills their program actually grades (reflective listening, open questions, MI-consistent responses, risk screening). Why now: LLMs can finally hold a coherent emotional persona across a 10-minute turn-taking session, and Claude is good enough at *not* breaking character while a separate evaluator scores the transcript against a clinical rubric.

## 2. The product
Praxis is a session simulator with an instructor's grading sheet baked in.
Core loop (3–5 steps):
1. Trainee picks a **case card** (e.g. "Maya, 19, ambivalent about cutting down drinking; guarded, minimizes") and a **modality** to practice (Motivational Interviewing, CBT intake, suicide-risk screen).
2. Trainee runs a live **chat/voice session** with the Patient agent, which stays in character, has hidden internal state (trust, disclosed-vs-withheld facts, mood), and reacts to *how* it's asked — a closed shaming question makes Maya shut down; an open reflective one earns a disclosure.
3. On "End session," an **Evaluator agent** scores the transcript against the modality's rubric (e.g. MITI-style: reflection-to-question ratio, % open questions, MI-adherent vs MI-inconsistent), citing the *exact* trainee lines that earned or lost points.
4. A **Coach agent** turns the score into 3 concrete drills and replays one pivotal moment with a "better next line" suggestion.
5. Trainee sees a skills dashboard that trends across sessions.

## 3. Why it's novel (technical innovation)
Not a chatbot wrapper. Three non-obvious mechanisms:
- **Hidden-state patient, not a script.** The Patient holds private structured state (a disclosure ledger, trust meter, risk flags) the trainee must *earn* access to. Disclosures are gated by interviewer technique, so two trainees get genuinely different sessions — making the sim a measurement instrument, not a demo reel.
- **Separation of actor and judge.** A persona-locked Patient never sees the rubric (so it can't "teach to the test"), while an independent Evaluator scores against a versioned clinical rubric with line-level citations. This adversarial-by-design split is what makes the feedback trustworthy.
- **Rubric-as-code with grounded citations.** Scoring rubrics (MITI, Columbia-style risk screen) are encoded as machine-checkable criteria; every point is tied to a transcript span, so feedback is auditable rather than vibes.

## 4. Architecture & Claude Code / Multica role
- **Components:** (a) Patient agent (persona + hidden-state engine), (b) Evaluator agent (rubric scorer w/ citations), (c) Coach agent (drills + replay), (d) Orchestrator that owns the transcript/state, (e) thin web UI (chat + score panel), (f) `rubrics/*.yaml` and `cases/*.yaml` content.
- **Multi-agent orchestration (central):** Multica coordinates the three role-locked agents and guarantees the Patient and Evaluator never share context — the Patient stream is isolated from the grading stream. This clean role separation is the differentiator and the live-demo story.
- **Claude Code role (central):** Claude Code is the build engine *and* a runtime author — it generates new case cards and rubric YAML from a one-line instructor prompt, and scaffolds the agent prompts/state schema. We demo generating a brand-new patient case live.
- **Models/skills/tools:** Claude (Opus for Patient persona fidelity + Evaluator reasoning; Sonnet for Coach), structured-output tool calls for the score JSON, a tiny state store for the disclosure ledger.

## 5. Build-day scope (the ~1-day vertical slice)
- **MVP that works in the demo:** one modality (Motivational Interviewing), two case cards, text-based session, hidden-state gating on 3 disclosures, Evaluator producing an MI rubric score with line citations, Coach producing 3 drills. Single-user, local.
- **Out of scope for the day:** voice, auth/multi-user, the longitudinal dashboard (mock with 2 prior sessions), HIPAA/PHI handling, mobile.
- **Hour-by-hour:** 0–2h: rubric + case YAML schema, agent prompts, orchestrator skeleton. 2–5h: hidden-state Patient + disclosure gating; wire the live chat. 5–7h: Evaluator scoring w/ line-level citations + Coach drills; score panel UI. 7–8h: demo polish, seed the two cases, rehearse the 2-min script.

## 6. The 2-minute demo
1. (0:15) "Counselors learn by practicing on actors that cost $50/hr. Watch this." Open Praxis, pick case **Maya — ambivalent drinker, MI**.
2. (0:45) Live session: ask one *bad* closed/judging question — Maya gets guarded, withholds. Then ask an open, reflective one — Maya *discloses* the real reason she drinks. Visible behavior change is the wow beat.
3. (1:15) Hit **End session**. Evaluator score appears: reflection-to-question ratio, % open questions, MI-adherent count — each line of the transcript highlighted green/red with *why*.
4. (1:40) Coach shows the pivotal moment + a "better next line." Then: in Claude Code, type "make a new case: grieving widower, CBT intake" → a fresh playable case card appears. End.

## 7. Evaluation / proof it works
- **Persona integrity:** % of turns the Patient stays in character / honors the disclosure gate (target >95% over scripted probes).
- **Scoring validity:** correlation of the Evaluator's MI scores vs. a human supervisor's MITI coding on 10 recorded mock sessions (target Spearman ρ ≥ 0.7); inter-rater agreement on open-vs-closed question labels.
- **Before/after:** a trainee's open-question % and reflection ratio across 3 consecutive Praxis sessions — show the curve rising.
- **Baseline beaten:** vs. a plain ChatGPT "pretend to be a patient" — Praxis differentiates by trustworthy, citation-grounded scores and a non-coachable patient.

## 8. Risks & unknowns
- **Patient breaks character / gets coached into the rubric.** Mitigation: hard role separation via Multica (Patient never sees rubric), persona-lock system prompt, scripted regression probes before demo.
- **Evaluator scores feel arbitrary / wrong.** Mitigation: rubric-as-code with mandatory line citations; if a score lacks a citation, suppress it. Pre-validate on the 2 demo cases.
- **Clinical-safety optics.** This is a *training* tool, not therapy and not a real patient. Mitigation: explicit "synthetic patient, training only" framing, no real PHI, no crisis advice to end users — keep it firmly in the deliberate-practice lane.

## 9. Self-score (1–5 each, with one line of justification)
- Technical innovation: 4/5 — hidden-state, technique-gated patient + adversarially separated, citation-grounded evaluator is a genuine mechanism, not a wrapper.
- Implementation quality (demo-ability in 1 day): 4/5 — one modality, two cases, text-only is a tight, achievable vertical slice with a clear wow beat.
- Potential impact: 4/5 — attacks the real bottleneck (cheap, instant deliberate practice + objective feedback) for a large, underserved training pipeline; clinical-validation is the gate to scale.
- **Total: 12/15**
