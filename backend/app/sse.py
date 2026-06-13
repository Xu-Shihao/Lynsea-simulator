"""Server-Sent Events framing helpers.

Frames bytes exactly per the api-contract "SSE framing" section::

    event: <type>\\n
    data: <single-line JSON>\\n
    \\n                     <- blank line terminates the event

`data` is always serialised as compact, single-line JSON (no embedded newlines)
so each event is exactly three lines. Pydantic models are dumped via
``model_dump_json`` (drops ``None`` is *not* applied — the contract fields are
explicit), plain dicts via ``json.dumps``.
"""

from __future__ import annotations

import json
from typing import Any, Union

from pydantic import BaseModel

Payload = Union[BaseModel, dict[str, Any]]


def _to_json(data: Payload) -> str:
    if isinstance(data, BaseModel):
        # compact, single line; preserves contract field names
        return data.model_dump_json()
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def sse_event(event: str, data: Payload) -> str:
    """Return one framed SSE event as a ``str`` (UTF-8 text).

    >>> sse_event("done", {"run_id": "abc"})
    'event: done\\ndata: {"run_id":"abc"}\\n\\n'
    """
    return f"event: {event}\ndata: {_to_json(data)}\n\n"


def sse_bytes(event: str, data: Payload) -> bytes:
    """Same as :func:`sse_event` but UTF-8 encoded for a byte stream."""
    return sse_event(event, data).encode("utf-8")


def sse_comment(text: str) -> str:
    """An SSE comment line (``: ...``) — used for keep-alive heartbeats.

    Comments are ignored by ``EventSource`` but keep the connection warm.
    """
    return f": {text}\n\n"
