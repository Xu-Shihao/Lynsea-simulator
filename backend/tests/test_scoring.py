"""ALG-40: every MetricPoint references >= 1 supporting event id and carries a
0-100 score for EVERY generated dimension id (dimension-agnostic scores map)."""
from __future__ import annotations

from app.contracts import DEFAULT_DIMENSIONS
from app.engine import backbone as backbone_mod
from app.engine import personas as personas_mod
from app.engine import scoring as scoring_mod
from app.engine import simulate as sim_mod
from app.engine.common import horizon_for_mode


def test_scores_have_supporting_events_and_every_dimension():
    decision = "Should I go back to school?"
    options = ["Go back to school", "Keep working"]
    seed = 100
    mode = "quick"

    dims = [d.model_copy() for d in DEFAULT_DIMENSIONS]
    dim_ids = {d.id for d in dims}

    personas = personas_mod.build_personas(decision, options, ["my partner"], seed, mode)
    backbone = backbone_mod.build_backbone(decision, seed, mode)
    stats = sim_mod.make_stats()

    events_a = sim_mod.generate_branch_events(
        "A", options[0], decision, personas, backbone, seed, mode, stats
    )
    events_b = sim_mod.generate_branch_events(
        "B", options[1], decision, personas, backbone, seed, mode, stats
    )
    all_events = events_a + events_b

    horizon = horizon_for_mode(mode)
    for branch, opt in (("A", options[0]), ("B", options[1])):
        points = scoring_mod.score_branch(branch, opt, personas, all_events, seed, mode, dims)
        # One point per month 0..horizon.
        assert len(points) == horizon + 1
        for pt in points:
            assert pt.supporting_event_ids, "MetricPoint must reference >=1 event"
            # scores keyed by EVERY dimension id, each 0-100.
            assert set(pt.scores.keys()) == dim_ids
            for v in pt.scores.values():
                assert 0.0 <= v <= 100.0
