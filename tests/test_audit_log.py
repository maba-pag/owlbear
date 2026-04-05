"""Tests for the audit log module (task #185, implementation #163).

Covers: exports (3), DispatchEvent model (5), CompletionEvent model (7),
AuditEvent TypeAdapter (5), AuditLog init (2), log_dispatch (3),
log_completion (2), query (6), gitignore (1) = 34 TestFromAC tests.
Plus 2 builder-discovered edge cases = 36 tests total.

Module: ``packages/orchestrator/src/owlbear/audit/``

Interface:
  log_dispatch(self, event: DispatchEvent, session_id: str) -> None
  log_completion(self, event: CompletionEvent, session_id: str) -> None
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Annotated

import pytest
from pydantic import Field, TypeAdapter, ValidationError

from owlbear.audit import AuditLog, CompletionEvent, DispatchEvent

# Construct local TypeAdapter matching the module-level TypeAdapter[AuditEvent] in models.py.
# Discriminated union on the 'type' field per AC #163 models.py AuditEvent type alias.
_AuditEvent = Annotated[DispatchEvent | CompletionEvent, Field(discriminator="type")]
audit_adapter: TypeAdapter[DispatchEvent | CompletionEvent] = TypeAdapter(_AuditEvent)


# ---------------------------------------------------------------------------
# DispatchEvent model tests
# ---------------------------------------------------------------------------


class TestFromAC_DispatchEvent:  # noqa: N801
    """DispatchEvent: frozen, all fields, ISO-8601 timestamp, prompt_summary max 100 chars, type='dispatch'."""

    def test_all_fields_present(self) -> None:
        event = DispatchEvent(
            timestamp="2026-03-29T10:00:00Z",
            task_id=42,
            agent="builder",
            prompt_summary="do something useful",
            session_id="sess-abc",
        )
        assert event.timestamp == "2026-03-29T10:00:00Z"
        assert event.task_id == 42
        assert event.agent == "builder"
        assert event.prompt_summary == "do something useful"
        assert event.session_id == "sess-abc"

    def test_type_literal_is_dispatch(self) -> None:
        event = DispatchEvent(
            timestamp="2026-03-29T10:00:00Z",
            task_id=1,
            agent="tester",
            prompt_summary="x",
            session_id="s1",
        )
        assert event.type == "dispatch"

    def test_frozen_raises_on_mutation(self) -> None:
        event = DispatchEvent(
            timestamp="2026-03-29T10:00:00Z",
            task_id=1,
            agent="tester",
            prompt_summary="x",
            session_id="s1",
        )
        with pytest.raises((TypeError, ValidationError)):
            event.agent = "hacker"  # type: ignore[misc]

    def test_timestamp_is_iso8601_string(self) -> None:
        ts = "2026-03-29T10:00:00+00:00"
        event = DispatchEvent(
            timestamp=ts,
            task_id=1,
            agent="a",
            prompt_summary="p",
            session_id="s",
        )
        # Must be stored as a string
        assert isinstance(event.timestamp, str)
        # Must parse as valid ISO-8601
        datetime.fromisoformat(event.timestamp)

    def test_prompt_summary_max_100_chars_enforced(self) -> None:
        oversized = "x" * 101
        with pytest.raises(ValidationError):
            DispatchEvent(
                timestamp="2026-03-29T10:00:00Z",
                task_id=1,
                agent="a",
                prompt_summary=oversized,
                session_id="s",
            )


# ---------------------------------------------------------------------------
# CompletionEvent model tests
# ---------------------------------------------------------------------------


class TestFromAC_CompletionEvent:  # noqa: N801
    """CompletionEvent: frozen, all fields, outcome Literal, error optional, type='completion'."""

    def test_all_fields_present(self) -> None:
        event = CompletionEvent(
            timestamp="2026-03-29T10:01:00Z",
            task_id=42,
            agent="builder",
            outcome="success",
            duration_ms=1500,
            files_changed=["src/foo.py"],
            error=None,
        )
        assert event.timestamp == "2026-03-29T10:01:00Z"
        assert event.task_id == 42
        assert event.agent == "builder"
        assert event.outcome == "success"
        assert event.duration_ms == 1500
        assert event.files_changed == ["src/foo.py"]
        assert event.error is None

    def test_type_literal_is_completion(self) -> None:
        event = CompletionEvent(
            timestamp="2026-03-29T10:01:00Z",
            task_id=1,
            agent="a",
            outcome="success",
            duration_ms=0,
            files_changed=[],
            error=None,
        )
        assert event.type == "completion"

    def test_frozen_raises_on_mutation(self) -> None:
        event = CompletionEvent(
            timestamp="2026-03-29T10:01:00Z",
            task_id=1,
            agent="a",
            outcome="success",
            duration_ms=0,
            files_changed=[],
            error=None,
        )
        with pytest.raises((TypeError, ValidationError)):
            event.outcome = "hacked"  # type: ignore[misc]

    def test_outcome_success_accepted(self) -> None:
        event = CompletionEvent(
            timestamp="2026-03-29T10:01:00Z",
            task_id=1,
            agent="a",
            outcome="success",
            duration_ms=0,
            files_changed=[],
            error=None,
        )
        assert event.outcome == "success"

    def test_outcome_failure_accepted(self) -> None:
        event = CompletionEvent(
            timestamp="2026-03-29T10:01:00Z",
            task_id=1,
            agent="a",
            outcome="failure",
            duration_ms=100,
            files_changed=[],
            error="something went wrong",
        )
        assert event.outcome == "failure"

    def test_outcome_invalid_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            CompletionEvent(
                timestamp="2026-03-29T10:01:00Z",
                task_id=1,
                agent="a",
                outcome="partial",  # not in Literal["success","failure"]
                duration_ms=0,
                files_changed=[],
                error=None,
            )

    def test_error_accepts_none_and_str(self) -> None:
        e_none = CompletionEvent(
            timestamp="2026-03-29T10:01:00Z",
            task_id=1,
            agent="a",
            outcome="success",
            duration_ms=0,
            files_changed=[],
            error=None,
        )
        e_str = CompletionEvent(
            timestamp="2026-03-29T10:01:00Z",
            task_id=2,
            agent="a",
            outcome="failure",
            duration_ms=0,
            files_changed=[],
            error="it broke",
        )
        assert e_none.error is None
        assert e_str.error == "it broke"


# ---------------------------------------------------------------------------
# AuditEvent TypeAdapter (discriminated union)
# ---------------------------------------------------------------------------


class TestFromAC_AuditEventAdapter:  # noqa: N801
    """TypeAdapter round-trip and discriminated union via 'type' field."""

    def test_round_trip_dispatch_event(self) -> None:
        event = DispatchEvent(
            timestamp="2026-03-29T10:00:00Z",
            task_id=5,
            agent="planner",
            prompt_summary="plan now",
            session_id="sess-1",
        )
        restored = audit_adapter.validate_json(event.model_dump_json())
        assert isinstance(restored, DispatchEvent)
        assert restored.task_id == 5
        assert restored.agent == "planner"

    def test_round_trip_completion_event(self) -> None:
        event = CompletionEvent(
            timestamp="2026-03-29T10:01:00Z",
            task_id=5,
            agent="builder",
            outcome="success",
            duration_ms=2000,
            files_changed=["a.py"],
            error=None,
        )
        restored = audit_adapter.validate_json(event.model_dump_json())
        assert isinstance(restored, CompletionEvent)
        assert restored.duration_ms == 2000

    def test_discriminates_dispatch_by_type_field(self) -> None:
        raw = json.dumps(
            {
                "type": "dispatch",
                "timestamp": "2026-03-29T10:00:00Z",
                "task_id": 1,
                "agent": "a",
                "prompt_summary": "x",
                "session_id": "s",
            }
        )
        event = audit_adapter.validate_json(raw)
        assert isinstance(event, DispatchEvent)

    def test_discriminates_completion_by_type_field(self) -> None:
        raw = json.dumps(
            {
                "type": "completion",
                "timestamp": "2026-03-29T10:01:00Z",
                "task_id": 1,
                "agent": "a",
                "outcome": "failure",
                "duration_ms": 50,
                "files_changed": [],
                "error": "oops",
            }
        )
        event = audit_adapter.validate_json(raw)
        assert isinstance(event, CompletionEvent)

    def test_unknown_type_raises_validation_error(self) -> None:
        raw = json.dumps({"type": "unknown_event", "data": "x"})
        with pytest.raises(ValidationError):
            audit_adapter.validate_json(raw)


# ---------------------------------------------------------------------------
# AuditLog.__init__
# ---------------------------------------------------------------------------


class TestFromAC_AuditLogInit:  # noqa: N801
    """AuditLog.__init__: accepts Path, does not create dir eagerly."""

    def test_accepts_path(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit"
        log = AuditLog(audit_dir)
        assert log is not None

    def test_does_not_create_dir_eagerly(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit_lazy"
        AuditLog(audit_dir)
        assert not audit_dir.exists()


# ---------------------------------------------------------------------------
# AuditLog.log_dispatch()
# ---------------------------------------------------------------------------


class TestFromAC_LogDispatch:  # noqa: N801
    """log_dispatch(): writes JSONL line, creates audit_dir if missing, line is valid JSON."""

    def test_writes_jsonl_file_for_session(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit"
        log = AuditLog(audit_dir)
        log.log_dispatch(
            DispatchEvent(
                timestamp="2026-03-29T10:00:00Z",
                task_id=10,
                agent="researcher",
                prompt_summary="do research",
                session_id="sess-x",
            ),
            session_id="sess-x",
        )
        session_file = audit_dir / "sess-x.jsonl"
        assert session_file.exists()

    def test_creates_audit_dir_if_missing(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "nested" / "audit"
        assert not audit_dir.exists()
        log = AuditLog(audit_dir)
        log.log_dispatch(
            DispatchEvent(
                timestamp="2026-03-29T10:00:00Z",
                task_id=11,
                agent="architect",
                prompt_summary="design",
                session_id="sess-y",
            ),
            session_id="sess-y",
        )
        assert audit_dir.exists()

    def test_line_is_valid_dispatch_event_json(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit"
        log = AuditLog(audit_dir)
        log.log_dispatch(
            DispatchEvent(
                timestamp="2026-03-29T10:00:00Z",
                task_id=12,
                agent="builder",
                prompt_summary="implement it",
                session_id="sess-z",
            ),
            session_id="sess-z",
        )
        session_file = audit_dir / "sess-z.jsonl"
        line = session_file.read_text(encoding="utf-8").strip()
        parsed = audit_adapter.validate_json(line)
        assert isinstance(parsed, DispatchEvent)
        assert parsed.task_id == 12
        assert parsed.agent == "builder"
        assert parsed.session_id == "sess-z"


# ---------------------------------------------------------------------------
# AuditLog.log_completion()
# ---------------------------------------------------------------------------


class TestFromAC_LogCompletion:  # noqa: N801
    """log_completion(): appends JSONL line to session file."""

    def test_appends_to_session_file(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit"
        log = AuditLog(audit_dir)
        log.log_dispatch(
            DispatchEvent(
                timestamp="2026-03-29T10:00:00Z",
                task_id=20,
                agent="builder",
                prompt_summary="first",
                session_id="sess-c",
            ),
            session_id="sess-c",
        )
        log.log_completion(
            CompletionEvent(
                timestamp="2026-03-29T10:01:00Z",
                task_id=20,
                agent="builder",
                outcome="success",
                duration_ms=100,
                files_changed=["src/x.py"],
                error=None,
            ),
            session_id="sess-c",
        )
        session_file = audit_dir / "sess-c.jsonl"
        lines = session_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

    def test_line_is_valid_completion_event_json(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit"
        log = AuditLog(audit_dir)
        log.log_completion(
            CompletionEvent(
                timestamp="2026-03-29T10:01:00Z",
                task_id=21,
                agent="doc-writer",
                outcome="failure",
                duration_ms=300,
                files_changed=[],
                error="timed out",
            ),
            session_id="sess-d",
        )
        session_file = audit_dir / "sess-d.jsonl"
        line = session_file.read_text(encoding="utf-8").strip()
        parsed = audit_adapter.validate_json(line)
        assert isinstance(parsed, CompletionEvent)
        assert parsed.outcome == "failure"
        assert parsed.error == "timed out"


# ---------------------------------------------------------------------------
# AuditLog.query()
# ---------------------------------------------------------------------------


class TestFromAC_Query:  # noqa: N801
    """query(): no filters, agent filter, outcome filter, date_range filter, empty dir."""

    def _populate(self, log: AuditLog, session_id: str) -> None:
        """Write one dispatch + one completion event to a session."""
        log.log_dispatch(
            DispatchEvent(
                timestamp="2026-03-29T10:00:00Z",
                task_id=99,
                agent="reviewer",
                prompt_summary="review this",
                session_id=session_id,
            ),
            session_id=session_id,
        )
        log.log_completion(
            CompletionEvent(
                timestamp="2026-03-29T10:01:00Z",
                task_id=99,
                agent="reviewer",
                outcome="success",
                duration_ms=500,
                files_changed=[],
                error=None,
            ),
            session_id=session_id,
        )

    def test_empty_dir_returns_empty_list(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "empty_audit"
        audit_dir.mkdir()
        log = AuditLog(audit_dir)
        assert log.query() == []

    def test_no_filters_returns_all_events(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit"
        log = AuditLog(audit_dir)
        self._populate(log, "sess-1")
        self._populate(log, "sess-2")
        events = log.query()
        # 2 sessions x (1 dispatch + 1 completion) = 4 events
        assert len(events) == 4

    def test_agent_filter_returns_matching_only(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit"
        log = AuditLog(audit_dir)
        self._populate(log, "sess-a")  # reviewer events
        log.log_dispatch(
            DispatchEvent(
                timestamp="2026-03-29T10:00:00Z",
                task_id=50,
                agent="auditor",
                prompt_summary="audit task",
                session_id="sess-b",
            ),
            session_id="sess-b",
        )
        events = log.query(agent="reviewer")
        assert all(e.agent == "reviewer" for e in events)
        assert not any(e.agent == "auditor" for e in events)

    def test_outcome_filter_returns_only_completion_events(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit"
        log = AuditLog(audit_dir)
        log.log_dispatch(
            DispatchEvent(
                timestamp="2026-03-29T10:00:00Z",
                task_id=30,
                agent="builder",
                prompt_summary="build",
                session_id="sess-o",
            ),
            session_id="sess-o",
        )
        log.log_completion(
            CompletionEvent(
                timestamp="2026-03-29T10:01:00Z",
                task_id=30,
                agent="builder",
                outcome="failure",
                duration_ms=100,
                files_changed=[],
                error="broken",
            ),
            session_id="sess-o",
        )
        log.log_completion(
            CompletionEvent(
                timestamp="2026-03-29T10:02:00Z",
                task_id=31,
                agent="builder",
                outcome="success",
                duration_ms=200,
                files_changed=[],
                error=None,
            ),
            session_id="sess-o",
        )
        failures = log.query(outcome="failure")
        assert all(isinstance(e, CompletionEvent) for e in failures)
        assert all(e.outcome == "failure" for e in failures)
        assert len(failures) == 1

    def test_date_range_filter_includes_events_in_range(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit"
        log = AuditLog(audit_dir)
        self._populate(log, "sess-range")
        all_events = log.query()
        assert len(all_events) > 0
        # Wide-open range spanning all of history and future
        start = "2020-01-01T00:00:00Z"
        end = "2099-12-31T23:59:59Z"
        events_in_range = log.query(date_range=(start, end))
        assert len(events_in_range) == len(all_events)

    def test_date_range_filter_excludes_out_of_range(self, tmp_path: Path) -> None:
        audit_dir = tmp_path / "audit"
        log = AuditLog(audit_dir)
        self._populate(log, "sess-past")
        # Entirely past range — no event should match
        start = "1990-01-01T00:00:00Z"
        end = "1990-12-31T23:59:59Z"
        events = log.query(date_range=(start, end))
        assert events == []


# ---------------------------------------------------------------------------
# __init__.py exports
# ---------------------------------------------------------------------------


class TestFromAC_Exports:  # noqa: N801
    """__init__.py exports AuditLog, DispatchEvent, CompletionEvent (AC #163 line 1)."""

    def test_auditlog_exported(self) -> None:
        import owlbear.audit as _audit

        assert hasattr(_audit, "AuditLog")

    def test_dispatchevent_exported(self) -> None:
        import owlbear.audit as _audit

        assert hasattr(_audit, "DispatchEvent")

    def test_completionevent_exported(self) -> None:
        import owlbear.audit as _audit

        assert hasattr(_audit, "CompletionEvent")


# ---------------------------------------------------------------------------
# .gitignore check
# ---------------------------------------------------------------------------


class TestFromAC_GitIgnore:  # noqa: N801
    """data/audit/ is listed in .gitignore (AC #163 line 10)."""

    def test_data_audit_in_gitignore(self, project_root: Path) -> None:
        gitignore = project_root / ".gitignore"
        assert gitignore.exists(), ".gitignore not found at project root"
        content = gitignore.read_text(encoding="utf-8")
        assert "store/audit" in content, "store/audit/ missing from .gitignore"


# ---------------------------------------------------------------------------
# Builder-discovered edge cases
# ---------------------------------------------------------------------------


class TestBuilderDiscovered:
    """Edge cases discovered during GREEN phase — covers log.py lines 48 and 55."""

    def test_query_nonexistent_dir_returns_empty_list(self, tmp_path: Path) -> None:
        """query() returns [] when audit_dir was never created (line 48 coverage)."""
        audit_dir = tmp_path / "never_created"
        log = AuditLog(audit_dir)
        assert log.query() == []

    def test_query_skips_empty_lines_in_jsonl(self, tmp_path: Path) -> None:
        """query() ignores blank lines inside a JSONL file (line 55 coverage)."""
        audit_dir = tmp_path / "audit"
        audit_dir.mkdir()
        session_file = audit_dir / "sess-blank.jsonl"
        event = DispatchEvent(
            timestamp="2026-03-29T10:00:00Z",
            task_id=1,
            agent="builder",
            prompt_summary="test",
            session_id="sess-blank",
        )
        session_file.write_text(
            "\n" + event.model_dump_json() + "\n\n",
            encoding="utf-8",
        )
        log = AuditLog(audit_dir)
        events = log.query()
        assert len(events) == 1
        assert isinstance(events[0], DispatchEvent)
