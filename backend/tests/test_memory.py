"""EverOS-inspired in-process memory stream (Phase 3).

Retrieval ranks by recency x importance x lexical relevance; reflection fires
once cumulative importance since the last reflection crosses the threshold.
All deterministic on the stub path (no key) — config.complete is monkeypatched
to None by the autouse fixture in conftest.
"""
from __future__ import annotations

from app.engine.memory import MemoryItem, MemoryStream


def test_retrieval_ranks_recency_importance_relevance():
    ms = MemoryStream()
    ms.add(MemoryItem(text="got a promotion at work", importance=9, month=5, source="event"))
    ms.add(MemoryItem(text="watered the plants", importance=1, month=1, source="event"))
    top = ms.retrieve(query="work promotion raise", now_month=5, k=1)
    assert top, "retrieval returns at least one item"
    assert "promotion" in top[0].text


def test_retrieval_respects_k_and_ordering():
    ms = MemoryStream()
    ms.add(MemoryItem(text="alpha relevant query word", importance=8, month=4, source="o"))
    ms.add(MemoryItem(text="beta unrelated topic", importance=3, month=1, source="o"))
    ms.add(MemoryItem(text="gamma query word again", importance=5, month=4, source="o"))
    top = ms.retrieve(query="relevant query word", now_month=4, k=2)
    assert len(top) == 2
    # The most relevant + recent + important comes first.
    assert top[0].text.startswith("alpha")


def test_retrieval_deterministic_tie_break():
    """Identical scoring inputs tie-break by (importance, -month) deterministically."""
    ms = MemoryStream()
    ms.add(MemoryItem(text="same words here", importance=5, month=2, source="o"))
    ms.add(MemoryItem(text="same words here", importance=7, month=2, source="o"))
    top = ms.retrieve(query="same words here", now_month=2, k=2)
    # Higher importance wins the tie.
    assert top[0].importance == 7


def test_reflection_fires_past_threshold():
    ms = MemoryStream(reflection_threshold=10)
    for i in range(4):
        ms.add(MemoryItem(text=f"stressful overtime {i}", importance=5, month=i, source="event"))
    reflections = ms.maybe_reflect(now_month=4)
    assert reflections, "a reflection is synthesized once the threshold is crossed"
    assert reflections[0].kind == "reflection"
    assert reflections[0].importance >= 5  # higher-level belief


def test_reflection_does_not_fire_below_threshold():
    ms = MemoryStream(reflection_threshold=150)
    ms.add(MemoryItem(text="minor thing", importance=2, month=1, source="event"))
    assert ms.maybe_reflect(now_month=1) == []


def test_reflection_resets_counter():
    ms = MemoryStream(reflection_threshold=10)
    for i in range(3):
        ms.add(MemoryItem(text=f"big event {i}", importance=6, month=i, source="event"))
    first = ms.maybe_reflect(now_month=2)
    assert first, "first reflection fires"
    # Counter reset: a single small item must not immediately re-trigger.
    ms.add(MemoryItem(text="small follow-up", importance=2, month=3, source="event"))
    assert ms.maybe_reflect(now_month=3) == []


def test_reflection_text_is_deterministic_on_stub():
    """With config.complete stubbed to None, reflection text is the deterministic
    concatenation of the top salient memory texts."""
    def build():
        ms = MemoryStream(reflection_threshold=10)
        for i in range(4):
            ms.add(MemoryItem(text=f"overtime crunch {i}", importance=5, month=i, source="event"))
        return ms.maybe_reflect(now_month=4)

    a = build()
    b = build()
    assert a and b
    assert a[0].text == b[0].text
