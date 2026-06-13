"""ALG-20: shared exogenous events are identical across branch A and branch B."""
from __future__ import annotations

from app.engine import backbone as backbone_mod
from app.engine import personas as personas_mod
from app.engine import simulate as sim_mod


def _shared_signature(events, branch):
    sig = []
    for e in events:
        if e.branch == branch and e.is_shared_exogenous:
            sig.append((e.shared_event_id, e.month, e.title, e.description))
    return sorted(sig)


def test_shared_backbone_identical_across_branches():
    decision = "Should I take the new job offer?"
    options = ["Take the offer", "Stay put"]
    seed = 42
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

    sig_a = _shared_signature(events_a, "A")
    sig_b = _shared_signature(events_b, "B")

    assert sig_a  # backbone present in branch A
    assert sig_a == sig_b  # hash-equal on shared_event_id/month/title/description
