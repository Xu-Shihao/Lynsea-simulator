"""test_engine.py — BE-Engine acceptance: deterministic RNG + two-layer events.

Covers ALG-20, ALG-21, ALG-30, ALG-31, ALG-32 and NFR-01 for the modules owned
by BE-Engine (``app.rng`` + ``app.events``):

* NFR-01 / ALG-20 — same seed ⇒ equal ``shared_event_hash``; the shared
  (perturbation) event stream is byte-identical across branches A and B, even
  when the two branches are generated concurrently.
* ALG-21 — pre-fork (shared) structure is consistent across branches.
* ALG-30 — both the skeleton (high-prob) and perturbation (low-prob) layers are
  produced, with the required ``{branch}-m{month}-{n}`` id convention.
* ALG-31 — the implausible-event rate is ≤ 2% (whitelist-constrained).
* ALG-32 — an incompatible perturbation is resampled then degraded to a flagged
  placeholder.

Run: pytest backend/tests/test_engine.py -v
"""
import concurrent.futures
import os
import re
import sys

import pytest

# Make ``app`` importable no matter where pytest is invoked from.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.events import (  # noqa: E402
    IMPLAUSIBLE_KEYWORDS,
    PERTURBATION_TYPES,
    DEGRADED_TITLE_PREFIX,
    _build_perturbation,
    _select_perturbation,
    generate_events,
    plausibility_rate,
    shared_signature,
)
from app.rng import SeededRNG  # noqa: E402
from app.schemas import Persona, ValueWeights, World  # noqa: E402

SEED = 4242
ID_RE = re.compile(r"^[ABC]-m\d+-\d+$")


def make_world(seed: int = SEED, mode: str = "quick") -> World:
    """A small shared world (identical for both branches, like the orchestrator)."""
    personas = [
        Persona(id="self", role="you", influence_weight=10, confidence="high"),
        Persona(id="partner", role="partner", influence_weight=8, confidence="high"),
        Persona(id="mentor", role="mentor", influence_weight=5, confidence="low"),
    ]
    return World(
        run_id="test-run",
        decision="Should I take the new job?",
        mode=mode,  # type: ignore[arg-type]
        seed=seed,
        options={"A": "Stay put", "B": "Take the job"},
        personas=personas,
        values=ValueWeights(),
    )


# --------------------------------------------------------------------------- #
# RNG: determinism + branch parity (ALG-20 / NFR-01)
# --------------------------------------------------------------------------- #
def test_same_seed_equal_shared_event_hash():
    assert SeededRNG(SEED).shared_event_hash() == SeededRNG(SEED).shared_event_hash()


def test_different_seed_different_hash():
    assert SeededRNG(SEED).shared_event_hash() != SeededRNG(SEED + 1).shared_event_hash()


def test_shared_event_hash_is_stable_hex_string():
    h = SeededRNG(SEED).shared_event_hash()
    assert isinstance(h, str) and h and re.fullmatch(r"[0-9a-f]+", h)


def test_shared_rng_identical_across_calls_and_branches():
    rng = SeededRNG(SEED)
    a = [rng.shared_rng().random() for _ in range(5)]
    b = [rng.shared_rng().random() for _ in range(5)]
    # A fresh shared generator each call -> identical sequence every time.
    assert a == b
    # branch_rng preserves the seed, so its shared stream matches the parent's.
    assert rng.branch_rng("A").shared_event_hash() == rng.shared_event_hash()


def test_branch_rng_differs_per_branch():
    rng = SeededRNG(SEED)
    a = [rng.branch_rng("A").random() for _ in range(5)]
    b = [rng.branch_rng("B").random() for _ in range(5)]
    assert a != b


def test_branch_rng_is_reproducible():
    a1 = [SeededRNG(SEED).branch_rng("A").random() for _ in range(5)]
    a2 = [SeededRNG(SEED).branch_rng("A").random() for _ in range(5)]
    assert a1 == a2


# --------------------------------------------------------------------------- #
# Events: branch parity of the shared layer (ALG-20 / ALG-21)
# --------------------------------------------------------------------------- #
def test_ab_shared_perturbations_identical():
    """ALG-20: perturbation (shared) events are identical across A and B."""
    world = make_world()
    rng = SeededRNG(world.seed)
    ev_a = generate_events(world, "A", rng)
    ev_b = generate_events(world, "B", rng)
    assert shared_signature(ev_a) == shared_signature(ev_b)
    # And there is actually a shared layer to compare.
    assert any(e.kind == "perturbation" for e in ev_a)


def test_ab_skeleton_months_match():
    """ALG-20 parity (as QA asserts live): skeleton covers the same months A/B."""
    world = make_world()
    rng = SeededRNG(world.seed)
    months_a = sorted(e.month for e in generate_events(world, "A", rng) if e.kind == "skeleton")
    months_b = sorted(e.month for e in generate_events(world, "B", rng) if e.kind == "skeleton")
    assert months_a == months_b
    assert months_a == list(range(1, 7))  # quick mode = 6 monthly skeleton events


def test_ab_shared_layer_identical_under_concurrency():
    """The shared stream must not race when A and B run in parallel threads."""
    world = make_world()
    rng = SeededRNG(world.seed)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        fa = pool.submit(generate_events, world, "A", rng)
        fb = pool.submit(generate_events, world, "B", rng)
        ev_a, ev_b = fa.result(), fb.result()
    assert shared_signature(ev_a) == shared_signature(ev_b)


def test_alg21_pre_fork_months_consistent():
    """ALG-21: before any divergence the branches share the same month structure."""
    world = make_world()
    rng = SeededRNG(world.seed)
    months_a = sorted(e.month for e in generate_events(world, "A", rng))
    months_b = sorted(e.month for e in generate_events(world, "B", rng))
    assert months_a == months_b


# --------------------------------------------------------------------------- #
# Events: reproducibility (NFR-01)
# --------------------------------------------------------------------------- #
def test_same_seed_identical_events():
    world1 = make_world()
    world2 = make_world()
    a1 = generate_events(world1, "A", SeededRNG(world1.seed))
    a2 = generate_events(world2, "A", SeededRNG(world2.seed))
    assert [e.model_dump() for e in a1] == [e.model_dump() for e in a2]


# --------------------------------------------------------------------------- #
# Events: two layers + id convention (ALG-30)
# --------------------------------------------------------------------------- #
def test_two_layers_present():
    world = make_world()
    ev = generate_events(world, "A", SeededRNG(world.seed))
    kinds = {e.kind for e in ev}
    assert "skeleton" in kinds and "perturbation" in kinds


def test_event_id_convention():
    world = make_world()
    for branch in ("A", "B"):
        for e in generate_events(world, branch, SeededRNG(world.seed)):
            assert ID_RE.match(e.event_id), e.event_id
            assert e.event_id.startswith(f"{branch}-m{e.month}-")
            assert e.branch == branch


# --------------------------------------------------------------------------- #
# Plausibility (ALG-31)
# --------------------------------------------------------------------------- #
def test_plausibility_rate_within_bound_many_seeds():
    for seed in range(40):
        world = make_world(seed=seed)
        ev = generate_events(world, "A", SeededRNG(seed)) + generate_events(world, "B", SeededRNG(seed))
        assert plausibility_rate(ev) <= 0.02


def test_no_implausible_keywords_emitted():
    for seed in range(40):
        world = make_world(seed=seed)
        for e in generate_events(world, "A", SeededRNG(seed)):
            text = f"{e.title} {e.detail}".lower()
            assert not any(kw in text for kw in IMPLAUSIBLE_KEYWORDS)


# --------------------------------------------------------------------------- #
# Resample-then-degrade (ALG-32)
# --------------------------------------------------------------------------- #
def test_select_degrades_when_all_types_exhausted():
    """ALG-32: every type already used -> resample budget spent -> degrade."""
    used = {t["type"] for t in PERTURBATION_TYPES}
    template, degraded = _select_perturbation(
        SeededRNG(1).shared_rng(), used, ["self"], {"self": "you"}
    )
    assert template is None and degraded is True


def test_degraded_placeholder_is_flagged_and_plausible():
    ev = _build_perturbation("A-m3-2", "A", 3, "self", None, True)
    assert ev.kind == "perturbation"
    assert ev.title.startswith(DEGRADED_TITLE_PREFIX)
    assert not any(kw in f"{ev.title} {ev.detail}".lower() for kw in IMPLAUSIBLE_KEYWORDS)


def test_select_returns_compatible_template_normally():
    template, degraded = _select_perturbation(
        SeededRNG(7).shared_rng(), set(), ["self", "partner"], {"self": "you", "partner": "partner"}
    )
    assert degraded is False and template is not None
    assert template in PERTURBATION_TYPES


# --------------------------------------------------------------------------- #
# Orchestrator binding: confirms "using real app.rng / app.events"
# --------------------------------------------------------------------------- #
def test_orchestrator_binds_real_engine():
    import app.events as events_mod
    import app.orchestrator as orch

    assert orch.generate_events is events_mod.generate_events
    assert isinstance(orch._make_rng(SEED), SeededRNG)
