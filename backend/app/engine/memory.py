"""In-process per-agent memory stream (EverOS-inspired, ALG-10 / ALG-11).

A lightweight, pure-Python memory layer for the multi-agent interaction loop.
NO vector embeddings — relevance is lexical (Jaccard over lowercased word sets),
so retrieval is fully deterministic given its inputs. This is deliberately a thin
in-process stand-in for the full EverOS markdown+SQLite+LanceDB stack (spec §4).

Each MemoryItem carries a free-text observation, an importance (1-10), the month
it occurred, its source, and a kind ("obs" | "reflection"). Retrieval ranks the
stream by a weighted blend of recency, importance, and lexical relevance to a
query. Reflection (ALG-11) synthesizes a higher-level belief item once the
cumulative importance of additions since the last reflection crosses a threshold
(~150 by default), then resets the counter.

Any LLM use for reflection summarization goes through `config.complete`; on the
stub path (or any failure) the reflection text is the deterministic concatenation
of the most salient memory texts, so tests stay green with no key.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .. import config

# Retrieval blend weights (ALG-10). Tuned so a clearly relevant + recent +
# important memory beats a stale trivial one, while no single term dominates.
_W_RECENCY: float = 1.0
_W_IMPORTANCE: float = 1.0
_W_LEXICAL: float = 1.5

_REFLECTION_SYSTEM = (
    "You synthesize a person's recent experiences into a single higher-level "
    "belief or realization, in one short sentence. Output the sentence only."
)


@dataclass
class MemoryItem:
    """A single memory: an observation, reflection, or recorded outcome."""

    text: str
    importance: int  # 1-10
    month: int
    source: str
    kind: str = "obs"  # "obs" | "reflection"

    def __post_init__(self) -> None:
        # Clamp importance into the documented 1-10 band so downstream scoring
        # (importance / 10) and reflection math stay well-behaved.
        try:
            imp = int(self.importance)
        except (TypeError, ValueError):
            imp = 1
        self.importance = max(1, min(10, imp))


def _words(text: str) -> set:
    """Lowercased word set for Jaccard lexical overlap."""
    return {w for w in (text or "").lower().split() if w}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


class MemoryStream:
    """An ordered, append-only memory stream with retrieval + reflection.

    `reflection_threshold` is the cumulative importance (sum of item importances
    added since the last reflection) at which `maybe_reflect` synthesizes a new
    belief. The spec's default is ~150 (ALG-11); callers in tight test loops pass
    a smaller threshold.
    """

    def __init__(self, reflection_threshold: int = 150) -> None:
        self.reflection_threshold = int(reflection_threshold)
        self.items: List[MemoryItem] = []
        # Cumulative importance accrued since the last reflection (reset on fire).
        self._since_reflection: int = 0

    # -- writes ----------------------------------------------------------------
    def add(self, item: MemoryItem) -> MemoryItem:
        """Append a memory and accrue its importance toward the next reflection."""
        self.items.append(item)
        self._since_reflection += int(item.importance)
        return item

    # -- retrieval (ALG-10) ----------------------------------------------------
    def _score(self, item: MemoryItem, query_words: set, now_month: int) -> float:
        recency = 1.0 / (1.0 + max(0, now_month - item.month))
        importance = item.importance / 10.0
        lexical = _jaccard(query_words, _words(item.text))
        return (
            _W_RECENCY * recency
            + _W_IMPORTANCE * importance
            + _W_LEXICAL * lexical
        )

    def retrieve(self, query: str, now_month: int, k: int = 5) -> List[MemoryItem]:
        """Return the top-k memories ranked by recency x importance x relevance.

        Deterministic tie-break by (importance, -month) so equal-scoring items
        order stably regardless of insertion order.
        """
        if k <= 0 or not self.items:
            return []
        query_words = _words(query)
        scored = [
            (self._score(it, query_words, now_month), it.importance, -it.month, idx, it)
            for idx, it in enumerate(self.items)
        ]
        # Sort by score desc, then importance desc, then month desc (-month asc on
        # the negative), then a stable index for full determinism.
        scored.sort(key=lambda t: (-t[0], -t[1], -t[2], t[3]))
        return [t[4] for t in scored[:k]]

    # -- reflection (ALG-11) ---------------------------------------------------
    def maybe_reflect(self, now_month: int) -> List[MemoryItem]:
        """Synthesize a higher-level belief if the importance threshold is met.

        Returns the newly added reflection item(s) (a list, possibly empty). The
        reflection text comes from `config.complete`; on the stub path / failure
        it is the deterministic concatenation of the top salient memory texts.
        Importance = min(10, avg_importance_of_salient + 2). Resets the counter.
        """
        if self._since_reflection < self.reflection_threshold:
            return []

        # Salient set: the most relevant-to-recent memories drive the belief.
        # Query with the most recent observation's text so the reflection is
        # anchored to what the agent is currently experiencing (deterministic).
        recent_obs = [it for it in self.items if it.kind != "reflection"]
        anchor = recent_obs[-1].text if recent_obs else ""
        salient = self.retrieve(query=anchor, now_month=now_month, k=min(5, len(self.items)))
        if not salient:
            # Nothing to reflect on; still reset so we don't spin.
            self._since_reflection = 0
            return []

        avg_imp = sum(it.importance for it in salient) / float(len(salient))
        importance = min(10, int(round(avg_imp)) + 2)

        text = self._summarize(salient)

        reflection = MemoryItem(
            text=text,
            importance=importance,
            month=now_month,
            source="reflection",
            kind="reflection",
        )
        # Append directly (do NOT route through add(): a reflection should not
        # itself count toward the next reflection's threshold) and reset.
        self.items.append(reflection)
        self._since_reflection = 0
        return [reflection]

    def _summarize(self, salient: List[MemoryItem]) -> str:
        """Belief text: LLM summary if available, else deterministic concat."""
        joined = "; ".join(it.text for it in salient)
        prompt = (
            "Recent experiences (most salient first):\n%s\n\n"
            "Summarize the single most important higher-level belief or pattern "
            "in one short sentence." % joined
        )
        try:
            out = config.complete(
                prompt, system=_REFLECTION_SYSTEM, max_tokens=80, temperature=0.3
            )
        except Exception:
            out = None
        if isinstance(out, str) and out.strip():
            return out.strip()
        # Deterministic stub fallback: a belief framed from the salient texts.
        return "I am noticing a pattern: " + joined
