"""NFR-01: same decision+seed => identical shared exogenous events and persona ids."""
from __future__ import annotations

import hashlib
import json

from app.engine import backbone as backbone_mod
from app.engine import personas as personas_mod


def _hash_backbone(events):
    blob = json.dumps(
        [
            {
                "shared_event_id": e["shared_event_id"],
                "month": e["month"],
                "title": e["title"],
                "description": e["description"],
            }
            for e in events
        ],
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def test_backbone_reproducible():
    decision = "Should I quit my job to start a company?"
    seed = 12345
    b1 = backbone_mod.build_backbone(decision, seed, "quick")
    b2 = backbone_mod.build_backbone(decision, seed, "quick")
    assert b1  # non-empty
    assert _hash_backbone(b1) == _hash_backbone(b2)


def test_persona_ids_reproducible():
    decision = "Should I move abroad for a new role?"
    options = ["Move abroad", "Stay home"]
    people = ["my partner Alex", "my manager"]
    seed = 999

    p1 = personas_mod.build_personas(decision, options, people, seed, "quick")
    p2 = personas_mod.build_personas(decision, options, people, seed, "quick")

    ids1 = [p.id for p in p1]
    ids2 = [p.id for p in p2]
    assert ids1 == ids2
    assert ids1[0] == "p_user"
    # 3-5 personas in quick mode
    assert 3 <= len(ids1) <= 5
