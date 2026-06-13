# Research Dossier — Lynsea: a General Decision Outcome Simulator

> Owner: Deep Research Agent. Scope: prior art, the decision/causal-simulation science, evaluation
> methodology, credibility risks + mitigations, and an honest account of what is genuinely novel.
> Lynsea = a multi-agent LLM system that runs **paired, seeded counterfactual rollouts** of a
> decision and **shows the divergent trajectories** (scored against the user's own values) rather
> than handing down advice.

---

## 1. Prior art & competitive landscape

**Generative-agent worlds.** The closest technical ancestor is Stanford/Google's *Generative Agents:
Interactive Simulacra of Human Behavior* — the "Smallville" sandbox of 25 LLM-driven agents with
memory, reflection, and planning that produced emergent social behavior ([Park et al., 2023,
arXiv:2304.03442](https://arxiv.org/abs/2304.03442)). The same group later showed LLM "agents" can
replicate the survey responses of 1,000 real people with ~85% accuracy
([Park et al., 2024, arXiv:2411.10109](https://arxiv.org/abs/2411.10109)), establishing that
persona-conditioned agents can be *individually* faithful, not just collectively plausible.
Lynsea reuses this persistent-persona machinery but points it at a *decision* rather than open-ended
social life.

**Agent-based modeling (ABM).** Simulating outcomes via interacting actors is decades old —
Schelling's segregation model and Axelrod's cooperation tournaments are canonical
([Axelrod, 1997](https://press.princeton.edu/books/paperback/9780691015675/the-complexity-of-cooperation)),
with NetLogo as the standard platform ([Wilensky, 1999](https://ccl.northwestern.edu/netlogo/)).
LLM-driven ABM is now an active area, e.g. *S³* and economic simulations like
[*EconAgent* (Li et al., 2023, arXiv:2310.10436)](https://arxiv.org/abs/2310.10436). ABM gives
emergent second-order effects; what it historically lacks is a per-user, natural-language framing
and a values-weighted verdict — the layer Lynsea adds.

**Decision-support / "what-if" tools.** Classical decision analysis (influence diagrams, decision
trees, Monte-Carlo "what-if" in tools like [Analytica](https://lumina.com/) or Palisade @RISK)
quantifies uncertainty but requires the user to hand-build the model. Lynsea instead *constructs the
world model from plain language* and lets non-experts interrogate it.

**"Digital twins" of people.** The term originates in engineering/manufacturing
([Grieves & Vickers, 2017](https://doi.org/10.1007/978-3-319-38756-7_4)) and has spread to
healthcare ([Bruynseels et al., 2018, *Front. Genetics*](https://doi.org/10.3389/fgene.2018.00031)).
Most "personal digital twin" work models *physiology or behavior data*, not branching life
*decisions* under counterfactual interventions.

**Interactive Machine Labs** (named in the hackathon brief as the bar to beat) positions itself
around simulated/interactive environments for behavior; the brief's own note concedes exact details
"were not machine-readable from the event page" (`docs/HACKATHON_BRIEF.md`). The honest framing is
therefore *category* competition, not a feature-by-feature diff.

**The gap Lynsea fills.** None of the above combines all four of: (a) *natural-language framing* of
an arbitrary decision into stakeholder/force agents, (b) *paired seeded* counterfactual rollouts so
branches differ **only** by the decision, (c) a *values-weighted* outcome score calibrated by the
user, and (d) *live counterfactual interrogation*. Each ingredient exists; the integration is the
contribution.

## 2. The science

**Counterfactual / causal validity.** Pearl's "ladder of causation" separates association,
intervention, and counterfactuals; valid what-if reasoning lives on the top two rungs and requires a
*structural causal model*, not just correlation
([Pearl & Mackenzie, 2018, *The Book of Why*](https://bayes.cs.ucla.edu/WHY/)). An LLM rollout is
**not** a validated SCM, so Lynsea's branches should be read as *structured scenario generation*, not
calibrated probability — a point Section 4 returns to.

**Paired seeded rollouts as a controlled comparison.** Holding the random seed (and world state)
fixed across branches is the simulation-statistics technique of **common random numbers (CRN)**: when
comparing alternatives, sharing randomness reduces the variance of the *difference* estimator so that
observed divergence is attributable to the decision, not to noise
([Law, *Simulation Modeling and Analysis*](https://www.mheducation.com/highered/product/simulation-modeling-analysis-law/M9780073401324.html);
[Glasserman & Yao, 1992, *Management Science*](https://doi.org/10.1287/mnsc.38.6.884)). This is the
formal backbone of Lynsea's "branches differ only by the decision" claim and its strongest scientific
hook.

**Values-weighted scoring.** Folding a multi-dimensional trajectory into a single comparable score is
exactly **multi-attribute utility theory (MAUT)** — eliciting attribute weights and combining them,
typically additively ([Keeney & Raiffa, 1976, *Decisions with Multiple Objectives*](https://doi.org/10.1017/CBO9781139174084)).
Lynsea's user-calibrated weights operationalize "better *for you*" rather than "objectively better."

**Why "show the trajectory, don't advise."** Behavioral decision research shows people systematically
mispredict how they will *feel* about future outcomes — **impact bias** / affective forecasting errors
([Wilson & Gilbert, 2003](https://doi.org/10.1016/S0065-2601(03)01006-2);
[Gilbert et al., 1998, *JPSP*](https://doi.org/10.1037/0022-3514.75.3.617)) — and project current
preferences onto a different future self, **projection bias**
([Loewenstein, O'Donoghue & Rabin, 2003, *QJE*](https://doi.org/10.1162/003355303321675922)). A tool
that hands down a verdict inherits these biases silently; one that *renders the lived trajectory and
its divergence points* lets the user re-feel the tradeoff, which is the debiasing rationale for
Lynsea's "show, don't advise" stance.

## 3. Evaluation methodology

The core claim to test: *multi-agent paired counterfactuals beat a single-LLM pros/cons baseline.*
A defensible eval stacks four layers:

1. **Face-validity expert panels.** Blind domain experts rank Lynsea trajectories vs. baseline on
   plausibility/usefulness — the same human-judgment protocol Park et al. used to validate
   believability ([arXiv:2304.03442](https://arxiv.org/abs/2304.03442)).
2. **Calibration on resolvable items.** Where outcomes are later observable, score predictions with
   **Brier scores** and reliability diagrams ([Brier, 1950, *Mon. Weather Rev.*](https://doi.org/10.1175/1520-0493(1950)078%3C0001:VOFEIT%3E2.0.CO;2));
   well-calibrated systems are honest about uncertainty rather than merely fluent. LLMs are known to
   be *verbally* overconfident ([Xiong et al., 2023, arXiv:2306.13063](https://arxiv.org/abs/2306.13063)),
   so this layer is a real discriminator.
3. **Controlled-diff honesty checks.** Because of CRN seeding, flipping *only* the decision should move
   *only* causally-downstream events; an automated diff that flags branch differences with no plausible
   causal path catches narrative confabulation.
4. **Pre/post decision-confidence + decision quality.** Measure shift in subjective confidence and
   decision-process quality before vs. after, ideally A/B against the pros/cons baseline. (Caveat:
   higher confidence is *not* itself a good outcome — pair it with a quality rubric to avoid rewarding
   persuasive-but-wrong output.)

## 4. Credibility risks & literature-backed mitigations

- **Fake precision.** A fluent number ("Outcome Score 7.3/10") implies calibration the model does not
  have; LLMs are systematically overconfident ([Xiong et al., 2023](https://arxiv.org/abs/2306.13063)).
  *Mitigation:* present ranges/distributions across seeds, label scores as relative not absolute, and
  expose the calibration metrics from §3.2.
- **Narrative runaway / hallucinated causality.** Free-form agent dialogue drifts into compelling but
  unfounded storylines. *Mitigation:* the Referee + structured Outcome-event logging in
  `solution/README.md`, plus the controlled-diff check (§3.3), constrain branches to causally-defensible
  events.
- **Anthropomorphism & over-trust (automation bias).** Users over-rely on confident automation and
  under-verify ([Parasuraman & Riley, 1997, *Human Factors*](https://doi.org/10.1518/001872097778543886);
  [Mosier et al., 1998](https://doi.org/10.1207/s15327566ijce0801_3)); persuasive personas amplify this.
  *Mitigation:* the "show the trajectory, don't advise" stance, explicit "simulation, not prediction"
  framing, and surfacing divergence points so the user reasons rather than defers.
- **Scope/ethics.** Lynsea is decision-agnostic but must not pose as clinical or financial advice;
  high-stakes domains need explicit disclaimers and human-in-the-loop framing.

## 5. What is genuinely novel (honest assessment)

Not novel: LLM persona agents, emergent multi-agent worlds, MAUT scoring, and CRN/seeded comparison
each predate Lynsea by years to decades. **The novelty is the synthesis and the product stance:**
(1) automatically *framing an arbitrary natural-language decision* into a stakeholder/force world,
(2) enforcing **CRN-style seeded paired rollouts** in an *LLM* agent simulation so the branch
*difference* is the honest unit of analysis — a rigor not present in narrative generative-agent demos,
(3) a *user-calibrated* values-weighted verdict, and (4) live single-counterfactual re-runs. The
defensible claim is **"a decision-agnostic, causally-disciplined, values-personalized counterfactual
simulator,"** not "a new predictive science of life." Stated that way, it is both differentiated from
prior art and honest about its limits.

---

### Key sources

- Park et al. 2023, *Generative Agents* — [arXiv:2304.03442](https://arxiv.org/abs/2304.03442)
- Park et al. 2024, *Generative Agent Simulations of 1,000 People* — [arXiv:2411.10109](https://arxiv.org/abs/2411.10109)
- Pearl & Mackenzie 2018, *The Book of Why* — [bayes.cs.ucla.edu/WHY](https://bayes.cs.ucla.edu/WHY/)
- Glasserman & Yao 1992, common random numbers — [doi:10.1287/mnsc.38.6.884](https://doi.org/10.1287/mnsc.38.6.884)
- Keeney & Raiffa 1976, MAUT — [doi:10.1017/CBO9781139174084](https://doi.org/10.1017/CBO9781139174084)
- Wilson & Gilbert 2003, affective forecasting — [doi:10.1016/S0065-2601(03)01006-2](https://doi.org/10.1016/S0065-2601(03)01006-2)
- Loewenstein, O'Donoghue & Rabin 2003, projection bias — [doi:10.1162/003355303321675922](https://doi.org/10.1162/003355303321675922)
- Xiong et al. 2023, LLM confidence calibration — [arXiv:2306.13063](https://arxiv.org/abs/2306.13063)
- Brier 1950, verification score — [doi:10.1175/1520-0493(1950)078](https://doi.org/10.1175/1520-0493(1950)078%3C0001:VOFEIT%3E2.0.CO;2)
- Parasuraman & Riley 1997, use/misuse/abuse of automation — [doi:10.1518/001872097778543886](https://doi.org/10.1518/001872097778543886)
