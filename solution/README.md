# Solution — Lynsea: a General Decision Outcome Simulator

> The chosen build-day direction, formed by **combining Plan 01 (Lynsea life-sim sandbox)** and
> **Plan 03 (Decision Twin)** into one product for **general decision outcome simulation**.
> This folder is filled out by two Multica agents (see "Plan folder layout" below).

## One-liner

Point Lynsea at *any* decision — personal, business, product, or policy — and it builds a living
world model of the people and forces that decision touches, fast-forwards that world under each
option as a controlled counterfactual, and shows you the scored, side-by-side futures plus the
exact moments and human dynamics that made them diverge.

## How 01 + 03 combine (and why the combination is stronger than either)

| Ingredient | From | What it contributes |
|---|---|---|
| Persistent **stakeholder/force agents** populate the world; outcomes **emerge from agent interactions** | 01 | Realism + non-obvious second-order consequences |
| **Referee + Outcome agent** turn free-form dialogue into structured, scoreable events | 01 | Stops narrative runaway / unfalsifiable optimism |
| **Shared seeded `WorldState`** stepped over time; **paired counterfactual rollouts under a fixed seed** | 03 | Branches differ *only* by the decision → honest, causal contrast |
| **Values-weighted outcome score** the user calibrates + live **counterfactual interrogation** | 03 | "Better *for you*", and a memorable interactive demo beat |

- **01's weakness** (thin causal/scoring story) is fixed by **03's** seeded paired rollouts + values-weighted scorer.
- **03's weakness** (abstract "domains" instead of real actors) is fixed by **01's** persistent stakeholder agents.
- **Generalization:** the engine is decision-agnostic. The *same* loop handles "stay vs. move to Seattle",
  "ship feature A vs. B", or "raise prices 10%" — you just instantiate different stakeholder/force agents
  (partner & manager, or users & competitors & support load, or customers & churn & margin).

## Core loop (decision-agnostic)

1. **Frame** — extract the decision, its 2–3 options, and the entities it touches (stakeholders + forces) from plain language.
2. **Model** — a short structured interview builds the decider's `UserModel` (values weights, risk tolerance, constraints); each entity gets a persona/force agent.
3. **Simulate** — fork the seeded `WorldState` per option; step time forward; stakeholder + domain/force agents react and interact; a Referee caps drift and an Outcome agent logs structured events.
4. **Score & contrast** — fold each branch's trajectory into a values-weighted Life/Decision Outcome Score; surface the divergence points and the dynamics that drove them, side by side.
5. **Interrogate** — the user asks "what if X?" and that single counterfactual re-runs live in seconds.

## Why now / why Claude Code + Multica

Claude-class models can finally hold distinct, persistent personas with memory, and Multica's
multi-agent orchestration makes the per-entity / per-branch fan-out tractable to build in a day.
Claude Code both *builds* the orchestrator + schemas on build day and *is* the agents at runtime.
Judging fit: technical innovation (seeded multi-agent counterfactual world), implementation quality
(seed-locked demo), and impact (high-stakes decisions are universal and underserved).

## Plan folder layout (who fills what)

| File | Owner agent | Contents |
|---|---|---|
| `solution/README.md` | (this file — orchestrator) | The combined concept + seed for the two agents |
| `solution/research-dossier.md` | **Deep Research Agent** | Prior art & competitive landscape, the decision/causal-sim science, evaluation methodology, credibility risks + literature-backed mitigations, what is genuinely novel |
| `solution/build-plan.md` | **Hackathon Agent** | Unified product spec, merged architecture + data schemas (`UserModel`/`WorldState`), build-day MVP & hour-by-hour cut, 2-min demo, eval plan, risks, self-score |
