"""Deterministic, branch-parity RNG for Lynsea (owner: BE-Engine).

This module implements :class:`SeededRNG`, the real replacement for the Wave-1
``StubSeededRNG`` in ``orchestrator.py``. It satisfies the ``SeededRNG`` Protocol
in ``app.interfaces`` and the acceptance gates that hinge on it:

* **ALG-20 / ALG-21** — the paired counterfactual branches A and B must share the
  *same* exogenous (non-decision) random events; only the decision variable may
  change the outcome. We model this with two clearly separated stream families:

  - a **shared** stream, derived from the *seed alone* (``shared_rng()``), used by
    ``events.py`` for the perturbation (exogenous) layer. Because it depends only
    on the seed — never on the branch — branch A and branch B reconstruct a
    byte-identical sequence, even when they run concurrently (the orchestrator
    runs the two branches in parallel threads). ``shared_rng()`` always returns a
    **fresh** generator, so there is no shared mutable state to race on.
  - per-branch streams (``branch_rng(branch)``), derived from ``seed + branch``,
    used for decision-conditioned draws (e.g. the skeleton layer). These differ
    between A and B by construction.

* **NFR-01** — fully deterministic and reproducible: the same seed always yields
  the same streams and the same :meth:`shared_event_hash`, so a repeated run
  returns an identical hash via ``GET /api/run/{id}/seed-check``.

``shared_event_hash()`` is a stable fingerprint of the **shared** stream. The
orchestrator records it before any events are generated, so it is computed purely
from the seed (not from generated text) — exactly the structural, reproducible
quantity QA asserts equality on.
"""

from __future__ import annotations

import hashlib
import json
import random
from typing import Sequence

# Number of shared-stream draws folded into ``shared_event_hash``. Large enough to
# fingerprint the whole exogenous plan that ``events.py`` derives from the same
# stream, so equal hash <=> equal seed <=> identical shared (A/B) event stream.
_HASH_TOKENS = 64


class SeededRNG:
    """Deterministic RNG with separated shared / per-branch streams.

    Construct from a single integer ``seed``. ``random`` / ``randint`` / ``choice``
    draw from a general sequential stream; ``branch_rng`` and ``shared_rng`` expose
    the decision-conditioned and exogenous-shared sub-streams respectively.
    """

    seed: int

    def __init__(self, seed: int, *, _stream: random.Random | None = None,
                 _branch: str | None = None) -> None:
        self.seed = int(seed)
        self.branch = _branch
        # General sequential stream. Seeded via the same stable derivation used
        # for every sub-stream so behaviour is platform-independent.
        self._rng = _stream if _stream is not None else random.Random(
            self._derive("stream", self.branch or "")
        )

    # ------------------------------------------------------------------ #
    # Stable seed derivation (platform-independent, unlike hash())
    # ------------------------------------------------------------------ #
    def _derive(self, *parts: object) -> int:
        """A stable 64-bit integer derived from the seed + the given parts."""
        blob = "|".join([str(self.seed), *(str(p) for p in parts)])
        digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        return int(digest[:16], 16)

    # ------------------------------------------------------------------ #
    # Protocol surface (general stream)
    # ------------------------------------------------------------------ #
    def random(self) -> float:
        """Next float in [0, 1) from the general stream."""
        return self._rng.random()

    def randint(self, a: int, b: int) -> int:
        """Next int in [a, b] (inclusive) from the general stream."""
        return self._rng.randint(a, b)

    def choice(self, seq: Sequence):  # type: ignore[type-arg]
        """Pick one element of ``seq`` from the general stream."""
        return self._rng.choice(list(seq))

    # ------------------------------------------------------------------ #
    # Sub-streams
    # ------------------------------------------------------------------ #
    def branch_rng(self, branch: str) -> "SeededRNG":
        """A child RNG for decision-conditioned draws (differs per branch).

        Derived from ``seed + branch`` so branch A and branch B diverge, while
        repeated runs with the same seed reproduce exactly (NFR-01).
        """
        sub = random.Random(self._derive("branch", branch))
        return SeededRNG(self.seed, _stream=sub, _branch=branch)

    def shared_rng(self) -> random.Random:
        """A fresh generator for the **shared** (exogenous) event stream.

        Derived from the *seed only* — never the branch — so both branches build
        an identical exogenous timeline (ALG-20/21). Returns a brand-new
        generator on every call so concurrent branch generation cannot race on
        shared mutable state.
        """
        return random.Random(self._derive("shared"))

    # ------------------------------------------------------------------ #
    # Reproducibility fingerprint
    # ------------------------------------------------------------------ #
    def _shared_tokens(self, n: int = _HASH_TOKENS) -> list[float]:
        """A deterministic, seed-only token sequence from the shared stream."""
        r = self.shared_rng()
        return [round(r.random(), 12) for _ in range(n)]

    def shared_event_hash(self) -> str:
        """Stable hash of the shared (non-decision) random-event stream.

        Depends only on the seed, so it is identical across branches A/B and
        across repeated same-seed runs (ALG-20 / NFR-01). 16 hex chars, matching
        the shape the seed-check endpoint and the Wave-1 stub returned.
        """
        payload = json.dumps(self._shared_tokens(), separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        b = f", branch={self.branch!r}" if self.branch else ""
        return f"SeededRNG(seed={self.seed}{b})"


__all__ = ["SeededRNG"]
