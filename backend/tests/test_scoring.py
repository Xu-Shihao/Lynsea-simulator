"""ALG-40: every MetricPoint references >= 1 supporting event id."""
from __future__ import annotations

from app.contracts import METRIC_DIMS
from app.engine import backbone as backbone_mod
from app.engine import personas as personas_mod
from app.engine import scoring as scoring_mod
from app.engine import simulate as sim_mod
from app.engine.common import horizon_for_mode


def test_scores_have_supporting_events():
    decision = "Should I go back to school?"
    options = ["Go back to school", "Keep working"]
    seed = 100
    mode = "quick"

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
    for branch, opt, evs in (("A", options[0], all_events), ("B", options[1], all_events)):
        points = scoring_mod.score_branch(branch, opt, personas, evs, seed, mode)
        # One point per month 0..horizon.
        assert len(points) == horizon + 1
        for pt in points:
            assert pt.supporting_event_ids, "MetricPoint must reference >=1 event"
            for dim in METRIC_DIMS:
                v = getattr(pt, dim)
                assert 0.0 <= v <= 100.0
