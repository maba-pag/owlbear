"""Failing tests for B-15: CockpitView facade — OCC mutations, admin operations,
activity/session reads (task #1078).

AC coverage:
  occ-edit     — CockpitView.edit_task requires expected_updated; mismatch → ConcurrencyError(ERR_STALE)
  occ-move     — CockpitView.move_task requires expected_updated; mismatch → ConcurrencyError(ERR_STALE)
  rel-claimed  — release_task on claimed task clears claim
  rel-noop     — release_task on unclaimed → idempotent, updated NOT advanced (AC-NEW-21)
  rel-miss     — release_task on missing id → NotFoundError(ERR_NOT_FOUND)
  sweep-ok     — sweep returns list of released task IDs (AC-NEW-22)
  sweep-idem   — sweep idempotent: second call → []
  sweep-fresh  — sweep with fresh claims returns []
  sweep-ints   — sweep return type is list[int]
  act-all      — list_activity with no filter returns all ActivityEvent records
  act-task-id  — list_activity filter by task_id
  act-action   — list_activity filter by action
  act-source   — list_activity filter by source
  act-since    — list_activity filter by since (time window)
  act-until    — list_activity filter by until (time window)
  act-empty    — list_activity on empty log returns []
  sess-records — list_sessions returns list[SessionRecord]
  sess-running — open claim with no close event → state='running'
  sess-all     — list_sessions(filter='all') includes completed sessions
  sess-released — list_sessions(filter='released') returns release-outcome sessions
  sess-empty   — list_sessions on empty log returns []
  scan-clean   — scan_corruption on clean board returns empty list
  scan-corrupt — scan_corruption with corrupt file returns list[CorruptionError]
  scan-ro      — scan_corruption is read-only (no file writes)
  scan-archive — scan_corruption checks archive/ dir too
  repair-ret   — repair_storage returns list of RepairOutcome objects
  repair-ph1   — repair_storage phase-1 quarantines corrupt files
  repair-ph2   — repair_storage phase-2 creates AR task for each quarantined file
  repair-start — repair_storage never called implicitly at engine startup
  compact-ret  — compact_activity returns ActivityCompactionResult
  compact-del  — compact_activity delegates to storage.compact_activity_log
  compact-empty — compact_activity on board with no activity does not raise
  role-admin   — CockpitView exposes all required admin methods
  role-no-create — CockpitView does NOT expose create_task
  role-no-start  — CockpitView does NOT expose start_work
  role-no-end    — CockpitView does NOT expose end_work
  role-no-pick   — CockpitView does NOT expose pick_tasks
  src-agent    — AgentView mutations emit ActivityEvent.source='agent'
  src-cockpit  — CockpitView mutations emit ActivityEvent.source='cockpit'
  src-engine   — sweep() emits ActivityEvent.source='engine'

All tests FAIL (RED phase).
"""

from __future__ import annotations

import inspect
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.corruption import CorruptionError
from owlbear_kanban.engine import CockpitView
from owlbear_kanban.models import (
    ActivityCompactionResult,
    ActivityEvent,
    ConcurrencyError,
    NotFoundError,
    RepairOutcome,
    SessionRecord,
    SingleTaskResponse,
)

# ---------------------------------------------------------------------------
# Board / task helpers
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - done
priorities:
  - someday
  - nice-to-have
  - important
  - needed
  - critical
entry_status: research
terminal_status: done
wave_size: 4
agent_map:
  research: researcher
  backlog: architect
  todo: builder
  in-progress: builder
  review: reviewer
  done: auditor
agent_types: {}
agent_compatibility: {}
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 100
"""

_TASK_TMPL = """\
---
id: {task_id}
title: {title}
status: {status}
priority: important
created: "2026-01-01T10:00:00+00:00"
updated: "{updated}"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: {claimed_at}
archival_reason: null
archival_refs: []
---
Task body.
"""


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_BASE_CONFIG, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write_task(  # noqa: PLR0913
    kanban_dir: Path,
    task_id: int,
    title: str = "Task",
    status: str = "research",
    updated: str = "2026-01-01T10:00:00+00:00",
    claimed_at: str = "null",
) -> Path:
    safe_title = title.lower().replace(" ", "-")
    filename = f"{task_id}-{safe_title}.md"
    path = kanban_dir / "tasks" / filename
    content = _TASK_TMPL.format(
        task_id=task_id,
        title=title,
        status=status,
        updated=updated,
        claimed_at=claimed_at,
    )
    path.write_text(content, encoding="utf-8")
    return path


def _make_cockpit_view(kanban_dir: Path) -> CockpitView:
    engine = KanbanEngine(kanban_dir)
    return CockpitView(engine)


def _write_activity_event(  # noqa: PLR0913
    kanban_dir: Path,
    *,
    task_id: int,
    action: str,
    source: str,
    detail: str,
    timestamp: str,
) -> None:
    event = {
        "timestamp": timestamp,
        "task_id": task_id,
        "action": action,
        "source": source,
        "detail": detail,
    }
    activity_path = kanban_dir / "activity.jsonl"
    with activity_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


# ---------------------------------------------------------------------------
# AC: occ-edit, occ-move — OCC guard on CockpitView.edit_task / move_task
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewOCC:
    """OCC guard on CockpitView.edit_task and CockpitView.move_task (D22+D46)."""

    # -- edit_task signature ---

    def test_edit_task_signature_has_expected_updated_param(self, tmp_path: Path) -> None:
        """CockpitView.edit_task must declare expected_updated as a keyword parameter."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        sig = inspect.signature(cv.edit_task)
        assert "expected_updated" in sig.parameters, (
            "CockpitView.edit_task must require expected_updated (OCC token)"
        )

    def test_edit_task_expected_updated_is_required_no_default(
        self, tmp_path: Path
    ) -> None:
        """CockpitView.edit_task.expected_updated must be mandatory (no default)."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        sig = inspect.signature(cv.edit_task)
        param = sig.parameters.get("expected_updated")
        assert param is not None, "expected_updated param missing"
        assert param.default is inspect.Parameter.empty, (
            "CockpitView.edit_task.expected_updated must be required (no default)"
        )

    def test_edit_task_stale_expected_updated_raises_concurrency_error(
        self, tmp_path: Path
    ) -> None:
        """edit_task with a stale expected_updated raises ConcurrencyError(ERR_STALE)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated="2026-01-01T10:00:00+00:00")
        cv = _make_cockpit_view(kanban_dir)
        with pytest.raises(ConcurrencyError) as exc_info:
            cv.edit_task(
                1,
                expected_updated="2025-01-01T00:00:00+00:00",  # stale token
                append_body="some edit",
            )
        assert exc_info.value.code == "ERR_STALE"

    def test_edit_task_matching_expected_updated_returns_single_task_response(
        self, tmp_path: Path
    ) -> None:
        """edit_task with a matching expected_updated returns SingleTaskResponse."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated="2026-01-01T10:00:00+00:00")
        cv = _make_cockpit_view(kanban_dir)
        result = cv.edit_task(
            1,
            expected_updated="2026-01-01T10:00:00+00:00",
            append_body="admin note",
        )
        assert isinstance(result, SingleTaskResponse)

    # -- move_task signature --

    def test_move_task_signature_has_expected_updated_param(self, tmp_path: Path) -> None:
        """CockpitView.move_task must declare expected_updated as a keyword parameter."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        sig = inspect.signature(cv.move_task)
        assert "expected_updated" in sig.parameters, (
            "CockpitView.move_task must require expected_updated (OCC token)"
        )

    def test_move_task_expected_updated_is_required_no_default(
        self, tmp_path: Path
    ) -> None:
        """CockpitView.move_task.expected_updated must be mandatory (no default)."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        sig = inspect.signature(cv.move_task)
        param = sig.parameters.get("expected_updated")
        assert param is not None, "expected_updated param missing"
        assert param.default is inspect.Parameter.empty, (
            "CockpitView.move_task.expected_updated must be required (no default)"
        )

    def test_move_task_stale_expected_updated_raises_concurrency_error(
        self, tmp_path: Path
    ) -> None:
        """move_task with a stale expected_updated raises ConcurrencyError(ERR_STALE)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated="2026-01-01T10:00:00+00:00")
        cv = _make_cockpit_view(kanban_dir)
        with pytest.raises(ConcurrencyError) as exc_info:
            cv.move_task(
                1,
                "backlog",
                expected_updated="2025-01-01T00:00:00+00:00",  # stale token
            )
        assert exc_info.value.code == "ERR_STALE"

    def test_move_task_matching_expected_updated_returns_single_task_response(
        self, tmp_path: Path
    ) -> None:
        """move_task with a matching expected_updated returns SingleTaskResponse."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated="2026-01-01T10:00:00+00:00")
        cv = _make_cockpit_view(kanban_dir)
        result = cv.move_task(
            1,
            "backlog",
            expected_updated="2026-01-01T10:00:00+00:00",
        )
        assert isinstance(result, SingleTaskResponse)


# ---------------------------------------------------------------------------
# AC: rel-claimed, rel-noop, rel-miss — CockpitView.release_task
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewReleaseTask:
    """release_task: idempotent no-op on unclaimed, NotFoundError on missing id."""

    def test_release_task_claimed_clears_claim_at(self, tmp_path: Path) -> None:
        """release_task on a claimed task clears claimed_at and returns SingleTaskResponse."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, claimed_at='"2026-01-01T09:00:00+00:00"')
        cv = _make_cockpit_view(kanban_dir)
        result = cv.release_task(1, expected_updated="2026-01-01T10:00:00+00:00")
        assert isinstance(result, SingleTaskResponse)
        assert result.claimed_at is None

    def test_release_task_unclaimed_is_idempotent_noop_updated_not_advanced(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-21: release_task on unclaimed task is a no-op; updated is NOT advanced."""
        kanban_dir = _make_board(tmp_path)
        original_updated = "2026-01-01T10:00:00+00:00"
        _write_task(kanban_dir, 1, updated=original_updated, claimed_at="null")
        cv = _make_cockpit_view(kanban_dir)
        result = cv.release_task(1, expected_updated=original_updated)
        assert isinstance(result, SingleTaskResponse)
        # updated must NOT be advanced — no mutation occurred
        assert result.updated == original_updated

    def test_release_task_missing_id_raises_not_found_error(self, tmp_path: Path) -> None:
        """release_task on a non-existent task id raises NotFoundError(ERR_NOT_FOUND)."""
        kanban_dir = _make_board(tmp_path)
        cv = _make_cockpit_view(kanban_dir)
        with pytest.raises(NotFoundError) as exc_info:
            cv.release_task(999, expected_updated="2026-01-01T10:00:00+00:00")
        assert exc_info.value.code == "ERR_NOT_FOUND"

    def test_release_task_unclaimed_returns_single_task_response(
        self, tmp_path: Path
    ) -> None:
        """release_task on unclaimed task returns SingleTaskResponse (current task state)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, claimed_at="null")
        cv = _make_cockpit_view(kanban_dir)
        result = cv.release_task(1, expected_updated="2026-01-01T10:00:00+00:00")
        assert isinstance(result, SingleTaskResponse)

    def test_release_task_stale_expected_updated_raises_concurrency_error(
        self, tmp_path: Path
    ) -> None:
        """release_task with a stale expected_updated raises ConcurrencyError(ERR_STALE)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated="2026-01-01T10:00:00+00:00", claimed_at="null")
        cv = _make_cockpit_view(kanban_dir)
        with pytest.raises(ConcurrencyError) as exc_info:
            cv.release_task(1, expected_updated="2025-01-01T00:00:00+00:00")  # stale token
        assert exc_info.value.code == "ERR_STALE"


# ---------------------------------------------------------------------------
# AC: sweep-ok, sweep-idem, sweep-fresh, sweep-ints — CockpitView.sweep
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewSweep:
    """sweep returns released task IDs (list[int]) and is idempotent (AC-NEW-22)."""

    def test_sweep_with_expired_claim_returns_task_id(self, tmp_path: Path) -> None:
        """AC-NEW-22: sweep releases expired claims and returns their IDs."""
        kanban_dir = _make_board(tmp_path)
        expired_ts = (datetime.now(tz=UTC) - timedelta(hours=2)).isoformat()
        _write_task(kanban_dir, 1, claimed_at=f'"{expired_ts}"')
        cv = _make_cockpit_view(kanban_dir)
        released = cv.sweep()
        assert isinstance(released, list)
        assert 1 in released

    def test_sweep_idempotent_second_call_returns_empty(self, tmp_path: Path) -> None:
        """AC-NEW-22: second sweep with no new expired claims returns []."""
        kanban_dir = _make_board(tmp_path)
        expired_ts = (datetime.now(tz=UTC) - timedelta(hours=2)).isoformat()
        _write_task(kanban_dir, 1, claimed_at=f'"{expired_ts}"')
        cv = _make_cockpit_view(kanban_dir)
        cv.sweep()  # first call — releases expired claim
        second = cv.sweep()  # second call — nothing left to release
        assert second == []

    def test_sweep_with_fresh_claim_returns_empty(self, tmp_path: Path) -> None:
        """sweep does not release claims that have not yet expired."""
        kanban_dir = _make_board(tmp_path)
        fresh_ts = (datetime.now(tz=UTC) - timedelta(minutes=1)).isoformat()
        _write_task(kanban_dir, 1, claimed_at=f'"{fresh_ts}"')
        cv = _make_cockpit_view(kanban_dir)
        released = cv.sweep()
        assert released == []

    def test_sweep_return_type_is_list_of_ints(self, tmp_path: Path) -> None:
        """sweep return type is list[int] — not list[str] or other type."""
        kanban_dir = _make_board(tmp_path)
        expired_ts = (datetime.now(tz=UTC) - timedelta(hours=2)).isoformat()
        _write_task(kanban_dir, 1, claimed_at=f'"{expired_ts}"')
        _write_task(kanban_dir, 2, title="Task Two", claimed_at=f'"{expired_ts}"')
        cv = _make_cockpit_view(kanban_dir)
        released = cv.sweep()
        assert all(isinstance(x, int) for x in released)

    def test_sweep_returns_exactly_the_expired_task_ids_no_extras_and_no_missing(
        self, tmp_path: Path
    ) -> None:
        """AC-NEW-22: sweep returns EXACTLY the set of expired claim IDs — no extras, no missing.

        A board with one expired task, one fresh-claimed task, and one unclaimed task.
        sweep() must return exactly {1}: not {1, 2}, not {1, 3}, not [].
        """
        kanban_dir = _make_board(tmp_path)
        expired_ts = (datetime.now(tz=UTC) - timedelta(hours=2)).isoformat()
        fresh_ts = (datetime.now(tz=UTC) - timedelta(minutes=1)).isoformat()
        _write_task(kanban_dir, 1, claimed_at=f'"{expired_ts}"')  # expired → must appear
        _write_task(kanban_dir, 2, title="Task Two", claimed_at=f'"{fresh_ts}"')  # fresh → must NOT appear
        _write_task(kanban_dir, 3, title="Task Three", claimed_at="null")  # unclaimed → must NOT appear
        cv = _make_cockpit_view(kanban_dir)
        released = cv.sweep()
        assert set(released) == {1}, (
            f"sweep returned {released!r} but must return exactly the set of expired IDs: {{1}}"
        )


# ---------------------------------------------------------------------------
# AC: act-all, act-task-id, act-action, act-source, act-since, act-until,
#     act-empty — CockpitView.list_activity
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewListActivity:
    """list_activity supports filtering by task_id, action, source, time window."""

    def _board_with_events(self, tmp_path: Path) -> tuple[Path, CockpitView]:
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1)
        _write_task(kanban_dir, 2, title="Task Two")
        _write_activity_event(
            kanban_dir, task_id=1, action="start_work", source="agent",
            detail="claimed", timestamp="2026-01-01T10:00:00+00:00",
        )
        _write_activity_event(
            kanban_dir, task_id=1, action="end_work", source="agent",
            detail="success", timestamp="2026-01-01T11:00:00+00:00",
        )
        _write_activity_event(
            kanban_dir, task_id=2, action="start_work", source="agent",
            detail="claimed", timestamp="2026-01-01T12:00:00+00:00",
        )
        _write_activity_event(
            kanban_dir, task_id=2, action="release", source="cockpit",
            detail="released by admin", timestamp="2026-01-01T13:00:00+00:00",
        )
        return kanban_dir, _make_cockpit_view(kanban_dir)

    def test_list_activity_no_filter_returns_all_events(self, tmp_path: Path) -> None:
        """list_activity() with no filters returns all ActivityEvent records."""
        _, cv = self._board_with_events(tmp_path)
        events = cv.list_activity()
        assert len(events) == 4
        assert all(isinstance(e, ActivityEvent) for e in events)

    def test_list_activity_filter_by_task_id(self, tmp_path: Path) -> None:
        """list_activity(task_id=1) returns only events for task 1."""
        _, cv = self._board_with_events(tmp_path)
        events = cv.list_activity(task_id=1)
        assert len(events) == 2
        assert all(e.task_id == 1 for e in events)

    def test_list_activity_filter_by_action(self, tmp_path: Path) -> None:
        """list_activity(action='start_work') returns only start_work events."""
        _, cv = self._board_with_events(tmp_path)
        events = cv.list_activity(action="start_work")
        assert len(events) == 2
        assert all(e.action == "start_work" for e in events)

    def test_list_activity_filter_by_source(self, tmp_path: Path) -> None:
        """list_activity(source='cockpit') returns only cockpit-sourced events."""
        _, cv = self._board_with_events(tmp_path)
        events = cv.list_activity(source="cockpit")
        assert len(events) == 1
        assert events[0].source == "cockpit"

    def test_list_activity_filter_by_since(self, tmp_path: Path) -> None:
        """list_activity(since=...) returns only events at or after that timestamp."""
        _, cv = self._board_with_events(tmp_path)
        events = cv.list_activity(since="2026-01-01T12:00:00+00:00")
        assert len(events) == 2

    def test_list_activity_since_returns_only_events_within_window_exact_identity(
        self, tmp_path: Path
    ) -> None:
        """since filter returns events with exact task_id and action identity, not just count."""
        # Board has 4 events: task1 start_work@10h, task1 end_work@11h,
        # task2 start_work@12h, task2 release@13h.
        # since=12h must return only the task2 events (start_work, release).
        _, cv = self._board_with_events(tmp_path)
        events = cv.list_activity(since="2026-01-01T12:00:00+00:00")
        task_ids = {e.task_id for e in events}
        actions = {e.action for e in events}
        assert task_ids == {2}, "since filter must exclude task1 events (before window)"
        assert actions == {"start_work", "release"}, (
            "since filter must return exactly task2 start_work and release events"
        )

    def test_list_activity_filter_by_until(self, tmp_path: Path) -> None:
        """list_activity(until=...) returns only events at or before that timestamp."""
        _, cv = self._board_with_events(tmp_path)
        events = cv.list_activity(until="2026-01-01T11:00:00+00:00")
        assert len(events) == 2

    def test_list_activity_until_returns_only_events_within_window_exact_identity(
        self, tmp_path: Path
    ) -> None:
        """until filter returns events with exact task_id and action identity, not just count."""
        # Board has 4 events: task1 start_work@10h, task1 end_work@11h,
        # task2 start_work@12h, task2 release@13h.
        # until=11h must return only the task1 events (start_work, end_work).
        _, cv = self._board_with_events(tmp_path)
        events = cv.list_activity(until="2026-01-01T11:00:00+00:00")
        task_ids = {e.task_id for e in events}
        actions = {e.action for e in events}
        assert task_ids == {1}, "until filter must exclude task2 events (after window)"
        assert actions == {"start_work", "end_work"}, (
            "until filter must return exactly task1 start_work and end_work events"
        )

    def test_list_activity_on_empty_log_returns_empty_list(self, tmp_path: Path) -> None:
        """list_activity on a board with no activity.jsonl returns []."""
        kanban_dir = _make_board(tmp_path)
        cv = _make_cockpit_view(kanban_dir)
        events = cv.list_activity()
        assert events == []


# ---------------------------------------------------------------------------
# AC: sess-records, sess-running, sess-all, sess-released, sess-empty —
#     CockpitView.list_sessions
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewListSessions:
    """list_sessions returns SessionRecord list with correct state derivation (D31)."""

    def _board_with_completed_session(self, tmp_path: Path) -> tuple[Path, CockpitView]:
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1)
        _write_activity_event(
            kanban_dir, task_id=1, action="start_work", source="agent",
            detail="claimed", timestamp="2026-01-01T10:00:00+00:00",
        )
        _write_activity_event(
            kanban_dir, task_id=1, action="end_work", source="agent",
            detail="success: research -> backlog", timestamp="2026-01-01T11:00:00+00:00",
        )
        return kanban_dir, _make_cockpit_view(kanban_dir)

    def test_list_sessions_returns_list_of_session_records(self, tmp_path: Path) -> None:
        """list_sessions returns list[SessionRecord]."""
        _, cv = self._board_with_completed_session(tmp_path)
        sessions = cv.list_sessions()
        assert isinstance(sessions, list)
        assert all(isinstance(s, SessionRecord) for s in sessions)

    def test_list_sessions_open_claim_has_state_running(self, tmp_path: Path) -> None:
        """An open claim not yet timed out → state='running' per D31."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1)
        fresh_ts = (datetime.now(tz=UTC) - timedelta(minutes=5)).isoformat()
        _write_activity_event(
            kanban_dir, task_id=1, action="start_work", source="agent",
            detail="claimed", timestamp=fresh_ts,
        )
        cv = _make_cockpit_view(kanban_dir)
        sessions = cv.list_sessions(filter="active")
        active = [s for s in sessions if s.task_id == 1]
        assert len(active) == 1
        assert active[0].state == "running"

    def test_list_sessions_filter_all_includes_completed_sessions(
        self, tmp_path: Path
    ) -> None:
        """list_sessions(filter='all') includes completed/ended sessions."""
        _, cv = self._board_with_completed_session(tmp_path)
        sessions = cv.list_sessions(filter="all")
        assert len(sessions) >= 1

    def test_list_sessions_filter_released_returns_release_outcome_sessions(
        self, tmp_path: Path
    ) -> None:
        """list_sessions(filter='released') returns sessions with outcome='release'."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1)
        _write_activity_event(
            kanban_dir, task_id=1, action="start_work", source="agent",
            detail="claimed", timestamp="2026-01-01T10:00:00+00:00",
        )
        _write_activity_event(
            kanban_dir, task_id=1, action="release", source="cockpit",
            detail="released by admin", timestamp="2026-01-01T11:00:00+00:00",
        )
        cv = _make_cockpit_view(kanban_dir)
        sessions = cv.list_sessions(filter="released")
        assert len(sessions) == 1
        assert sessions[0].outcome == "release"

    def test_list_sessions_completed_end_work_has_state_completed_and_outcome_success(
        self, tmp_path: Path
    ) -> None:
        """D31: end_work with 'success:' detail → state='completed', outcome='success'."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1)
        _write_activity_event(
            kanban_dir, task_id=1, action="start_work", source="agent",
            detail="claimed", timestamp="2026-01-01T10:00:00+00:00",
        )
        _write_activity_event(
            kanban_dir, task_id=1, action="end_work", source="agent",
            detail="success: research -> backlog", timestamp="2026-01-01T11:00:00+00:00",
        )
        cv = _make_cockpit_view(kanban_dir)
        sessions = cv.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 1]
        assert len(task_sessions) == 1
        assert task_sessions[0].state == "completed"
        assert task_sessions[0].outcome == "success"

    def test_list_sessions_rejected_end_work_has_state_rejected_and_outcome_reject(
        self, tmp_path: Path
    ) -> None:
        """D31: end_work with 'reject:' detail → state='rejected', outcome='reject'."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1)
        _write_activity_event(
            kanban_dir, task_id=1, action="start_work", source="agent",
            detail="claimed", timestamp="2026-01-01T10:00:00+00:00",
        )
        _write_activity_event(
            kanban_dir, task_id=1, action="end_work", source="agent",
            detail="reject: research -> backlog", timestamp="2026-01-01T11:00:00+00:00",
        )
        cv = _make_cockpit_view(kanban_dir)
        sessions = cv.list_sessions(filter="blocked-or-rejected")
        rejected = [s for s in sessions if s.task_id == 1]
        assert len(rejected) == 1
        assert rejected[0].state == "rejected"
        assert rejected[0].outcome == "reject"

    def test_list_sessions_blocked_end_work_has_state_blocked_and_outcome_block(
        self, tmp_path: Path
    ) -> None:
        """D31: end_work with block/fail detail → state='blocked', outcome='block'."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1)
        _write_activity_event(
            kanban_dir, task_id=1, action="start_work", source="agent",
            detail="claimed", timestamp="2026-01-01T10:00:00+00:00",
        )
        _write_activity_event(
            kanban_dir, task_id=1, action="end_work", source="agent",
            detail="block: needs clarification", timestamp="2026-01-01T11:00:00+00:00",
        )
        cv = _make_cockpit_view(kanban_dir)
        sessions = cv.list_sessions(filter="blocked-or-rejected")
        blocked = [s for s in sessions if s.task_id == 1]
        assert len(blocked) == 1
        assert blocked[0].state == "blocked"
        assert blocked[0].outcome == "block"

    def test_list_sessions_open_stale_claim_has_state_stuck(self, tmp_path: Path) -> None:
        """D31: open claim older than claim_timeout (1h config) → state='stuck'."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1)
        stale_ts = (datetime.now(tz=UTC) - timedelta(hours=2)).isoformat()
        _write_activity_event(
            kanban_dir, task_id=1, action="start_work", source="agent",
            detail="claimed", timestamp=stale_ts,
        )
        cv = _make_cockpit_view(kanban_dir)
        sessions = cv.list_sessions(filter="active")
        stuck = [s for s in sessions if s.task_id == 1]
        assert len(stuck) == 1
        assert stuck[0].state == "stuck"

    def test_list_sessions_sweep_released_claim_has_state_expired(
        self, tmp_path: Path
    ) -> None:
        """D31: sweep-release close action → state='expired', outcome='expired'."""
        kanban_dir = _make_board(tmp_path)
        expired_ts = (datetime.now(tz=UTC) - timedelta(hours=2)).isoformat()
        _write_task(kanban_dir, 1, claimed_at=f'"{expired_ts}"')
        _write_activity_event(
            kanban_dir, task_id=1, action="start_work", source="agent",
            detail="claimed", timestamp=expired_ts,
        )
        cv = _make_cockpit_view(kanban_dir)
        cv.sweep()  # emits sweep-release event closing the open claim
        sessions = cv.list_sessions(filter="all")
        expired = [s for s in sessions if s.state == "expired"]
        assert len(expired) == 1
        assert expired[0].task_id == 1
        assert expired[0].outcome == "expired"

    def test_list_sessions_empty_log_returns_empty_list(self, tmp_path: Path) -> None:
        """list_sessions on a board with no activity returns []."""
        kanban_dir = _make_board(tmp_path)
        cv = _make_cockpit_view(kanban_dir)
        result = cv.list_sessions(filter="all")
        assert result == []


# ---------------------------------------------------------------------------
# AC: scan-clean, scan-corrupt, scan-ro, scan-archive — CockpitView.scan_corruption
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewScanCorruption:
    """scan_corruption is read-only and returns list[CorruptionError]."""

    def test_scan_corruption_clean_board_returns_empty_list(self, tmp_path: Path) -> None:
        """scan_corruption on a clean board with valid tasks returns []."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1)
        cv = _make_cockpit_view(kanban_dir)
        result = cv.scan_corruption()
        assert result == []

    def test_scan_corruption_with_corrupt_file_returns_corruption_errors(
        self, tmp_path: Path
    ) -> None:
        """scan_corruption with an unparseable task file returns list[CorruptionError]."""
        kanban_dir = _make_board(tmp_path)
        (kanban_dir / "tasks" / "99-corrupt.md").write_text(
            "no yaml frontmatter here at all", encoding="utf-8"
        )
        cv = _make_cockpit_view(kanban_dir)
        result = cv.scan_corruption()
        assert len(result) >= 1
        assert all(isinstance(e, CorruptionError) for e in result)

    def test_scan_corruption_makes_no_writes_to_tasks_dir(self, tmp_path: Path) -> None:
        """scan_corruption is read-only — the set of files in tasks/ is unchanged after call."""
        kanban_dir = _make_board(tmp_path)
        (kanban_dir / "tasks" / "99-corrupt.md").write_text(
            "no yaml frontmatter here at all", encoding="utf-8"
        )
        tasks_dir = kanban_dir / "tasks"
        before_files = set(tasks_dir.iterdir())
        cv = _make_cockpit_view(kanban_dir)
        cv.scan_corruption()
        after_files = set(tasks_dir.iterdir())
        assert before_files == after_files, (
            "scan_corruption must not create or remove files in tasks/"
        )

    def test_scan_corruption_checks_archive_directory(self, tmp_path: Path) -> None:
        """scan_corruption also scans archive/ for corrupt files."""
        kanban_dir = _make_board(tmp_path)
        (kanban_dir / "archive" / "88-archive-corrupt.md").write_text(
            "not valid frontmatter", encoding="utf-8"
        )
        cv = _make_cockpit_view(kanban_dir)
        result = cv.scan_corruption()
        assert len(result) >= 1

    def test_scan_corruption_does_not_mutate_clean_task_file_contents(
        self, tmp_path: Path
    ) -> None:
        """scan_corruption must not mutate file contents — clean task byte content unchanged."""
        kanban_dir = _make_board(tmp_path)
        task_path = _write_task(kanban_dir, 1)
        content_before = task_path.read_bytes()
        cv = _make_cockpit_view(kanban_dir)
        cv.scan_corruption()
        content_after = task_path.read_bytes()
        assert content_after == content_before, (
            "scan_corruption must not modify clean task file contents (strictly read-only)"
        )

    def test_scan_corruption_does_not_mutate_corrupt_file_contents(
        self, tmp_path: Path
    ) -> None:
        """scan_corruption must not modify corrupt file contents — quarantine is repair_storage's job."""
        kanban_dir = _make_board(tmp_path)
        corrupt_content = b"no yaml frontmatter here at all"
        corrupt_path = kanban_dir / "tasks" / "99-corrupt.md"
        corrupt_path.write_bytes(corrupt_content)
        cv = _make_cockpit_view(kanban_dir)
        cv.scan_corruption()
        assert corrupt_path.exists(), (
            "scan_corruption must not delete corrupt files (quarantine is repair_storage's job)"
        )
        assert corrupt_path.read_bytes() == corrupt_content, (
            "scan_corruption must not modify corrupt file contents"
        )


# ---------------------------------------------------------------------------
# AC: repair-ret, repair-ph1, repair-ph2, repair-start — CockpitView.repair_storage
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewRepairStorage:
    """repair_storage: two-phase repair; never called implicitly at engine startup."""

    def test_repair_storage_returns_list_of_repair_outcomes(self, tmp_path: Path) -> None:
        """repair_storage returns list[RepairOutcome]."""
        kanban_dir = _make_board(tmp_path)
        cv = _make_cockpit_view(kanban_dir)
        result = cv.repair_storage()
        assert isinstance(result, list)
        assert all(isinstance(o, RepairOutcome) for o in result)

    def test_repair_storage_phase1_quarantines_corrupt_file(self, tmp_path: Path) -> None:
        """repair_storage phase-1 calls scan_and_fix → quarantines corrupt files."""
        kanban_dir = _make_board(tmp_path)
        (kanban_dir / "tasks" / "99-corrupt.md").write_text(
            "no yaml here", encoding="utf-8"
        )
        cv = _make_cockpit_view(kanban_dir)
        outcomes = cv.repair_storage()
        quarantined = [o for o in outcomes if o.action == "quarantined"]
        assert len(quarantined) >= 1

    def test_repair_storage_phase2_creates_ar_task_for_quarantined_file(
        self, tmp_path: Path
    ) -> None:
        """repair_storage phase-2 creates an action-required task per quarantined file."""
        kanban_dir = _make_board(tmp_path)
        (kanban_dir / "tasks" / "99-corrupt.md").write_text(
            "no yaml here", encoding="utf-8"
        )
        cv = _make_cockpit_view(kanban_dir)
        cv.repair_storage()
        # An AR task should exist with the type:user-action tag
        task_files = list((kanban_dir / "tasks").glob("*.md"))
        task_contents = [f.read_text(encoding="utf-8") for f in task_files]
        assert any("type:user-action" in c for c in task_contents), (
            "repair_storage must create an action-required task for each quarantined file"
        )

    def test_repair_storage_not_called_implicitly_at_engine_startup(
        self, tmp_path: Path
    ) -> None:
        """repair_storage must never be called implicitly at KanbanEngine init."""
        kanban_dir = _make_board(tmp_path)
        corrupt_path = kanban_dir / "tasks" / "99-corrupt.md"
        corrupt_path.write_text("no yaml here", encoding="utf-8")
        # Engine init must NOT repair the corrupt file
        _ = KanbanEngine(kanban_dir)
        assert corrupt_path.exists(), (
            "KanbanEngine.__init__ must not auto-repair corrupt files; "
            "repair_storage() is user-triggered only"
        )
        # Verify repair_storage exists on CockpitView and DOES repair when called explicitly
        cv = CockpitView(KanbanEngine(kanban_dir))
        assert hasattr(cv, "repair_storage"), "repair_storage must be on CockpitView"
        cv.repair_storage()
        quarantine_dir = kanban_dir / "quarantine"
        assert quarantine_dir.exists(), (
            "Explicit repair_storage() must quarantine corrupt files"
        )


# ---------------------------------------------------------------------------
# AC: compact-ret, compact-del, compact-empty — CockpitView.compact_activity
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewCompactActivity:
    """compact_activity delegates to storage.compact_activity_log."""

    def test_compact_activity_returns_activity_compaction_result(
        self, tmp_path: Path
    ) -> None:
        """compact_activity returns ActivityCompactionResult."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1)
        _write_activity_event(
            kanban_dir, task_id=1, action="start_work", source="agent",
            detail="claimed", timestamp="2026-01-01T10:00:00+00:00",
        )
        cv = _make_cockpit_view(kanban_dir)
        result = cv.compact_activity()
        assert isinstance(result, ActivityCompactionResult)

    def test_compact_activity_delegates_to_storage_compact_activity_log(
        self, tmp_path: Path
    ) -> None:
        """compact_activity calls storage.compact_activity_log (verified via spy)."""
        from unittest.mock import patch

        kanban_dir = _make_board(tmp_path)
        cv = _make_cockpit_view(kanban_dir)
        with patch("owlbear_kanban.storage.compact_activity_log") as mock_compact:
            mock_compact.return_value = ActivityCompactionResult(
                before_bytes=0, after_bytes=0, records_compacted=0
            )
            cv.compact_activity()
        mock_compact.assert_called_once()

    def test_compact_activity_on_board_with_no_log_does_not_raise(
        self, tmp_path: Path
    ) -> None:
        """compact_activity on a board with no activity.jsonl does not raise."""
        kanban_dir = _make_board(tmp_path)
        cv = _make_cockpit_view(kanban_dir)
        result = cv.compact_activity()
        assert isinstance(result, ActivityCompactionResult)


# ---------------------------------------------------------------------------
# AC: role-admin, role-no-* — CockpitView role separation
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewRoleSeparation:
    """CockpitView exposes admin methods and does NOT expose agent-only operations."""

    def test_cockpit_view_exposes_all_required_admin_methods(self, tmp_path: Path) -> None:
        """CockpitView must have sweep, scan_corruption, repair_storage,
        compact_activity, list_activity, list_sessions."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        required_admin = {
            "sweep",
            "scan_corruption",
            "repair_storage",
            "compact_activity",
            "list_activity",
            "list_sessions",
        }
        missing = {m for m in required_admin if not hasattr(cv, m)}
        assert not missing, f"Missing required admin methods on CockpitView: {missing}"

    def test_cockpit_view_does_not_expose_create_task(self, tmp_path: Path) -> None:
        """create_task is an agent-only operation — must not be on CockpitView."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        # Require an admin method to exist (fails if admin methods are absent)
        assert hasattr(cv, "sweep"), "sweep must exist before testing absence of create_task"
        assert not hasattr(cv, "create_task"), (
            "CockpitView must NOT expose create_task (agent-only)"
        )

    def test_cockpit_view_does_not_expose_start_work(self, tmp_path: Path) -> None:
        """start_work is an agent-only operation — must not be on CockpitView."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        assert hasattr(cv, "sweep"), "sweep must exist before testing absence of start_work"
        assert not hasattr(cv, "start_work"), (
            "CockpitView must NOT expose start_work (agent-only)"
        )

    def test_cockpit_view_does_not_expose_end_work(self, tmp_path: Path) -> None:
        """end_work is an agent-only operation — must not be on CockpitView."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        assert hasattr(cv, "compact_activity"), (
            "compact_activity must exist before testing absence of end_work"
        )
        assert not hasattr(cv, "end_work"), (
            "CockpitView must NOT expose end_work (agent-only)"
        )

    def test_cockpit_view_does_not_expose_pick_tasks(self, tmp_path: Path) -> None:
        """pick_tasks is an agent-only dispatcher operation — must not be on CockpitView."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        assert hasattr(cv, "list_activity"), (
            "list_activity must exist before testing absence of pick_tasks"
        )
        assert not hasattr(cv, "pick_tasks"), (
            "CockpitView must NOT expose pick_tasks (AgentView-only dispatcher)"
        )


# ---------------------------------------------------------------------------
# AC: src-agent, src-cockpit, src-engine — ActivityEvent.source auto-population
# ---------------------------------------------------------------------------


class TestFromAC_ActivityEventSource:
    """ActivityEvent.source is auto-populated: 'agent', 'cockpit', or 'engine' (§3.8)."""

    def test_agent_view_mutation_emits_source_agent(self, tmp_path: Path) -> None:
        """AgentView.start_work emits ActivityEvent with source='agent'."""
        from owlbear_kanban.activity_store import list_activity_events

        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1)
        engine = KanbanEngine(kanban_dir)
        engine.agent_view().start_work(1)
        events = list_activity_events(kanban_dir, action="start_work")
        start = [e for e in events if e.task_id == 1]
        assert len(start) == 1
        assert start[0].source == "agent"

    def test_cockpit_view_mutation_emits_source_cockpit(self, tmp_path: Path) -> None:
        """CockpitView.release_task emits ActivityEvent with source='cockpit'."""
        from owlbear_kanban.activity_store import list_activity_events

        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, claimed_at='"2026-01-01T09:00:00+00:00"')
        cv = _make_cockpit_view(kanban_dir)
        cv.release_task(1, expected_updated="2026-01-01T10:00:00+00:00")
        events = list_activity_events(kanban_dir, action="release", task_id=1)
        assert len(events) == 1
        assert events[0].source == "cockpit"

    def test_sweep_operation_emits_source_engine(self, tmp_path: Path) -> None:
        """sweep() (engine auto-operation) emits ActivityEvent with source='engine'."""
        from owlbear_kanban.activity_store import list_activity_events

        kanban_dir = _make_board(tmp_path)
        expired_ts = (datetime.now(tz=UTC) - timedelta(hours=2)).isoformat()
        _write_task(kanban_dir, 1, claimed_at=f'"{expired_ts}"')
        cv = _make_cockpit_view(kanban_dir)
        cv.sweep()
        events = list_activity_events(kanban_dir, action="sweep-release", task_id=1)
        assert len(events) == 1
        assert events[0].source == "engine"

    def test_cockpit_view_edit_task_emits_source_cockpit(self, tmp_path: Path) -> None:
        """CockpitView.edit_task emits ActivityEvent with source='cockpit'."""
        from owlbear_kanban.activity_store import list_activity_events

        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated="2026-01-01T10:00:00+00:00")
        cv = _make_cockpit_view(kanban_dir)
        cv.edit_task(
            1,
            expected_updated="2026-01-01T10:00:00+00:00",
            append_body="admin edit",
        )
        events = list_activity_events(kanban_dir, action="edit", task_id=1)
        assert len(events) == 1
        assert events[0].source == "cockpit"

    def test_cockpit_view_move_task_emits_source_cockpit(self, tmp_path: Path) -> None:
        """CockpitView.move_task emits ActivityEvent with source='cockpit'."""
        from owlbear_kanban.activity_store import list_activity_events

        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated="2026-01-01T10:00:00+00:00")
        cv = _make_cockpit_view(kanban_dir)
        cv.move_task(1, "backlog", expected_updated="2026-01-01T10:00:00+00:00")
        events = list_activity_events(kanban_dir, action="move", task_id=1)
        assert len(events) == 1
        assert events[0].source == "cockpit"

    def test_agent_view_edit_task_emits_source_agent(self, tmp_path: Path) -> None:
        """AgentView.edit_task emits ActivityEvent with source='agent'."""
        from owlbear_kanban.activity_store import list_activity_events

        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated="2026-01-01T10:00:00+00:00")
        engine = KanbanEngine(kanban_dir)
        engine.agent_view().edit_task(1, append_body="agent note")
        events = list_activity_events(kanban_dir, action="edit", task_id=1)
        assert len(events) == 1
        assert events[0].source == "agent"

    def test_agent_view_move_task_emits_source_agent(self, tmp_path: Path) -> None:
        """AgentView.move_task emits ActivityEvent with source='agent'."""
        from owlbear_kanban.activity_store import list_activity_events

        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated="2026-01-01T10:00:00+00:00")
        engine = KanbanEngine(kanban_dir)
        engine.agent_view().move_task(1, "backlog")
        events = list_activity_events(kanban_dir, action="move", task_id=1)
        assert len(events) == 1
        assert events[0].source == "agent"
