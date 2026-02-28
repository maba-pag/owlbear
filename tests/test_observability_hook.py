"""Tests for owlbear.core.observability â€” ObservabilityHook JSONL event logging."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.core.observability import (
    EventStore,
    ObservabilityEvent,
    ObservabilityHook,
)

_event_adapter: TypeAdapter[ObservabilityEvent] = TypeAdapter(ObservabilityEvent)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _event(  # noqa: PLR0913
    *,
    event_type: str = "post_tool_use",
    agent_name: str | None = "builder",
    tool_name: str | None = "read_file",
    session_id: str | None = "sess-001",
    success: bool = True,
    error: str | None = None,
    duration_ms: float | None = 42.0,
    minutes_ago: int = 0,
    metadata: dict | None = None,
) -> ObservabilityEvent:
    """Build an ObservabilityEvent with a timestamp *minutes_ago* from now."""
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    return ObservabilityEvent(
        timestamp=ts.isoformat(),
        event_type=event_type,
        agent_name=agent_name,
        tool_name=tool_name,
        session_id=session_id,
        success=success,
        error=error,
        duration_ms=duration_ms,
        metadata=metadata or {},
    )


def _write_jsonl(path: Path, events: list[ObservabilityEvent]) -> None:
    """Manually write events as JSONL for test fixtures."""
    with path.open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(_event_adapter.dump_json(ev).decode("utf-8") + "\n")


# ---------------------------------------------------------------------------
# ObservabilityEvent model
# ---------------------------------------------------------------------------


class TestObservabilityEvent:
    """ObservabilityEvent is a frozen Pydantic model with the correct schema."""

    def test_event_has_required_fields(self) -> None:
        ev = _event()
        assert ev.timestamp is not None
        assert ev.event_type == "post_tool_use"
        assert ev.agent_name == "builder"
        assert ev.tool_name == "read_file"
        assert ev.session_id == "sess-001"
        assert ev.success is True
        assert ev.error is None
        assert ev.duration_ms == 42.0
        assert ev.metadata == {}

    def test_event_is_frozen(self) -> None:
        ev = _event()
        with pytest.raises(ValidationError, match="frozen"):
            ev.event_type = "changed"  # type: ignore[misc]

    def test_event_serializes_to_json(self) -> None:
        ev = _event(tool_name="grep_search", duration_ms=99.5)
        data = json.loads(_event_adapter.dump_json(ev))
        assert data["tool_name"] == "grep_search"
        assert data["duration_ms"] == 99.5
        assert "timestamp" in data
        assert "event_type" in data

    def test_event_optional_fields_default_none(self) -> None:
        ev = ObservabilityEvent(
            timestamp=datetime.now(UTC).isoformat(),
            event_type="session_start",
            success=True,
        )
        assert ev.agent_name is None
        assert ev.tool_name is None
        assert ev.session_id is None
        assert ev.error is None
        assert ev.duration_ms is None
        assert ev.metadata == {}


# ---------------------------------------------------------------------------
# EventStore â€” append / load
# ---------------------------------------------------------------------------


class TestEventStoreAppend:
    """EventStore.append() writes one JSONL line per event."""

    def test_append_creates_file(self, tmp_path: Path) -> None:
        store = EventStore(tmp_path / "events.jsonl")
        store.append(_event())
        assert store.path.exists()

    def test_append_writes_one_line(self, tmp_path: Path) -> None:
        store = EventStore(tmp_path / "events.jsonl")
        store.append(_event())
        lines = store.path.read_text().strip().splitlines()
        assert len(lines) == 1

    def test_append_writes_valid_json(self, tmp_path: Path) -> None:
        store = EventStore(tmp_path / "events.jsonl")
        store.append(_event(tool_name="run_terminal"))
        line = store.path.read_text().strip()
        data = json.loads(line)
        assert data["tool_name"] == "run_terminal"

    def test_append_multiple_events(self, tmp_path: Path) -> None:
        store = EventStore(tmp_path / "events.jsonl")
        for i in range(3):
            store.append(_event(duration_ms=float(i)))
        lines = store.path.read_text().strip().splitlines()
        assert len(lines) == 3

    def test_append_creates_parent_dirs(self, tmp_path: Path) -> None:
        store = EventStore(tmp_path / "sub" / "dir" / "events.jsonl")
        store.append(_event())
        assert store.path.exists()


class TestEventStoreLoad:
    """EventStore.load() deserializes all events from JSONL file."""

    def test_load_returns_events(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        events = [_event(duration_ms=1.0), _event(duration_ms=2.0)]
        _write_jsonl(p, events)
        store = EventStore(p)
        loaded = store.load()
        assert len(loaded) == 2
        assert all(isinstance(e, ObservabilityEvent) for e in loaded)

    def test_load_preserves_field_values(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        ev = _event(tool_name="semantic_search", duration_ms=123.4, agent_name="researcher")
        _write_jsonl(p, [ev])
        store = EventStore(p)
        loaded = store.load()
        assert loaded[0].tool_name == "semantic_search"
        assert loaded[0].duration_ms == 123.4
        assert loaded[0].agent_name == "researcher"

    def test_load_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        p.write_text("")
        store = EventStore(p)
        assert store.load() == []

    def test_load_nonexistent_file_returns_empty_list(self, tmp_path: Path) -> None:
        store = EventStore(tmp_path / "nope.jsonl")
        assert store.load() == []


# ---------------------------------------------------------------------------
# EventStore â€” query (time window)
# ---------------------------------------------------------------------------


class TestEventStoreQuery:
    """EventStore.query(window) filters events by timestamp window."""

    def test_query_returns_recent_events(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        recent = _event(minutes_ago=5)
        old = _event(minutes_ago=120)
        _write_jsonl(p, [old, recent])
        store = EventStore(p)
        result = store.query(timedelta(hours=1))
        assert len(result) == 1

    def test_query_returns_all_within_window(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        events = [_event(minutes_ago=i) for i in range(5)]
        _write_jsonl(p, events)
        store = EventStore(p)
        result = store.query(timedelta(hours=1))
        assert len(result) == 5

    def test_query_excludes_old_events(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        old = _event(minutes_ago=1440)
        _write_jsonl(p, [old])
        store = EventStore(p)
        result = store.query(timedelta(hours=1))
        assert len(result) == 0

    def test_query_empty_file_returns_empty(self, tmp_path: Path) -> None:
        store = EventStore(tmp_path / "nope.jsonl")
        assert store.query(timedelta(hours=1)) == []


# ---------------------------------------------------------------------------
# EventStore â€” summary aggregation
# ---------------------------------------------------------------------------


class TestEventStoreSummary:
    """EventStore.summary() returns aggregated statistics."""

    def test_summary_counts_tool_calls(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        events = [
            _event(event_type="post_tool_use", tool_name="read_file"),
            _event(event_type="post_tool_use", tool_name="grep_search"),
            _event(event_type="session_start"),
        ]
        _write_jsonl(p, events)
        store = EventStore(p)
        s = store.summary()
        assert s["total_tool_calls"] == 2

    def test_summary_counts_errors(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        events = [
            _event(event_type="on_error", success=False, error="TypeError"),
            _event(event_type="on_error", success=False, error="KeyError"),
            _event(event_type="post_tool_use", success=True),
        ]
        _write_jsonl(p, events)
        store = EventStore(p)
        s = store.summary()
        assert s["error_count"] == 2

    def test_summary_avg_duration(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        events = [
            _event(event_type="post_tool_use", duration_ms=10.0),
            _event(event_type="post_tool_use", duration_ms=30.0),
        ]
        _write_jsonl(p, events)
        store = EventStore(p)
        s = store.summary()
        assert s["avg_tool_duration_ms"] == pytest.approx(20.0)

    def test_summary_tools_by_frequency(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        events = [
            _event(event_type="post_tool_use", tool_name="read_file"),
            _event(event_type="post_tool_use", tool_name="read_file"),
            _event(event_type="post_tool_use", tool_name="grep_search"),
        ]
        _write_jsonl(p, events)
        store = EventStore(p)
        s = store.summary()
        assert s["tools_by_frequency"]["read_file"] == 2
        assert s["tools_by_frequency"]["grep_search"] == 1

    def test_summary_agents_by_usage(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        events = [
            _event(agent_name="builder"),
            _event(agent_name="builder"),
            _event(agent_name="researcher"),
        ]
        _write_jsonl(p, events)
        store = EventStore(p)
        s = store.summary()
        assert s["agents_by_usage"]["builder"] == 2
        assert s["agents_by_usage"]["researcher"] == 1

    def test_summary_empty_store(self, tmp_path: Path) -> None:
        store = EventStore(tmp_path / "nope.jsonl")
        s = store.summary()
        assert s["total_tool_calls"] == 0
        assert s["error_count"] == 0
        assert s["avg_tool_duration_ms"] == 0.0
        assert s["tools_by_frequency"] == {}
        assert s["agents_by_usage"] == {}

    def test_summary_respects_time_window(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        recent = _event(event_type="post_tool_use", minutes_ago=5)
        old = _event(event_type="post_tool_use", minutes_ago=120)
        _write_jsonl(p, [old, recent])
        store = EventStore(p)
        s = store.summary(timedelta(hours=1))
        assert s["total_tool_calls"] == 1


# ---------------------------------------------------------------------------
# EventStore â€” tool_stats aggregation
# ---------------------------------------------------------------------------


class TestEventStoreToolStats:
    """EventStore.tool_stats() returns per-tool statistics."""

    def test_tool_stats_call_count(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        events = [
            _event(event_type="post_tool_use", tool_name="read_file"),
            _event(event_type="post_tool_use", tool_name="read_file"),
            _event(event_type="post_tool_use", tool_name="grep_search"),
        ]
        _write_jsonl(p, events)
        store = EventStore(p)
        stats = store.tool_stats()
        assert stats["read_file"]["call_count"] == 2
        assert stats["grep_search"]["call_count"] == 1

    def test_tool_stats_error_count(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        events = [
            _event(
                event_type="post_tool_use",
                tool_name="run_terminal",
                success=False,
                error="Timeout",
            ),
            _event(
                event_type="post_tool_use",
                tool_name="run_terminal",
                success=True,
            ),
            _event(
                event_type="post_tool_use",
                tool_name="run_terminal",
                success=False,
                error="Exit 1",
            ),
        ]
        _write_jsonl(p, events)
        store = EventStore(p)
        stats = store.tool_stats()
        assert stats["run_terminal"]["error_count"] == 2

    def test_tool_stats_avg_duration(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        events = [
            _event(event_type="post_tool_use", tool_name="read_file", duration_ms=10.0),
            _event(event_type="post_tool_use", tool_name="read_file", duration_ms=30.0),
        ]
        _write_jsonl(p, events)
        store = EventStore(p)
        stats = store.tool_stats()
        assert stats["read_file"]["avg_duration_ms"] == pytest.approx(20.0)

    def test_tool_stats_empty_store(self, tmp_path: Path) -> None:
        store = EventStore(tmp_path / "nope.jsonl")
        assert store.tool_stats() == {}

    def test_tool_stats_respects_time_window(self, tmp_path: Path) -> None:
        p = tmp_path / "events.jsonl"
        recent = _event(event_type="post_tool_use", tool_name="read_file", minutes_ago=5)
        old = _event(event_type="post_tool_use", tool_name="grep_search", minutes_ago=120)
        _write_jsonl(p, [old, recent])
        store = EventStore(p)
        stats = store.tool_stats(timedelta(hours=1))
        assert "read_file" in stats
        assert "grep_search" not in stats


# ---------------------------------------------------------------------------
# ObservabilityHook â€” register + event handling
# ---------------------------------------------------------------------------


class TestObservabilityHookRegister:
    """ObservabilityHook.register(hooks) registers on all 9 HookEvent types."""

    def test_register_on_all_hook_events(self, tmp_path: Path) -> None:
        store = EventStore(tmp_path / "events.jsonl")
        hook = ObservabilityHook(store)
        registry = HookRegistry()
        hook.register(registry)
        for event in HookEvent:
            assert event in registry.handlers, f"Missing handler for {event}"
            assert len(registry.handlers[event]) >= 1


class TestObservabilityHookEvents:
    """ObservabilityHook writes JSONL events when hooks fire."""

    def test_session_start_writes_event(self, tmp_path: Path) -> None:
        store = EventStore(tmp_path / "events.jsonl")
        hook = ObservabilityHook(store)
        registry = HookRegistry()
        hook.register(registry)
        asyncio.run(
            registry.emit(HookEvent.SESSION_START, {"agent_name": "builder", "session_id": "s1"})
        )
        events = store.load()
        assert len(events) == 1
        assert events[0].event_type == "session_start"
        assert events[0].agent_name == "builder"
        assert events[0].session_id == "s1"

    def test_pre_tool_use_writes_event(self, tmp_path: Path) -> None:
        store = EventStore(tmp_path / "events.jsonl")
        hook = ObservabilityHook(store)
        registry = HookRegistry()
        hook.register(registry)
        asyncio.run(registry.emit(HookEvent.PRE_TOOL_USE, {"tool_name": "read_file"}))
        events = store.load()
        assert len(events) == 1
        assert events[0].event_type == "pre_tool_use"
        assert events[0].tool_name == "read_file"

    def test_post_tool_use_has_duration(self, tmp_path: Path) -> None:
        store = EventStore(tmp_path / "events.jsonl")
        hook = ObservabilityHook(store)
        registry = HookRegistry()
        hook.register(registry)

        # Fire PRE then POST for the same tool
        asyncio.run(registry.emit(HookEvent.PRE_TOOL_USE, {"tool_name": "read_file"}))
        asyncio.run(
            registry.emit(HookEvent.POST_TOOL_USE, {"tool_name": "read_file", "success": True})
        )
        events = store.load()
        post_events = [e for e in events if e.event_type == "post_tool_use"]
        assert len(post_events) == 1
        assert post_events[0].duration_ms is not None
        assert post_events[0].duration_ms >= 0.0

    def test_on_error_captures_error_details(self, tmp_path: Path) -> None:
        store = EventStore(tmp_path / "events.jsonl")
        hook = ObservabilityHook(store)
        registry = HookRegistry()
        hook.register(registry)
        asyncio.run(
            registry.emit(
                HookEvent.ON_ERROR,
                {"error": "TypeError: bad arg", "agent_name": "builder"},
            )
        )
        events = store.load()
        assert len(events) == 1
        assert events[0].event_type == "on_error"
        assert events[0].error == "TypeError: bad arg"
        assert events[0].success is False

    def test_task_complete_writes_event(self, tmp_path: Path) -> None:
        store = EventStore(tmp_path / "events.jsonl")
        hook = ObservabilityHook(store)
        registry = HookRegistry()
        hook.register(registry)
        asyncio.run(registry.emit(HookEvent.TASK_COMPLETE, {"agent_name": "builder"}))
        events = store.load()
        assert len(events) == 1
        assert events[0].event_type == "task_complete"

    def test_question_pending_writes_event(self, tmp_path: Path) -> None:
        store = EventStore(tmp_path / "events.jsonl")
        hook = ObservabilityHook(store)
        registry = HookRegistry()
        hook.register(registry)
        asyncio.run(registry.emit(HookEvent.QUESTION_PENDING, {"agent_name": "builder"}))
        events = store.load()
        assert len(events) == 1
        assert events[0].event_type == "question_pending"

    def test_multiple_events_accumulate(self, tmp_path: Path) -> None:
        store = EventStore(tmp_path / "events.jsonl")
        hook = ObservabilityHook(store)
        registry = HookRegistry()
        hook.register(registry)
        for event in [HookEvent.SESSION_START, HookEvent.ON_MESSAGE, HookEvent.SESSION_END]:
            asyncio.run(registry.emit(event, {"agent_name": "builder"}))
        events = store.load()
        assert len(events) == 3
        types = [e.event_type for e in events]
        assert "session_start" in types
        assert "on_message" in types
        assert "session_end" in types
