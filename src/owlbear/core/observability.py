"""Observability hook — structured JSONL event logging for all lifecycle events.

Provides :class:`ObservabilityHook` — a hook that writes structured events to a
JSONL file via :class:`EventStore`.  Each lifecycle event (session start/end,
tool use, errors, etc.) is captured as an :class:`ObservabilityEvent` with
optional duration tracking for pre/post tool-use pairs.

The ``EventStore`` follows the same append-only JSONL pattern as
:class:`~owlbear.memory.usage.UsageTracker`.
"""

from __future__ import annotations

import logging
import time
from collections import Counter
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from owlbear.core.jsonl_store import JsonlStore

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import timedelta
    from pathlib import Path

    from owlbear.core.hooks import HookEvent, HookRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event model
# ---------------------------------------------------------------------------


class ObservabilityEvent(BaseModel, frozen=True):
    """A single lifecycle event observation.

    All optional fields default to ``None`` (or ``{}`` for metadata).
    The ``timestamp`` is an ISO-8601 string so it round-trips cleanly
    through JSON serialization.
    """

    timestamp: str
    event_type: str
    agent_name: str | None = None
    tool_name: str | None = None
    session_id: str | None = None
    success: bool = True
    error: str | None = None
    duration_ms: float | None = None
    metadata: dict = {}


# ---------------------------------------------------------------------------
# EventStore — append-only JSONL persistence + aggregation
# ---------------------------------------------------------------------------


class EventStore(JsonlStore[ObservabilityEvent]):
    """Append-only JSONL store for :class:`ObservabilityEvent`.

    Usage::

        store = EventStore(Path("~/.owlbear/events.jsonl"))
        store.append(event)
        recent = store.query(timedelta(hours=1))
        totals = store.summary(timedelta(hours=24))
    """

    def __init__(self, path: Path) -> None:
        super().__init__(path, ObservabilityEvent)

    # -- query ---------------------------------------------------------------

    def query(self, window: timedelta) -> list[ObservabilityEvent]:
        """Return events whose timestamp falls within *window* from now."""
        cutoff = datetime.now(UTC) - window
        cutoff_iso = cutoff.isoformat()
        return [e for e in self.load() if e.timestamp >= cutoff_iso]

    # -- aggregation ---------------------------------------------------------

    def summary(self, window: timedelta | None = None) -> dict:
        """Aggregate events within *window* (``None`` = all events).

        Returns a dict with keys: ``total_tool_calls``, ``error_count``,
        ``avg_tool_duration_ms``, ``tools_by_frequency``, ``agents_by_usage``.
        """
        events = self.load() if window is None else self.query(window)

        tool_events = [e for e in events if e.event_type == "post_tool_use"]
        error_events = [e for e in events if e.event_type == "on_error"]

        durations = [e.duration_ms for e in tool_events if e.duration_ms is not None]
        avg_dur = sum(durations) / len(durations) if durations else 0.0

        tool_counts: Counter[str] = Counter()
        for e in tool_events:
            if e.tool_name:
                tool_counts[e.tool_name] += 1

        agent_counts: Counter[str] = Counter()
        for e in events:
            if e.agent_name:
                agent_counts[e.agent_name] += 1

        return {
            "total_tool_calls": len(tool_events),
            "error_count": len(error_events),
            "avg_tool_duration_ms": avg_dur,
            "tools_by_frequency": dict(tool_counts),
            "agents_by_usage": dict(agent_counts),
        }

    def tool_stats(self, window: timedelta | None = None) -> dict[str, dict]:
        """Per-tool statistics within *window* (``None`` = all events).

        Returns a dict mapping ``tool_name`` to
        ``{call_count, error_count, avg_duration_ms}``.
        """
        events = self.load() if window is None else self.query(window)
        tool_events = [e for e in events if e.event_type == "post_tool_use" and e.tool_name]

        stats: dict[str, dict] = {}
        for e in tool_events:
            name = e.tool_name
            assert name is not None  # guarded above
            if name not in stats:
                stats[name] = {"call_count": 0, "error_count": 0, "_durations": []}
            stats[name]["call_count"] += 1
            if not e.success:
                stats[name]["error_count"] += 1
            if e.duration_ms is not None:
                stats[name]["_durations"].append(e.duration_ms)

        # Compute averages and remove internal accumulator.
        for info in stats.values():
            durations = info.pop("_durations")
            info["avg_duration_ms"] = sum(durations) / len(durations) if durations else 0.0

        return stats


# ---------------------------------------------------------------------------
# ObservabilityHook — lifecycle hook that writes events through EventStore
# ---------------------------------------------------------------------------


class ObservabilityHook:
    """Hook that logs structured events to a JSONL :class:`EventStore`.

    Registers on all :class:`~owlbear.core.hooks.HookEvent` types.  For
    ``PRE_TOOL_USE`` / ``POST_TOOL_USE`` pairs, calculates ``duration_ms``.

    Args:
        store: The :class:`EventStore` to append events to.
    """

    def __init__(self, store: EventStore) -> None:
        self._store = store
        self._timers: dict[str, float] = {}

    def register(self, hooks: HookRegistry) -> None:
        """Register a handler on every :class:`HookEvent`."""
        from owlbear.core.hooks import HookEvent  # noqa: PLC0415

        for event in HookEvent:
            hooks.register(event, self._make_handler(event))

    # -- internals -----------------------------------------------------------

    def _make_handler(self, event: HookEvent) -> Callable:
        """Create a single-arg handler closure for the hook registry."""

        async def _handler(data: dict[str, Any]) -> None:
            self._handle_event(event, data)

        return _handler

    def _handle_event(self, event: HookEvent, data: dict) -> None:
        """Build an :class:`ObservabilityEvent` and append it to the store."""
        tool_name = data.get("tool_name")
        agent_name = data.get("agent_name")
        session_id = data.get("session_id")
        duration_ms: float | None = None
        success = data.get("success", True)
        error = data.get("error")

        # Timer tracking for PRE/POST tool-use pairs.
        if event.value == "pre_tool_use" and tool_name:
            self._timers[tool_name] = time.monotonic()

        if event.value == "post_tool_use" and tool_name:
            start = self._timers.pop(tool_name, None)
            if start is not None:
                duration_ms = (time.monotonic() - start) * 1000.0

        # ON_ERROR events are always marked as failures.
        if event.value == "on_error":
            success = False

        ev = ObservabilityEvent(
            timestamp=datetime.now(UTC).isoformat(),
            event_type=event.value,
            agent_name=agent_name,
            tool_name=tool_name,
            session_id=session_id,
            success=success,
            error=error,
            duration_ms=duration_ms,
        )
        self._store.append(ev)
