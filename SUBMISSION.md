Team Name
Lingxi Frontier Lab


Team Members
Shihao Xu, Gary_Xu


Project Description
Lynsea — a fixed-seed paired-counterfactual decision simulator. One hard decision, two side-by-side parallel futures.

The problem: When people face a high-stakes life decision — take the higher-paying but high-stress job, end a relationship, move abroad — they have no fair way to compare the two futures. Existing "what-if" tools just generate two unrelated stories, so any difference is noise, not signal.

What Lynsea does: You describe a decision, its two options, and the people it affects. Lynsea (1) builds digital-twin personas of you and your social circle from minimal input (Big Five traits inferred, never hand-entered); (2) runs a fixed-seed paired counterfactual — both branches share a byte-identical seeded backbone of exogenous life events (rent rises, a friend moves abroad, flu season), drawn with no LLM, so the only thing that differs between the two futures is the decision itself; and (3) streams back, in real time, two aligned month-by-month timelines, decision-specific metric curves (0–100), the branch points where the futures diverge with a cause chain, and a credibility card with a value-weighted recommendation.

The differentiator is that the two branches are a controlled experiment, not two narratives — same seed, same world, personas forked from identical pre-decision state, and everything phrased as probabilities, never prophecy (high-risk outcomes surface a "this is a simulation, not a prophecy" banner plus a "how to change this outcome" hint). It degrades gracefully to deterministic stubs when the LLM is slow or unavailable, so it always runs end-to-end.


Public Project Demo Video
[TODO: record a 1-minute demo and paste the YouTube link]


How was Opus 4.8 used in your project?
Opus 4.8 was the primary engineering agent that designed and built the entire system through Claude Code. Rather than autocomplete, it ran the whole loop: brainstorming the product concept, authoring the design spec and a TDD implementation plan, then implementing the FastAPI simulation engine (seeded paired-counterfactual backbone, persona generation, per-branch event simulation with a plausibility guard, multi-dimension scoring, branch-point detection, credibility card) and the Next.js + Recharts streaming frontend — verified with pytest (14/14 green on the no-key stub path) and an end-to-end demo.sh covering all four P0 acceptance scenarios.

I directed Opus 4.8 as a multi-agent orchestrator: a single BUILD_PLAN.md integration contract let backend and frontend agents build in disjoint lanes, and a custom Opus-driven audit-fix-verify workflow (.claude/workflows/lynsea-p0-polish.js) spawned parallel read-only auditors that scored the code against the P0 acceptance IDs (ALG-20, BE-04, FE-21, NFR-01...) and returned structured findings, then fixed gaps and re-ran the test/build gate. Opus 4.8 also drove the second iteration (dynamic per-decision dimensions, an in-process EverOS-inspired agent-memory layer, and LLM-generated iterative clarification).

Runtime note: the deployed simulation calls go through a single model-agnostic config.complete() abstraction that defaults to Haiku 4.5 for low latency under API throttling, and can be pointed at Opus 4.8 by changing one env var (DEFAULT_MODEL).


Public GitHub Repository
https://github.com/Xu-Shihao/Lynsea-simulator


Live Demo URL
[TODO: not yet deployed — deploy frontend (e.g. Vercel) + backend (e.g. Render/Fly/Railway) and paste the URL, or run locally via ./demo.sh for judges]


Link to Session Log (Optional)
[TODO: run /export session-log.md in Claude Code, commit the file, then link it, e.g. https://github.com/Xu-Shihao/Lynsea-simulator/blob/main/session-log.md]


How did you orchestrate Claude's work?
I treated Opus 4.8 as a multi-agent build system driven by a written contract and a rubric, not a single chat:

Single-source-of-truth contract — BUILD_PLAN.md froze the API, data models, and the fixed-seed paired-counterfactual algorithm so independent backend and frontend agents could build in disjoint directories without colliding.

Rubric-driven verification — plans/Lynsea-验收标准.md is the acceptance-criteria rubric (P0 rows, IDs like SYS-12 / ALG-20 / BE-04 / NFR-01). Agents were scored against these IDs, and demo.sh runs the four P0 end-to-end scenarios as an automated pass/fail gate.

Superpowers skill pipeline — brainstorming, design spec, writing-plans (TDD), test-driven-development, plus a deep-research workflow that produced the research dossier in plans/Deep-research.md.

Custom multi-agent workflow script — .claude/workflows/lynsea-p0-polish.js: a deterministic audit-fix-verify fan-out. Parallel read-only Explore auditors return schema-validated findings against each P0 criterion; gaps are fixed in disjoint backend/frontend/docs lanes; a final parallel step runs pytest + next build as the verifier gate.

Custom scaffolding — frontend/AGENTS.md / CLAUDE.md warn the agent that this Next.js has breaking changes and to read local docs first; Stitch (MCP) generated the design language the frontend was reskinned to.

Links (all in the repo):
Brief / contract: BUILD_PLAN.md
Rubric: plans/Lynsea-验收标准.md
Workflow script: .claude/workflows/lynsea-p0-polish.js
Design spec + TDD plan: docs/superpowers/specs/2026-06-13-lynsea-prediction-enrichment-design.md, docs/superpowers/plans/2026-06-13-lynsea-prediction-enrichment.md
E2E verifier: demo.sh


Do you have any feedback on Opus 4.8?
Opus 4.8 was strong at holding a written contract across a long multi-agent build — disjoint backend/frontend lanes integrated cleanly against BUILD_PLAN.md with very few interface mismatches, and it was reliable at the "audit against a rubric and return structured findings" pattern. It also self-diagnosed a real concurrency bug (a shared Anthropic client racing under asyncio.gather) and fixed it with thread-local clients + bounded timeouts. Main friction was latency/throttling on live API calls during simulation, which pushed us to default the runtime to Haiku 4.5 and lean on the deterministic stub path for tests/demos.
