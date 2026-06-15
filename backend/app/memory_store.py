"""EverOS-inspired memory stream for Lynsea persona agents (owner: BE-Sim).

Owner file (BUILD_PLAN §4): ``backend/app/memory_store.py``. Consumed by
``app.simulation``; never re-defines another module's interface.

What this module is
-------------------
Each persona in the social simulation owns one :class:`MemoryStream` — a
chronological list of :class:`MemoryEntry` records, each carrying
``content`` / ``importance`` (1–10) / ``timestamp`` / ``embedding``. This mirrors
the Generative-Agents / EverOS "memory stream + retrieval + reflection" pattern
referenced in BUILD_PLAN §3.

Load-bearing invariants
------------------------
* **Retrieval (ALG-10)** scores every candidate by
  ``recency × importance × relevance`` — each of the three signals is min-max
  normalised across the candidate set and combined with per-signal weights
  (default equal). Ordering is fully deterministic: ties break by recency then
  by insertion order, so the same query over the same stream always returns the
  same ranking (no model call, no wall-clock — safe for NFR-01-style repro).
* **Reflection (ALG-11)** fires when the *cumulative importance* of observations
  added since the last reflection crosses :data:`DEFAULT_REFLECTION_THRESHOLD`
  (~150). It synthesises one or more **higher-level belief** entries
  (``kind="reflection"``) whose ``source_ids`` point back at the memories that
  produced them — i.e. a reflection *tree* and a fully traceable belief
  (supports ALG-14). Reflection entries themselves do **not** count toward the
  next cumulative-importance budget, so reflection cannot trigger itself.
* **Embeddings** come from a ``.env``-configured provider when one is wired,
  otherwise from a **deterministic local hashing embedding** so the whole stream
  runs offline with no API key (see :func:`default_embedder`).

The module is intentionally LLM-free in its core paths; an optional
``synthesizer`` callback lets the caller (``app.simulation``) plug an
``app.llm`` Haiku call into :meth:`MemoryStream.reflect` for nicer belief prose,
always with a deterministic structural fallback.
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

logger = logging.getLogger("lynsea.memory")

# Dimensionality of the local hashing embedding. Small but enough to separate
# the short belief/observation strings this simulation produces.
EMBED_DIM = 96

# Per-"time unit" (month) recency decay used by retrieval. 0.92 keeps a memory
# from last month at ~0.92 weight and one from six months ago at ~0.6.
RECENCY_DECAY = 0.92

# Cumulative importance that triggers reflection (BUILD_PLAN / ALG-11 ~150).
DEFAULT_REFLECTION_THRESHOLD = 150.0

# Default (recency, importance, relevance) weights for retrieval (ALG-10).
DEFAULT_RETRIEVAL_WEIGHTS: tuple[float, float, float] = (1.0, 1.0, 1.0)

Embedder = Callable[[str], list[float]]
# A reflection synthesizer maps the contributing memory contents to one or more
# higher-level belief statements. Returning ``[]`` means "nothing worth saying".
Synthesizer = Callable[[Sequence[str]], Sequence[str]]

_TOKEN_RE = re.compile(r"[A-Za-z0-9一-鿿]+")
_STOPWORDS = frozenset(
    "the a an and or of to in on for with about my me i you they them it is are "
    "be was were i'm about_decision around likely chance".split()
)


# --------------------------------------------------------------------------- #
# Local hashing embedding (offline default)
# --------------------------------------------------------------------------- #
def _tokenize(text: str) -> list[str]:
    return [t for t in (m.group(0).lower() for m in _TOKEN_RE.finditer(text)) if t]


def hashing_embedding(text: str, dim: int = EMBED_DIM) -> list[float]:
    """Deterministic, offline bag-of-tokens hashing embedding (L2-normalised).

    Each token is hashed into a bucket with a stable sign (the *signed hashing
    trick*), so semantically overlapping strings share buckets and yield a
    higher cosine similarity. Fully deterministic across processes/platforms
    (uses ``hashlib`` rather than the salted builtin ``hash``), which keeps
    retrieval reproducible.
    """
    vec = [0.0] * dim
    for tok in _tokenize(text):
        h = int(hashlib.blake2b(tok.encode("utf-8"), digest_size=8).hexdigest(), 16)
        bucket = h % dim
        sign = 1.0 if (h >> 16) & 1 else -1.0
        vec[bucket] += sign
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        return vec
    return [v / norm for v in vec]


def default_embedder() -> Embedder:
    """Return the embedder selected by ``.env``, else the local hashing fallback.

    Honors an optional ``EMBEDDING_PROVIDER`` env var so a deployment can wire a
    remote embedder later. No remote provider is bundled (Lynsea's only model
    access is Claude via ``app.llm``, which has no embeddings endpoint), so this
    currently always resolves to :func:`hashing_embedding` — logged, not
    silently — guaranteeing offline operation.
    """
    provider = os.getenv("EMBEDDING_PROVIDER", "").strip().lower()
    if provider and provider not in {"local", "hash", "hashing"}:
        logger.info(
            "memory: EMBEDDING_PROVIDER=%s requested but no remote embedder is "
            "wired; using deterministic local hashing embedding (offline).",
            provider,
        )
    return hashing_embedding


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity of two equal-length vectors; 0.0 for a zero vector."""
    if len(a) != len(b):
        raise ValueError("embedding length mismatch")
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / math.sqrt(na * nb)


# --------------------------------------------------------------------------- #
# Memory entry
# --------------------------------------------------------------------------- #
@dataclass
class MemoryEntry:
    """One memory in a persona's stream.

    ``kind`` is one of ``observation`` | ``belief`` | ``judgement`` |
    ``reflection`` | ``seed``. ``source_ids`` links a derived memory (a belief,
    judgement, or reflection) back to the memories it was built from — the chain
    that makes every downstream judgement traceable (ALG-14).
    """

    id: str
    content: str
    importance: float  # clamped to [1, 10]
    timestamp: float  # simulation time (month); higher == more recent
    embedding: list[float]
    kind: str = "observation"
    source_ids: list[str] = field(default_factory=list)
    seq: int = 0  # monotonic insertion order (recency tie-break)

    def recency(self, now: float, decay: float = RECENCY_DECAY) -> float:
        """Exponential recency in (0, 1]; 1.0 for a memory at/after ``now``."""
        age = max(0.0, now - self.timestamp)
        return decay**age


# --------------------------------------------------------------------------- #
# Retrieval result (entry + the component scores, for explainability/tests)
# --------------------------------------------------------------------------- #
@dataclass
class ScoredMemory:
    entry: MemoryEntry
    score: float
    recency: float
    importance: float
    relevance: float


# --------------------------------------------------------------------------- #
# Memory stream
# --------------------------------------------------------------------------- #
class MemoryStream:
    """A persona's memory stream with ALG-10 retrieval + ALG-11 reflection.

    Usage::

        ms = MemoryStream(owner_id="self")
        ms.add("Partner seemed unhappy about the move", importance=7, timestamp=2)
        hits = ms.retrieve("how does my partner feel", now=3, k=5)
        if ms.should_reflect():
            ms.reflect(now=3)
    """

    def __init__(
        self,
        owner_id: str,
        *,
        embedder: Optional[Embedder] = None,
        reflection_threshold: float = DEFAULT_REFLECTION_THRESHOLD,
        recency_decay: float = RECENCY_DECAY,
        weights: tuple[float, float, float] = DEFAULT_RETRIEVAL_WEIGHTS,
    ) -> None:
        self.owner_id = owner_id
        self._embed = embedder or default_embedder()
        self.reflection_threshold = float(reflection_threshold)
        self.recency_decay = float(recency_decay)
        self.weights = weights
        self._entries: list[MemoryEntry] = []
        self._seq = 0
        # Sum of importance of non-reflection memories added since last reflect().
        self._cumulative_importance = 0.0

    # ------------------------------------------------------------------ #
    # Introspection
    # ------------------------------------------------------------------ #
    def __len__(self) -> int:
        return len(self._entries)

    @property
    def entries(self) -> list[MemoryEntry]:
        return list(self._entries)

    @property
    def cumulative_importance(self) -> float:
        return self._cumulative_importance

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        for e in self._entries:
            if e.id == entry_id:
                return e
        return None

    # ------------------------------------------------------------------ #
    # Writing
    # ------------------------------------------------------------------ #
    def add(
        self,
        content: str,
        importance: float,
        timestamp: float,
        *,
        kind: str = "observation",
        source_ids: Optional[Sequence[str]] = None,
    ) -> MemoryEntry:
        """Append a memory; importance is clamped to [1, 10]; returns the entry.

        Reflection entries do not contribute to the cumulative-importance budget
        (so reflection cannot retrigger itself); everything else does.
        """
        imp = max(1.0, min(10.0, float(importance)))
        entry = MemoryEntry(
            id=f"{self.owner_id}:mem:{self._seq}",
            content=content,
            importance=imp,
            timestamp=float(timestamp),
            embedding=self._embed(content),
            kind=kind,
            source_ids=list(source_ids or []),
            seq=self._seq,
        )
        self._entries.append(entry)
        self._seq += 1
        if kind != "reflection":
            self._cumulative_importance += imp
        return entry

    # ------------------------------------------------------------------ #
    # Retrieval (ALG-10: recency x importance x relevance)
    # ------------------------------------------------------------------ #
    def score(
        self,
        query: str,
        now: float,
        *,
        weights: Optional[tuple[float, float, float]] = None,
        candidates: Optional[Sequence[MemoryEntry]] = None,
    ) -> list[ScoredMemory]:
        """Score candidates by the weighted sum of three min-max-normalised signals.

        Each of recency / importance / relevance is normalised to [0, 1] across
        the candidate set before weighting, matching the Generative-Agents
        retrieval formulation. Returned newest-first within equal scores.
        """
        pool = list(candidates if candidates is not None else self._entries)
        if not pool:
            return []

        w = weights or self.weights
        q_emb = self._embed(query)

        rec_raw = [e.recency(now, self.recency_decay) for e in pool]
        imp_raw = [e.importance / 10.0 for e in pool]
        rel_raw = [max(0.0, cosine_similarity(q_emb, e.embedding)) for e in pool]

        rec_n = _min_max(rec_raw)
        imp_n = _min_max(imp_raw)
        rel_n = _min_max(rel_raw)

        scored: list[ScoredMemory] = []
        for i, e in enumerate(pool):
            total = w[0] * rec_n[i] + w[1] * imp_n[i] + w[2] * rel_n[i]
            scored.append(
                ScoredMemory(
                    entry=e,
                    score=total,
                    recency=rec_n[i],
                    importance=imp_n[i],
                    relevance=rel_n[i],
                )
            )
        # Deterministic ordering: score desc, then recency (newest) desc, then
        # insertion order desc as the final stable tie-break.
        scored.sort(key=lambda s: (s.score, s.entry.timestamp, s.entry.seq), reverse=True)
        return scored

    def retrieve(
        self,
        query: str,
        now: float,
        k: int = 5,
        *,
        weights: Optional[tuple[float, float, float]] = None,
        kinds: Optional[Sequence[str]] = None,
    ) -> list[MemoryEntry]:
        """Top-``k`` memories for ``query`` at time ``now`` (ALG-10 ranking).

        ``kinds`` optionally restricts the candidate pool (e.g. retrieve only
        ``"belief"`` memories). Returns the entries only; use :meth:`score` when
        the component breakdown is needed (tests / explainability).
        """
        pool = self._entries
        if kinds is not None:
            allowed = set(kinds)
            pool = [e for e in self._entries if e.kind in allowed]
        ranked = self.score(query, now, weights=weights, candidates=pool)
        return [s.entry for s in ranked[: max(0, k)]]

    # ------------------------------------------------------------------ #
    # Reflection (ALG-11: threshold-triggered higher-level beliefs)
    # ------------------------------------------------------------------ #
    def should_reflect(self) -> bool:
        """True once accumulated observation importance crosses the threshold."""
        return self._cumulative_importance >= self.reflection_threshold

    def reflect(
        self,
        now: float,
        *,
        synthesizer: Optional[Synthesizer] = None,
        max_beliefs: int = 3,
        top_n: int = 15,
    ) -> list[MemoryEntry]:
        """Synthesise higher-level belief memories from recent salient memories.

        Picks the ``top_n`` most salient (importance × recency) non-reflection
        memories, asks ``synthesizer`` (optional LLM) — falling back to a
        deterministic structural summariser — for up to ``max_beliefs`` belief
        statements, and writes each as a ``kind="reflection"`` entry whose
        ``source_ids`` are the contributing memories (reflection tree + ALG-14
        traceability). Resets the cumulative-importance budget and returns the
        new entries (possibly empty).
        """
        source = [e for e in self._entries if e.kind != "reflection"]
        if not source:
            return []

        source.sort(key=lambda e: (e.importance * e.recency(now, self.recency_decay)), reverse=True)
        salient = source[: max(1, top_n)]
        source_ids = [e.id for e in salient]
        contents = [e.content for e in salient]

        beliefs: list[str] = []
        if synthesizer is not None:
            try:
                beliefs = [b.strip() for b in synthesizer(contents) if b and b.strip()]
            except Exception as exc:  # never let enrichment break the sim
                logger.warning("memory: reflection synthesizer failed (%s); using fallback.", exc)
                beliefs = []
        if not beliefs:
            beliefs = _structural_reflection(contents, max_beliefs)
        beliefs = beliefs[: max(1, max_beliefs)]

        # Reflection importance: a notch above the mean of its sources, capped.
        mean_imp = sum(e.importance for e in salient) / len(salient)
        reflect_imp = min(10.0, round(mean_imp + 1.5, 1))

        created: list[MemoryEntry] = []
        for belief in beliefs:
            created.append(
                self.add(
                    belief,
                    importance=reflect_imp,
                    timestamp=now,
                    kind="reflection",
                    source_ids=source_ids,
                )
            )
        # Budget consumed by this reflection cycle.
        self._cumulative_importance = 0.0
        return created


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _min_max(values: list[float]) -> list[float]:
    """Min-max normalise to [0, 1]; all-equal input maps to all-1.0."""
    lo = min(values)
    hi = max(values)
    if hi - lo < 1e-12:
        return [1.0 for _ in values]
    span = hi - lo
    return [(v - lo) / span for v in values]


def _structural_reflection(contents: Sequence[str], max_beliefs: int) -> list[str]:
    """Deterministic, LLM-free reflection: surface the dominant recurring themes.

    Builds 1..``max_beliefs`` higher-level belief statements from the most
    frequent meaningful tokens across the contributing memories. Always returns
    at least one statement so reflection produces a usable belief offline.
    """
    counter: Counter[str] = Counter()
    for text in contents:
        for tok in set(_tokenize(text)):
            if tok in _STOPWORDS or len(tok) <= 2:
                continue
            counter[tok] += 1

    themes = [tok for tok, _ in counter.most_common(max_beliefs * 2) if counter[tok] >= 2]
    if not themes:
        themes = [tok for tok, _ in counter.most_common(max_beliefs)]

    beliefs: list[str] = []
    n = len(contents)
    for theme in themes[:max_beliefs]:
        beliefs.append(
            f"Higher-level belief: '{theme}' has been a recurring thread across "
            f"{n} recent experiences — it now reads as a stable pattern, not a one-off."
        )
    if not beliefs:
        beliefs.append(
            f"Higher-level belief: the last {n} experiences cohere into a stable "
            "overall outlook rather than isolated events."
        )
    return beliefs


__all__ = [
    "MemoryEntry",
    "MemoryStream",
    "ScoredMemory",
    "Embedder",
    "Synthesizer",
    "hashing_embedding",
    "default_embedder",
    "cosine_similarity",
    "EMBED_DIM",
    "RECENCY_DECAY",
    "DEFAULT_REFLECTION_THRESHOLD",
    "DEFAULT_RETRIEVAL_WEIGHTS",
]
