export const meta = {
  name: 'lynsea-p0-polish',
  description: 'Audit Lynsea against P0 acceptance criteria, fix gaps in disjoint lanes, then verify',
  phases: [
    { title: 'Audit', detail: 'parallel read-only auditors score P0 criteria against the code' },
    { title: 'Fix', detail: 'disjoint backend / frontend / docs lanes apply gap fixes' },
    { title: 'Verify', detail: 'pytest + next build confirm green' },
  ],
}

const ROOT = '/Users/shihaoxu/Desktop/claude_hackathon/Lynsea-simulator-cc'

const FINDINGS_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['criterion', 'area', 'status', 'evidence', 'fix'],
        properties: {
          criterion: { type: 'string', description: 'acceptance id, e.g. FE-21 / ALG-20 / BE-04' },
          area: { type: 'string', enum: ['backend', 'frontend', 'docs'] },
          status: { type: 'string', enum: ['pass', 'gap', 'fail'] },
          evidence: { type: 'string', description: 'file:line or concrete observation' },
          fix: { type: 'string', description: 'concrete change needed; empty if pass' },
        },
      },
    },
  },
}

const FIX_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['summary', 'files_changed', 'verified'],
  properties: {
    summary: { type: 'string' },
    files_changed: { type: 'array', items: { type: 'string' } },
    verified: { type: 'string', description: 'how it was verified (test/build output)' },
  },
}

const common = `Repo: ${ROOT}. The product is "Lynsea", a fixed-seed paired-counterfactual decision simulator.
Contract + plan: read ${ROOT}/BUILD_PLAN.md (English, authoritative) and the P0 checklist in ${ROOT}/plans/Lynsea-验收标准.md section 10 (Chinese; the IDs like SYS-12/ALG-20/FE-21/BE-04/NFR-01 are what matter).
Backend = FastAPI in backend/app (engine/ api/ main.py, contracts.py, config.py). Frontend = Next.js in frontend/ (app/, components/, lib/).
The live-path hang has ALREADY been fixed (thread-local Anthropic clients + 45s timeout in config.py) — do NOT re-investigate that.`

// ---- KNOWN ISSUES injected by the controller (folded in at launch) ----
const KNOWN = args && args.known ? `\n\nController-observed issues to weigh:\n${args.known}` : ''

phase('Audit')

const AUDIT_DIMENSIONS = [
  {
    key: 'backend-alg',
    prompt: `${common}${KNOWN}\n\nAUDIT (read-only, do NOT edit) the BACKEND against these P0 criteria and return findings:
ALG-01 minimal input starts twin; ALG-02 Big5 inferred not asked; ALG-04 cold-start personas flagged is_default_inferred; ALG-20 shared exogenous events byte-identical across branches; ALG-21 pre-fork state identical; ALG-30 skeleton+perturbation two layers labeled; ALG-31 implausible-event rate guard; ALG-32 resample<=3 then downgrade+flag; ALG-40 every MetricPoint has >=1 supporting_event_id; NFR-01 same seed reproducible; BE-03 branches concurrent; BE-04 skeleton streamed before perturbation/scoring; BE-11 only .env provider; BE-12 retry + graceful degradation.
Read backend/app/engine/*.py, api/*.py, contracts.py, config.py. For each criterion give status pass/gap/fail with file:line evidence and a concrete fix if not pass. Be strict and specific.`,
  },
  {
    key: 'frontend-fe',
    prompt: `${common}${KNOWN}\n\nAUDIT (read-only, do NOT edit) the FRONTEND against these P0 criteria and return findings:
SYS-12 result shows side-by-side timelines + metric curves + result score + branch points; FE-01/02 single decision input + clarification summary; FE-10 small multiples same time axis aligned, shared exogenous marked in BOTH columns; FE-11 five 0-100 metric curves comparable; FE-12 branch points highlighted with cause text + divergence band; FE-13 click event -> evidence; FE-21 streaming skeleton-first via SSE, no full-screen hang; FE-22 credibility card visible; FE-23 uncertainty markers for is_default_inferred; FE-24/25 high-risk "simulation not prophecy" banner + probabilistic copy.
Read frontend/app/*, frontend/components/*, frontend/lib/* (types.ts, api.ts, useSimStream.ts). Verify the SSE event names/types match the backend contract in BUILD_PLAN.md exactly (status/persona/timeline_event/metric/branch_point/credibility/recommendation/done/error). For each criterion give status with file:line evidence and a concrete fix if not pass.`,
  },
  {
    key: 'safety',
    prompt: `${common}${KNOWN}\n\nAUDIT (read-only, do NOT edit) SAFETY/copy across BOTH backend and frontend:
SYS-15 probabilistic phrasing, zero "will happen/definitely" in result-facing copy; SYS-16 high-risk results show "this is a simulation, not a prophecy" + a "how to change this outcome" affordance; FE-24/25 same in UI; NFR-06 the four guardrails present (probabilistic + high-risk notice + editable premises + explainability).
Grep backend recommendation/credibility text generation (engine/credibility.py) and frontend SafetyBanner/RecommendationCard. Flag any deterministic/absolutist language. Mark area backend or frontend per where the fix belongs. Give file:line evidence + concrete fix.`,
  },
  {
    key: 'latency-stream',
    prompt: `${common}${KNOWN}\n\nAUDIT (read-only, do NOT edit) LATENCY + STREAMING architecture:
BE-04 first skeleton event must stream early (target <=20s), NOT be withheld until both branches fully finish; NFR-02 quick full result <=90s; SYS-02 progress + cancel. Read backend/app/engine/orchestrator.py and api/routes.py: does it emit each branch's skeleton events AS that branch returns, or does it batch all timeline_events only after asyncio.gather of both branches completes? If batched, that is a gap for BE-04/FE-21. Also assess retry amplification in config.complete (retries) x SDK max_retries x timeout — worst-case latency under API throttle. Give concrete fixes (area backend). Also note any frontend-side streaming gap (area frontend).`,
  },
  {
    key: 'docs-demo',
    prompt: `${common}${KNOWN}\n\nAUDIT (read-only, do NOT edit) DOCS/DEMO readiness (BUILD_PLAN section 8 lists "README (English) + demo script" as a P0 deliverable):
Is there a top-level README.md explaining what Lynsea is + how to run backend & frontend + a demo walkthrough? Is there a demo script hitting the P0 E2E scenarios (E2E-1 job, E2E-2 high-risk relationship, E2E-5 reproducibility, E2E-6 cold-start)? Check repo root. Mark everything missing as area docs with a concrete fix. (There is currently no top-level README — it was removed in the restructure.)`,
  },
]

const auditResults = await parallel(
  AUDIT_DIMENSIONS.map((d) => () =>
    agent(d.prompt, { label: `audit:${d.key}`, phase: 'Audit', schema: FINDINGS_SCHEMA, agentType: 'Explore' })
  )
)

const allFindings = auditResults.filter(Boolean).flatMap((r) => r.findings || [])
const gaps = allFindings.filter((f) => f.status !== 'pass')
log(`Audit complete: ${allFindings.length} criteria scored, ${gaps.length} gaps/fails found.`)

function lane(area) {
  const items = gaps.filter((f) => f.area === area)
  return items
    .map((f, i) => `${i + 1}. [${f.criterion}] (${f.status}) ${f.evidence}\n   FIX: ${f.fix}`)
    .join('\n')
}

const backendGaps = lane('backend')
const frontendGaps = lane('frontend')
const docsGaps = lane('docs')

phase('Fix')

const fixThunks = []

if (backendGaps.trim()) {
  fixThunks.push(() =>
    agent(
      `${common}\n\nYou are the BACKEND fix agent. You may ONLY edit files under backend/. Do NOT touch frontend/, plans/, .env, BUILD_PLAN.md, or run git.\nApply fixes for these confirmed P0 gaps (skip any that are already actually fine — verify first):\n${backendGaps}\n\nConstraints: keep the frozen API/data contract (contracts.py) intact; the stub-path tests must stay green; never log the API key; prefer graceful degradation. For BE-04/FE-21 streaming, emit each branch's skeleton events as soon as that branch returns (before scoring), rather than batching all timeline_events after gather of both branches.\nAfter editing, run \`backend/.venv/bin/pytest backend/tests -q\` and ensure all pass. Return the fix summary.`,
      { label: 'fix:backend', phase: 'Fix', schema: FIX_SCHEMA }
    )
  )
}
if (frontendGaps.trim()) {
  fixThunks.push(() =>
    agent(
      `${common}\n\nYou are the FRONTEND fix agent. You may ONLY edit files under frontend/. Do NOT touch backend/, plans/, .env, BUILD_PLAN.md, or run git.\nApply fixes for these confirmed P0 gaps (verify each is real first):\n${frontendGaps}\n\nConstraints: keep types matching the backend contract; the offline "Load demo" path must keep working; \`cd frontend && npm run build\` must succeed.\nAfter editing, run \`cd ${ROOT}/frontend && npm run build\` and ensure it compiles. Return the fix summary.`,
      { label: 'fix:frontend', phase: 'Fix', schema: FIX_SCHEMA }
    )
  )
}
// Docs lane always runs if there are docs gaps OR no README at root.
if (docsGaps.trim()) {
  fixThunks.push(() =>
    agent(
      `${common}\n\nYou are the DOCS agent. You may create/edit only top-level docs (README.md) and a demo script (e.g. scripts/demo.sh or DEMO.md). Do NOT edit backend/ or frontend/ source, plans/, .env, BUILD_PLAN.md, or run git.\nAddress these docs gaps:\n${docsGaps}\n\nDeliver: a polished top-level README.md (what Lynsea is, the differentiator, architecture, how to run backend+frontend, the P0 acceptance summary) and a runnable demo script that exercises the P0 E2E scenarios (E2E-1 job decision quick, E2E-2 high-risk relationship, E2E-5 same-seed reproducibility check, E2E-6 cold-start). English only. Return the summary.`,
      { label: 'fix:docs', phase: 'Fix', schema: FIX_SCHEMA }
    )
  )
}

const fixResults = fixThunks.length ? await parallel(fixThunks) : []

phase('Verify')

const verify = await parallel([
  () =>
    agent(
      `Run \`cd ${ROOT}/backend && .venv/bin/pytest tests -q\` and report the exact pass/fail counts and any failure tracebacks. Read-only except running tests. Return the summary verbatim.`,
      { label: 'verify:pytest', phase: 'Verify' }
    ),
  () =>
    agent(
      `Run \`cd ${ROOT}/frontend && npm run build\` and report success/failure plus any type/build errors verbatim. Read-only except running the build. Return the summary.`,
      { label: 'verify:build', phase: 'Verify' }
    ),
])

return {
  criteria_scored: allFindings.length,
  gaps_found: gaps.length,
  gaps_by_area: {
    backend: gaps.filter((f) => f.area === 'backend').length,
    frontend: gaps.filter((f) => f.area === 'frontend').length,
    docs: gaps.filter((f) => f.area === 'docs').length,
  },
  fixes: fixResults.filter(Boolean),
  verify,
  remaining_gaps_detail: gaps,
}
