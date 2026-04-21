"""TDD RED: C-09 — engine activity/session tests.

Task: #1054 (Brief C #1043) — paper-c.md §8.9
AC:   C42 (engine side), C43, fresh canonical stream
All tests FAIL (RED phase — new engine activity methods not yet implemented).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.storage import (  # NEW module — ImportError in RED
    ActivityEvent,
    SessionRecord,
    append_activity_event,
    list_activity_events,
)

# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - docs
  - done
priorities:
  - someday
  - nice-to-have
  - important
  - needed
  - critical
entry_status: research
wave_size: 4
agent_map: {}
agent_types: {}
agent_compatibility: {}
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1001
"""

_VALID_TASK = """\
---
id: {task_id}
title: Task {task_id}
status: {status}
priority: needed
created: "2026-04-21T10:00:00+00:00"
updated: "2026-04-21T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: null
archival_refs: []
---

## Notes

Content.
"""


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_task_file(kanban_dir: Path, task_id: int, status: str = "todo") -> Path:
    p = kanban_dir / "tasks" / f"{task_id}-task.md"
    p.write_text(_VALID_TASK.format(task_id=task_id, status=status), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# TestFromAC_EngineEmitsActivityEvents — AC-C42
# ---------------------------------------------------------------------------


class TestFromAC_EngineEmitsActivityEvents:
    """AC-C42: engine mutating operations append ActivityEvent entries to activity.jsonl."""

    def test_ac_c42_claim_task_emits_activity_event(self, tmp_path: Path) -> None:
        """AC-C42: start_work (claim) appends an ActivityEvent with action='claim'."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, "todo")

        engine = KanbanEngine(kanban_dir)
        engine.start_work(1001)

        events = list_activity_events(kanban_dir, task_id=1001)
        claim_events = [e for e in events if e.action == "claim"]
        assert claim_events, "Expected at least one 'claim' ActivityEvent"

    def test_ac_c42_end_work_emits_activity_event(self, tmp_path: Path) -> None:
        """AC-C42: end_work appends an ActivityEvent with action='end_work'."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, "todo")

        engine = KanbanEngine(kanban_dir)
        engine.start_work(1001)
        engine.end_work(1001, outcome="success", note="done")

        events = list_activity_events(kanban_dir, task_id=1001)
        end_events = [e for e in events if e.action == "end_work"]
        assert end_events, "Expected at least one 'end_work' ActivityEvent"

    def test_ac_c42_move_task_emits_activity_event(self, tmp_path: Path) -> None:
        """AC-C42: move_task appends an ActivityEvent with action='move'."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, "todo")

        engine = KanbanEngine(kanban_dir)
        engine.move_task(1001, "in-progress")

        events = list_activity_events(kanban_dir, task_id=1001)
        move_events = [e for e in events if e.action == "move"]
        assert move_events, "Expected at least one 'move' ActivityEvent"

    def test_ac_c42_edit_task_emits_activity_event(self, tmp_path: Path) -> None:
        """AC-C42: edit_task appends an ActivityEvent with action='edit'."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, "todo")

        engine = KanbanEngine(kanban_dir)
        engine.edit_task(1001, title="Updated title")

        events = list_activity_events(kanban_dir, task_id=1001)
        edit_events = [e for e in events if e.action == "edit"]
        assert edit_events, "Expected at least one 'edit' ActivityEvent"

    def test_ac_c42_sweep_emits_activity_event(self, tmp_path: Path) -> None:
        """AC-C42: sweep() appends an ActivityEvent for each released claim."""
        kanban_dir = _make_board(tmp_path)
        expired_ts = (datetime.now(tz=UTC) - timedelta(hours=3)).isoformat()
        task_content = _VALID_TASK.format(task_id=1001, status="in-progress").replace(
            "claimed_at: null", f'claimed_at: "{expired_ts}"'
        )
        (kanban_dir / "tasks" / "1001-expired.md").write_text(task_content, encoding="utf-8")

        engine = KanbanEngine(kanban_dir)
        released = engine.sweep()

        assert 1001 in released
        events = list_activity_events(kanban_dir, task_id=1001)
        sweep_events = [e for e in events if "sweep" in e.action]
        assert sweep_events, "Expected sweep-release ActivityEvent"

    def test_ac_c42_activity_event_has_source_field(self, tmp_path: Path) -> None:
        """AC-C42: emitted ActivityEvent carries source field ('agent'|'cockpit'|'engine')."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, "todo")

        engine = KanbanEngine(kanban_dir)
        engine.start_work(1001)

        events = list_activity_events(kanban_dir, task_id=1001)
        assert events
        for event in events:
            assert event.source in {"agent", "cockpit", "engine"}, (
                f"Unexpected source: {event.source}"
            )

    def test_ac_c42_activity_event_schema_matches_activity_event_model(
        self, tmp_path: Path
    ) -> None:
        """AC-C42: raw JSONL entries in activity.jsonl match ActivityEvent schema exactly."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, "todo")

        engine = KanbanEngine(kanban_dir)
        engine.start_work(1001)

        activity_file = kanban_dir / "activity.jsonl"
        assert activity_file.exists()
        lines = activity_file.read_text(encoding="utf-8").strip().splitlines()
        assert lines

        for line in lines:
            record = json.loads(line)
            # Must have all required ActivityEvent fields
            assert "timestamp" in record
            assert "action" in record
            assert "source" in record
            assert "detail" in record
            # task_id may be None for board-level events
            assert "task_id" in record

    def test_ac_c42_no_legacy_activity_log_format_after_fresh_start(
        self, tmp_path: Path
    ) -> None:
        """AC-C42 / fresh-stream: fresh board starts with no pre-existing activity history."""
        kanban_dir = _make_board(tmp_path)
        # No legacy activity.jsonl pre-seeded
        assert not (kanban_dir / "activity.jsonl").exists()

        _make_task_file(kanban_dir, 1001, "todo")
        engine = KanbanEngine(kanban_dir)
        engine.start_work(1001)

        events = list_activity_events(kanban_dir)
        # Only events produced by this engine; no legacy data
        actions = {e.action for e in events}
        assert "claim" in actions
        # No legacy fields like 'actor' that were used in the old format
        for event in events:
            assert not hasattr(event, "actor")


# ---------------------------------------------------------------------------
# TestFromAC_ListSessions — AC-C43
# ---------------------------------------------------------------------------


class TestFromAC_ListSessions:
    """AC-C43: list_sessions derives SessionRecord values from activity.jsonl."""

    def test_ac_c43_list_sessions_returns_session_records(self, tmp_path: Path) -> None:
        """AC-C43: list_sessions returns list[SessionRecord]."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, "todo")

        engine = KanbanEngine(kanban_dir)
        engine.start_work(1001)
        engine.end_work(1001, outcome="success", note="done")

        sessions = engine.list_sessions(filter="all")
        assert isinstance(sessions, list)
        assert len(sessions) >= 1
        assert isinstance(sessions[0], SessionRecord)

    def test_ac_c43_session_record_has_required_fields(self, tmp_path: Path) -> None:
        """AC-C43: SessionRecord has task_id, state, started_at, ended_at, outcome, duration_s."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, "todo")

        engine = KanbanEngine(kanban_dir)
        engine.start_work(1001)
        engine.end_work(1001, outcome="success", note="done")

        sessions = engine.list_sessions(filter="all")
        assert sessions
        s = sessions[0]
        assert hasattr(s, "task_id")
        assert hasattr(s, "task_status_at_start")
        assert hasattr(s, "state")
        assert hasattr(s, "started_at")
        assert hasattr(s, "ended_at")
        assert hasattr(s, "outcome")
        assert hasattr(s, "duration_s")

    def test_ac_c43_session_state_completed_on_success_end_work(self, tmp_path: Path) -> None:
        """AC-C43: closed session (success end_work) has state='completed', outcome='success'."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, "todo")

        engine = KanbanEngine(kanban_dir)
        engine.start_work(1001)
        engine.end_work(1001, outcome="success", note="done")

        sessions = engine.list_sessions(filter="all")
        completed = [s for s in sessions if s.task_id == 1001]
        assert completed
        assert completed[0].state == "completed"
        assert completed[0].outcome == "success"

    def test_ac_c43_session_state_blocked_on_block_end_work(self, tmp_path: Path) -> None:
        """AC-C43: end_work(outcome='block') produces state='blocked'."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, "todo")

        engine = KanbanEngine(kanban_dir)
        engine.start_work(1001)
        engine.end_work(1001, outcome="block", note="blocked by X")

        sessions = engine.list_sessions(filter="all")
        blocked = [s for s in sessions if s.task_id == 1001]
        assert blocked
        assert blocked[0].state == "blocked"

    def test_ac_c43_session_state_rejected_on_reject_end_work(self, tmp_path: Path) -> None:
        """AC-C43: end_work(outcome='reject') produces state='rejected'."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, "todo")

        engine = KanbanEngine(kanban_dir)
        engine.start_work(1001)
        engine.end_work(1001, outcome="reject", note="rejected back to todo")

        sessions = engine.list_sessions(filter="all")
        rejected = [s for s in sessions if s.task_id == 1001]
        assert rejected
        assert rejected[0].state == "rejected"

    def test_ac_c43_session_state_released_on_release(self, tmp_path: Path) -> None:
        """AC-C43: release_task produces state='released'."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, "todo")

        engine = KanbanEngine(kanban_dir)
        engine.start_work(1001)
        engine.release_task(1001)

        sessions = engine.list_sessions(filter="all")
        released = [s for s in sessions if s.task_id == 1001]
        assert released
        assert released[0].state == "released"

    def test_ac_c43_filter_active_returns_running_and_stuck(self, tmp_path: Path) -> None:
        """AC-C43: filter='active' returns only running + stuck sessions."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, "todo")
        _make_task_file(kanban_dir, 1002, "todo")

        engine = KanbanEngine(kanban_dir)
        engine.start_work(1001)  # Running
        engine.start_work(1002)
        engine.end_work(1002, outcome="success", note="done")  # Closed

        sessions = engine.list_sessions(filter="active")
        assert all(s.state in {"running", "stuck"} for s in sessions)
        task_ids = {s.task_id for s in sessions}
        assert 1001 in task_ids
        assert 1002 not in task_ids

    def test_ac_c43_filter_all_returns_every_session(self, tmp_path: Path) -> None:
        """AC-C43: filter='all' returns every session regardless of state."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, "todo")
        _make_task_file(kanban_dir, 1002, "todo")

        engine = KanbanEngine(kanban_dir)
        engine.start_work(1001)
        engine.start_work(1002)
        engine.end_work(1002, outcome="success", note="done")

        sessions = engine.list_sessions(filter="all")
        task_ids = {s.task_id for s in sessions}
        assert {1001, 1002}.issubset(task_ids)

    def test_ac_c43_filter_blocked_or_rejected(self, tmp_path: Path) -> None:
        """AC-C43: filter='blocked-or-rejected' returns blocked + rejected sessions only."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, "todo")
        _make_task_file(kanban_dir, 1002, "todo")
        _make_task_file(kanban_dir, 1003, "todo")

        engine = KanbanEngine(kanban_dir)
        engine.start_work(1001)
        engine.end_work(1001, outcome="block", note="blocked")
        engine.start_work(1002)
        engine.end_work(1002, outcome="reject", note="rejected")
        engine.start_work(1003)
        engine.end_work(1003, outcome="success", note="done")

        sessions = engine.list_sessions(filter="blocked-or-rejected")
        assert all(s.state in {"blocked", "rejected"} for s in sessions)
        task_ids = {s.task_id for s in sessions}
        assert 1001 in task_ids
        assert 1002 in task_ids
        assert 1003 not in task_ids

    def test_ac_c43_filter_released(self, tmp_path: Path) -> None:
        """AC-C43: filter='released' returns only released sessions."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, "todo")
        _make_task_file(kanban_dir, 1002, "todo")

        engine = KanbanEngine(kanban_dir)
        engine.start_work(1001)
        engine.release_task(1001)
        engine.start_work(1002)
        engine.end_work(1002, outcome="success", note="done")

        sessions = engine.list_sessions(filter="released")
        assert all(s.state == "released" for s in sessions)
        task_ids = {s.task_id for s in sessions}
        assert 1001 in task_ids
        assert 1002 not in task_ids

    def test_ac_c43_sessions_derived_from_activity_not_task_files(
        self, tmp_path: Path
    ) -> None:
        """AC-C43: list_sessions reads only activity.jsonl, NOT task frontmatter."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, "todo")

        engine = KanbanEngine(kanban_dir)
        engine.start_work(1001)
        engine.end_work(1001, outcome="success", note="done")

        read_calls: list[str] = []
        original_open = open  # noqa: WPS421

        def spy_open(path: object, *args: object, **kwargs: object) -> object:
            p = str(path)
            if p.endswith(".md"):
                read_calls.append(p)
            return original_open(path, *args, **kwargs)  # type: ignore[call-overload]

        with patch("builtins.open", side_effect=spy_open):
            engine.list_sessions(filter="all")

        assert read_calls == [], f"list_sessions read task .md files: {read_calls}"

    def test_ac_c43_task_status_at_start_captured_from_activity_event(
        self, tmp_path: Path
    ) -> None:
        """AC-C43: task_status_at_start in SessionRecord matches task status at claim time."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, "todo")

        engine = KanbanEngine(kanban_dir)
        engine.start_work(1001)
        engine.end_work(1001, outcome="success", note="done")

        sessions = engine.list_sessions(filter="all")
        matching = [s for s in sessions if s.task_id == 1001]
        assert matching
        assert matching[0].task_status_at_start == "todo"

    def test_ac_c43_empty_activity_log_returns_empty_list(self, tmp_path: Path) -> None:
        """AC-C43: no activity.jsonl → list_sessions returns []."""
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        sessions = engine.list_sessions(filter="all")
        assert sessions == []

    def test_ac_c43_session_record_state_values_match_spec(self, tmp_path: Path) -> None:
        """AC-C43: SessionRecord.state is one of the 7 allowed values from §7.2."""
        _allowed = {"running", "stuck", "completed", "blocked", "rejected", "released", "expired"}
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, "todo")

        engine = KanbanEngine(kanban_dir)
        engine.start_work(1001)
        engine.end_work(1001, outcome="success", note="done")

        sessions = engine.list_sessions(filter="all")
        for s in sessions:
            assert s.state in _allowed, f"Invalid state: {s.state}"
