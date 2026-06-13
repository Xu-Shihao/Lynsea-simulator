"""ALG-31/32: an injected implausible event is rejected or downgraded+flagged."""
from __future__ import annotations

from app.engine import backbone as backbone_mod
from app.engine import personas as personas_mod
from app.engine import simulate as sim_mod


def test_implausible_event_flagged_or_replaced():
    decision = "Should I switch careers?"
    options = ["Switch careers", "Stay in current field"]
    seed = 7
    mode = "quick"

    personas = personas_mod.build_personas(decision, options, [], seed, mode)
    backbone = backbone_mod.build_backbone(decision, seed, mode)
    stats = sim_mod.make_stats()

    implausible = [
        {
            "month": 2,
            "title": "You win the lottery jackpot",
            "description": "A sudden windfall of millions arrives out of nowhere.",
            "kind": "perturbation",
            "involved_personas": [personas[0].id],
        }
    ]

    events = sim_mod.generate_branch_events(
        "A", options[0], decision, personas, backbone, seed, mode, stats,
        extra_proposals=implausible,
    )

    # The implausible event must not survive verbatim.
    assert all("lottery" not in (e.title + e.description).lower() for e in events)
    # The guard registered a rejection.
    assert stats.rejected >= 1
    assert stats.rejection_rate > 0
    # At least one event carries a guard evidence marker (resampled or downgraded).
    markers = [e.evidence for e in events if e.evidence]
    assert any(
        "implausible" in (m or "").lower() or "resampled" in (m or "").lower()
        for m in markers
    )


def test_is_implausible_helper():
    assert sim_mod._is_implausible("Win the lottery", "")
    assert sim_mod._is_implausible("A sudden death", "out of nowhere")
    assert not sim_mod._is_implausible("Start a new job", "Begin the role next month.")
