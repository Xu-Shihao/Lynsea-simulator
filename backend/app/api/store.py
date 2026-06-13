"""In-memory simulation store (MVP — process-local, not persistent).

Maps sim_id -> a record holding the streaming queue, terminal state, the final
SimResult, and any error message. Each record's queue is an asyncio.Queue of
(event_type, payload) tuples consumed by the SSE endpoint.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Tuple

from ..contracts import SimResult


class SimRecord:
    """State for a single simulation run."""

    def __init__(self) -> None:
        self.queue: "asyncio.Queue[Tuple[str, dict]]" = asyncio.Queue()
        self.result: Optional[SimResult] = None
        self.done: bool = False
        self.error: Optional[str] = None
        # Buffer of all emitted events so late SSE subscribers can replay.
        self.history: List[Tuple[str, dict]] = []
        # Cooperative cancel handle + the background task, set by the API layer
        # so a /cancel request can signal and (best-effort) cancel the run.
        self.cancel_token: Optional[Any] = None
        self.task: Optional["asyncio.Task[Any]"] = None
        self.cancelled: bool = False

    async def emit(self, event_type: str, payload: dict) -> None:
        """Push an event onto the queue and into the replay buffer."""
        self.history.append((event_type, payload))
        await self.queue.put((event_type, payload))
        if event_type == "done":
            self.done = True
        elif event_type == "error":
            self.error = str(payload.get("message", "error"))
            self.done = True


class SimStore:
    """Process-local registry of SimRecords."""

    def __init__(self) -> None:
        self._records: Dict[str, SimRecord] = {}

    def create(self, sim_id: str) -> SimRecord:
        rec = SimRecord()
        self._records[sim_id] = rec
        return rec

    def get(self, sim_id: str) -> Optional[SimRecord]:
        return self._records.get(sim_id)

    def set_result(self, sim_id: str, result: SimResult) -> None:
        rec = self._records.get(sim_id)
        if rec is not None:
            rec.result = result


# Module-level singleton store.
STORE = SimStore()
