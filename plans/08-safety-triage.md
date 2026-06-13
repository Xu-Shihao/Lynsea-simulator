# Plan 08 — Threshold

**One-liner:** The safe front door to mental-health support — a panel of agents that splits "listen" from "decide," so no single model can both chat *and* mishandle a crisis.
**Idea lane:** Safety Triage — a guardrailed, explicitly non-clinical triage & routing front-door: classify need, cite evidence, escalate safely, hand off to humans/resources.

## 1. Problem & target user
Today's AI mental-health bots have one dangerous flaw: **one** model both holds the conversation and decides what's safe. It fails *open* — a cheerful reply to a buried crisis signal, a hallucinated "clinical" reassurance, a missed handoff. Who gets hurt: a user in distress reaching a wellness app at 2am. Who can't ship these bots: the clinicians and ops team at a health org (Shanda Health / Lingxi) who need a front door they can *audit and defend*. Why now: real-world harms and active regulatory scrutiny of "therapy" chatbots mean a safe router beats a smarter chatbot.

## 2. The product
Threshold is a non-clinical intake front-door. It never diagnoses or treats — it *routes*. Core loop:
1. User writes in plain language.
2. A panel of specialized agents assesses need, grounded in validated screening instruments, and produces a **calibrated risk vector** (with confidence).
3. If signals or uncertainty cross a threshold, it **escalates** — to a human, a crisis line (e.g. 988), or the right vetted resource.
4. It generates a **warm-handoff packet** (SBAR-style + consent) so a human picks up with full context.
5. Every decision is written to an **append-only audit ledger** a clinician can review.

## 3. Why it's novel (technical innovation)
Safety is a property of the **agent topology**, not the prompt. **Separation of duties:** the agent that talks to the user can't decide the action; an *independent* Tripwire agent can unilaterally escalate (fail-*safe*, never fail-open). **Calibrated abstention:** "uncertain → human" is a first-class output, not a fallback. **Evidence-grounding:** classifications cite specific items of C-SSRS / PHQ-9 / GAD-7, not vibes. **Auditability:** the ledger records every vote, evidence, and confidence. A deployable safety architecture, not a thin wrapper — the guarantee emerges from how the agents are wired.

## 4. Architecture & Claude Code / Multica role
- **Pipeline (Multica multi-agent orchestration is the core):** `Listener → Evidence Screener → Tripwire (parallel, independent) → Escalation Arbiter → Auditor`. Each agent has a narrow JSON-schema contract; no agent owns two jobs.
- **Tiered models = the agentic build story:** Haiku as the always-on Tripwire on the hot path (cheap, low-latency), Sonnet as the Screener, **Opus** as the Arbiter for the high-stakes routing call.
- **Tools/skills:** structured output for the risk vector; a small retrieval corpus (3 instruments + a resource graph of 988/clinic/peer/self-help); an append-only ledger store.
- **Claude Code** builds and wires the agents; **Multica** runs them as an orchestrated, inspectable workflow.

## 5. Build-day scope (the ~1-day vertical slice)
- **MVP:** the 5-agent pipeline end-to-end, ~12-resource graph, the risk-vector + handoff-card UI, the audit ledger, and a 30–50 vignette benchmark vs. a single-LLM baseline.
- **Out of scope:** real PII/clinical data (synthetic only), accounts/auth, persistence, mobile, live hotline integration (display, don't dial).
- **Cut:** 0–2h agent contracts + corpus; 2–5h pipeline + ledger; 5–7h side-by-side UI + benchmark; 7–8h demo polish.

## 6. The 2-minute demo
1. (0:00–0:20) "One model that both chats and judges safety is the bug. Threshold splits the jobs." Architecture lights up.
2. (0:20–0:50) Paste a message with a *buried* signal ("gave away my guitar, finally sorted my paperwork, everyone's better off without the hassle") into a naive baseline bot → cheerful generic reply. "It missed it."
3. (0:50–1:30) Same message into Threshold: agents fire live — Screener cites a C-SSRS item, the independent Tripwire flags passive ideation, Arbiter escalates to "urgent → human + 988," a warm-handoff card + consent appear.
4. (1:30–1:50) Open the audit ledger: every vote, citation, and confidence — clinician-reviewable.
5. (1:50–2:00) Safety scoreboard: on the vignette set, **100% crisis recall** vs the baseline's misses. Wow + proof.

## 7. Evaluation / proof it works
A labeled mini-benchmark (~30–50 vignettes: true-crisis / ambiguous / benign). Metrics: **crisis sensitivity (target ~100%, fail-safe)**, false-escalation rate, and citation validity. A red-team agent generates masked-crisis cases to stress-test. Headline: sensitivity and citation-backed decisions vs. a single-LLM baseline.

## 8. Risks & unknowns
1. **Catastrophic miss (false reassurance).** → Fail-safe: Tripwire escalates unilaterally; bias toward over-escalation; never claims to be a therapist.
2. **Liability / scope creep.** → Explicitly non-clinical, no diagnosis/treatment, synthetic data, always route to humans/established lines, visible disclaimers.
3. **Latency from many agents.** → Tiered models (Haiku on hot path), parallel Tripwire, Opus only when signals present.

## 9. Self-score (1–5 each, with one line of justification)
- Technical innovation: 4/5 — safety-as-topology + independent tripwire + calibrated abstention + audit ledger is a non-obvious composition for this space.
- Implementation quality (demo-ability in 1 day): 4/5 — tight, contract-driven slice; ambitious breadth and latency are the only risks.
- Potential impact: 5/5 — an urgently needed, auditable, deployable safe front door with a clear regulatory tailwind.
- **Total: 13/15**
