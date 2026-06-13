# Lynsea-simulator

Hackathon idea-exploration repo for the **Claude Code Build Day** (Cerebral Valley × Anthropic).

This repo holds **10 candidate product plans** — distinct directions seeded from an
evidence-based life-coaching + simulation/prediction concept — generated in parallel by
[Multica](https://multica.ai) agents (the *Hackathon Agent*, with the `hackathon-ai-devkit` skills).

## Layout

- `docs/HACKATHON_BRIEF.md` — shared grounding: the build-day requirements, judging criteria, constraints, and the seed concept. **Every plan must align to this.**
- `docs/PLAN_TEMPLATE.md` — the required structure for each plan doc.
- `plans/` — one markdown doc per candidate idea (`plans/NN-slug.md`), each landed via its own PR.
- `plans/README.md` — index + status of the 10 candidate ideas.

## Workflow

1. Each idea = one Multica issue → one agent run → one branch `plan/NN-slug` → one PR into `main`.
2. After all 10 land, score them with `hackathon-idea-scoring` and pick the build-day project.
