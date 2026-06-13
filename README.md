# Lynsea — a General Decision Outcome Simulator

Project repo for the **Claude Code Build Day** (Cerebral Valley × Anthropic).

**Chosen build-day direction →** given *any* decision (personal, business, product, policy), Lynsea
builds a living multi-agent world of the people and forces it touches, fast-forwards that world under
each option as a **seed-locked counterfactual**, and shows the scored, side-by-side futures plus the
exact moments and human dynamics that made them diverge. Full write-up in **[`solution/`](solution/)**.

It was selected by exploring **10 candidate directions** up front and combining the two strongest —
**Plan 01 (Lynsea life-sim sandbox)** + **Plan 03 (Decision Twin)** — into one decision-agnostic engine.

## Repository map

| Path | What's there |
|------|--------------|
| **[`solution/`](solution/)** | **The chosen direction** (Plan 01 ⊕ 03) |
| &nbsp;&nbsp;├ [`README.md`](solution/README.md) | The combined concept and how 01 + 03 merge |
| &nbsp;&nbsp;├ [`build-plan.md`](solution/build-plan.md) | Product spec, merged architecture + schemas, build-day MVP, 2-min demo, eval, self-score |
| &nbsp;&nbsp;└ [`research-dossier.md`](solution/research-dossier.md) | Prior art, the decision-/causal-simulation science, evaluation methodology, novelty (cited) |
| **[`plans/`](plans/)** | The 10 candidate directions explored first — see the [index](plans/README.md) |
| **[`docs/`](docs/)** | Shared grounding |
| &nbsp;&nbsp;├ [`HACKATHON_BRIEF.md`](docs/HACKATHON_BRIEF.md) | Build-day requirements, judging criteria, the seed concept |
| &nbsp;&nbsp;└ [`PLAN_TEMPLATE.md`](docs/PLAN_TEMPLATE.md) | The structure every candidate plan follows |

## How this repo was built

The 10 candidate plans in [`plans/`](plans/) were generated **in parallel by [Multica](https://multica.ai)
agents** — one issue → one agent run → one branch → one PR each (the *Hackathon Agent*, carrying the
`hackathon-ai-devkit` skills). Plans **01** and **03** were then combined into the chosen
[`solution/`](solution/), with the **Hackathon Agent** authoring the build plan and the **Deep Research
Agent** authoring the research dossier. Everything here is the consolidated, merged result on `main`.

## Where to start

1. Read **[`solution/README.md`](solution/README.md)** for the concept.
2. Read **[`solution/build-plan.md`](solution/build-plan.md)** for what to build on the day.
3. Skim **[`plans/`](plans/README.md)** to see the alternatives that were considered.
