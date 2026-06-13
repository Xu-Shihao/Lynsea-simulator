"""Structural interfaces (Protocols) the Wave-2 specialists implement.

BE-Core lands these *first* with stub implementations (see ``orchestrator.py``)
so the full SSE stream runs end-to-end on day one. Each specialist then writes
the real implementation in their **own** file, keeping the exact signature:

| function / type          | owner file       | owner role |
|--------------------------|------------------|------------|
| ``SeededRNG``            | ``rng.py``       | BE-Engine  |
| ``build_world``          | ``personas.py``  | BE-Twin    |
| ``generate_events``      | ``events.py``    | BE-Engine  |
| ``run_simulation``       | ``simulation.py``| BE-Sim     |
| ``score_branch``         | ``scoring.py``   | BE-Score   |
| ``detect_forks``         | ``scoring.py``   | BE-Score   |
| ``credibility``          | ``scoring.py``   | BE-Score   |
| ``recommend``            | ``scoring.py``   | BE-Score   |

These are ``typing.Protocol`` (and one ``runtime_checkable``) definitions, so a
specialist module satisfies the contract just by matching the shape — no base
class import or inheritance required.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.schemas import (
    BranchScore,
    Credibility,
    ForkPoint,
    Metric,
    Recommendation,
    SimResult,
    SimulateRequest,
    TimelineEvent,
    ValueWeights,
    World,
)


@runtime_checkable
class SeededRNG(Protocol):
    """Deterministic RNG (owner: ``rng.py`` / BE-Engine).

    Contract (``ALG-20/21`` + ``NFR-01`` hinge on this):

    * Constructed from a single integer ``seed``.
    * The **shared** (non-decision) random-event stream is identical across
      branches A and B for the same seed — only the decision variable differs.
    * ``shared_event_hash()`` returns a stable hash of that shared stream so QA
      can assert reproducibility / branch parity.
    """

    seed: int

    def random(self) -> float:
        """Next float in [0, 1) from the shared stream."""
        ...

    def randint(self, a: int, b: int) -> int:
        """Next int in [a, b] (inclusive) from the shared stream."""
        ...

    def choice(self, seq: list):  # type: ignore[type-arg]
        """Pick one element of ``seq`` from the shared stream."""
        ...

    def branch_rng(self, branch: str) -> "SeededRNG":
        """A child RNG deterministically derived from seed + branch.

        Used for decision-variable-dependent draws so that shared events stay
        identical while branch-specific events may differ.
        """
        ...

    def shared_event_hash(self) -> str:
        """Stable hash of the shared (non-decision) random-event stream."""
        ...


class BuildWorld(Protocol):
    """`build_world(req, rng) -> World` (owner: ``personas.py`` / BE-Twin)."""

    def __call__(self, req: SimulateRequest, rng: SeededRNG) -> World: ...


class GenerateEvents(Protocol):
    """`generate_events(world, branch, rng) -> [TimelineEvent]`.

    Owner: ``events.py`` / BE-Engine. Must emit skeleton (high-probability)
    events before perturbation (low-probability) events (`ALG-30`).
    """

    def __call__(
        self, world: World, branch: str, rng: SeededRNG
    ) -> list[TimelineEvent]: ...


class RunSimulation(Protocol):
    """`run_simulation(world, branch, events, rng) -> SimResult`.

    Owner: ``simulation.py`` / BE-Sim. Produces the 5-dimension metric curves;
    every metric references >= 1 evidence event (`ALG-40`).
    """

    def __call__(
        self,
        world: World,
        branch: str,
        events: list[TimelineEvent],
        rng: SeededRNG,
    ) -> SimResult: ...


class ScoreBranch(Protocol):
    """`score_branch(sim, values) -> BranchScore` (owner: ``scoring.py``)."""

    def __call__(self, sim: SimResult, values: ValueWeights) -> BranchScore: ...


class DetectForks(Protocol):
    """`detect_forks(a, b) -> [ForkPoint]` (owner: ``scoring.py``)."""

    def __call__(self, a: SimResult, b: SimResult) -> list[ForkPoint]: ...


class CredibilityFn(Protocol):
    """`credibility(world, sims) -> Credibility` (owner: ``scoring.py``)."""

    def __call__(self, world: World, sims: list[SimResult]) -> Credibility: ...


class RecommendFn(Protocol):
    """`recommend(world, scores, forks, cred) -> Recommendation`.

    Owner: ``scoring.py`` / BE-Score. Output copy MUST be probabilistic
    (`SYS-15`) and carry a guardrail for high-risk results (`SYS-16`).
    """

    def __call__(
        self,
        world: World,
        scores: list[BranchScore],
        forks: list[ForkPoint],
        cred: Credibility,
    ) -> Recommendation: ...


__all__ = [
    "SeededRNG",
    "BuildWorld",
    "GenerateEvents",
    "RunSimulation",
    "ScoreBranch",
    "DetectForks",
    "CredibilityFn",
    "RecommendFn",
    "Metric",
]
