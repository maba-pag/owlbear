"""CockpitView facade regression tests.

Promoted from archived tasks #1078 and #1141 during test curation.

AC coverage:
  - CockpitView edit/move OCC API and CAS persistence contracts
  - CockpitView.edit_task title parameter contract
  - sweep list/CAS behavior and activity emission
  - list_activity and list_sessions facade behavior
  - scan/repair/compact admin operations and role separation
"""

from __future__ import annotations

import inspect
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.corruption import CorruptionError
from owlbear_cockpit.view import CockpitView
from owlbear_kanban.models import (
    ActivityCompactionResult,
    ConcurrencyError,
    RepairOutcome,
    SessionRecord,
    SingleTaskResponse,
)

# Provenance: promoted from archived task-scoped suites for #1078 and #1141.


# ---------------------------------------------------------------------------
# Board / task helpers
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
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
    path = kanban_dir / "tasks" / f"{task_id}-{safe_title}.md"
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
    return CockpitView(KanbanEngine(kanban_dir))


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
    with activity_path.open("a", encoding="utf-8") as file_obj:
        file_obj.write(json.dumps(event) + "\n")


# ---------------------------------------------------------------------------
# OCC API contracts
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewOCC:
    """OCC guard on CockpitView.edit_task and CockpitView.move_task."""

    def test_edit_task_signature_has_expected_updated_param(self, tmp_path: Path) -> None:
        """CockpitView.edit_task declares required expected_updated."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        sig = inspect.signature(cv.edit_task)
        assert "expected_updated" in sig.parameters, "CockpitView.edit_task must require expected_updated"

    def test_edit_task_expected_updated_is_required_no_default(self, tmp_path: Path) -> None:
        """CockpitView.edit_task.expected_updated has no default."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        sig = inspect.signature(cv.edit_task)
        param = sig.parameters.get("expected_updated")
        assert param is not None, "expected_updated param missing"
        assert param.default is inspect.Parameter.empty, "CockpitView.edit_task.expected_updated must be required"

    def test_edit_task_stale_expected_updated_raises_concurrency_error(self, tmp_path: Path) -> None:
        """edit_task with a stale OCC token raises ERR_STALE."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated="2026-01-01T10:00:00+00:00")
        cv = _make_cockpit_view(kanban_dir)

        with pytest.raises(ConcurrencyError) as exc_info:
            cv.edit_task(
                1,
                expected_updated="2025-01-01T00:00:00+00:00",
                append_body="some edit",
            )

        assert exc_info.value.code == "ERR_STALE"

    def test_edit_task_matching_expected_updated_returns_single_task_response(self, tmp_path: Path) -> None:
        """edit_task with a fresh OCC token returns SingleTaskResponse."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated="2026-01-01T10:00:00+00:00")
        cv = _make_cockpit_view(kanban_dir)

        result = cv.edit_task(
            1,
            expected_updated="2026-01-01T10:00:00+00:00",
            append_body="admin note",
        )

        assert isinstance(result, SingleTaskResponse)

    def test_edit_task_success_path_routes_through_write_task_if_unchanged(self, tmp_path: Path) -> None:
        """edit_task success uses storage.write_task_if_unchanged on the CAS path."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated="2026-01-01T10:00:00+00:00")
        cv = _make_cockpit_view(kanban_dir)
        stale_error = ConcurrencyError("ERR_STALE", "CAS intercepted by spy")

        with (
            mock.patch(
                "owlbear_kanban.storage.write_task_if_unchanged",
                side_effect=stale_error,
            ) as mock_cas,
            pytest.raises(ConcurrencyError),
        ):
            cv.edit_task(
                1,
                expected_updated="2026-01-01T10:00:00+00:00",
                append_body="note",
            )

        mock_cas.assert_called_once()

    def test_move_task_signature_has_expected_updated_param(self, tmp_path: Path) -> None:
        """CockpitView.move_task declares required expected_updated."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        sig = inspect.signature(cv.move_task)
        assert "expected_updated" in sig.parameters, "CockpitView.move_task must require expected_updated"

    def test_move_task_expected_updated_is_required_no_default(self, tmp_path: Path) -> None:
        """CockpitView.move_task.expected_updated has no default."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        sig = inspect.signature(cv.move_task)
        param = sig.parameters.get("expected_updated")
        assert param is not None, "expected_updated param missing"
        assert param.default is inspect.Parameter.empty, "CockpitView.move_task.expected_updated must be required"

    def test_move_task_stale_expected_updated_raises_concurrency_error(self, tmp_path: Path) -> None:
        """move_task with a stale OCC token raises ERR_STALE."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated="2026-01-01T10:00:00+00:00")
        cv = _make_cockpit_view(kanban_dir)

        with pytest.raises(ConcurrencyError) as exc_info:
            cv.move_task(
                1,
                "backlog",
                expected_updated="2025-01-01T00:00:00+00:00",
            )

        assert exc_info.value.code == "ERR_STALE"

    def test_move_task_matching_expected_updated_returns_single_task_response(self, tmp_path: Path) -> None:
        """move_task with a fresh OCC token returns SingleTaskResponse."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated="2026-01-01T10:00:00+00:00")
        cv = _make_cockpit_view(kanban_dir)

        result = cv.move_task(
            1,
            "backlog",
            expected_updated="2026-01-01T10:00:00+00:00",
        )

        assert isinstance(result, SingleTaskResponse)

    def test_move_task_success_path_routes_through_write_task_if_unchanged(self, tmp_path: Path) -> None:
        """move_task success uses storage.write_task_if_unchanged on the CAS path."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated="2026-01-01T10:00:00+00:00")
        cv = _make_cockpit_view(kanban_dir)
        stale_error = ConcurrencyError("ERR_STALE", "CAS intercepted by spy")

        with (
            mock.patch(
                "owlbear_kanban.storage.write_task_if_unchanged",
                side_effect=stale_error,
            ) as mock_cas,
            pytest.raises(ConcurrencyError),
        ):
            cv.move_task(
                1,
                "backlog",
                expected_updated="2026-01-01T10:00:00+00:00",
            )

        mock_cas.assert_called_once()


# ---------------------------------------------------------------------------
# Title parameter contract
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewEditTaskTitle:
    """CockpitView.edit_task title parameter contract."""

    def test_edit_task_signature_has_title_param(self, tmp_path: Path) -> None:
        """CockpitView.edit_task exposes a title keyword parameter."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        sig = inspect.signature(cv.edit_task)
        assert "title" in sig.parameters, "CockpitView.edit_task must accept a title parameter"

    def test_edit_task_title_param_default_is_none(self, tmp_path: Path) -> None:
        """The title parameter defaults to None."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        sig = inspect.signature(cv.edit_task)
        param = sig.parameters.get("title")
        assert param is not None, "title param missing from CockpitView.edit_task"
        assert param.default is None, "CockpitView.edit_task title must default to None"

    def test_edit_task_with_title_updates_task_title(self, tmp_path: Path) -> None:
        """Supplying title updates the underlying task title."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            1,
            title="Original Title",
            updated="2026-01-01T10:00:00+00:00",
        )
        cv = _make_cockpit_view(kanban_dir)

        result = cv.edit_task(
            1,
            expected_updated="2026-01-01T10:00:00+00:00",
            title="New Title",
        )

        assert isinstance(result, SingleTaskResponse)
        assert result.title == "New Title"

    def test_edit_task_title_none_preserves_original_title(self, tmp_path: Path) -> None:
        """Passing title=None preserves the existing title."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            1,
            title="Original Title",
            updated="2026-01-01T10:00:00+00:00",
        )
        cv = _make_cockpit_view(kanban_dir)

        result = cv.edit_task(
            1,
            expected_updated="2026-01-01T10:00:00+00:00",
            title=None,
            append_body="minor note",
        )

        assert isinstance(result, SingleTaskResponse)
        assert result.title == "Original Title"

    def test_edit_task_title_is_keyword_only(self, tmp_path: Path) -> None:
        """The title parameter remains keyword-only."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        sig = inspect.signature(cv.edit_task)
        param = sig.parameters.get("title")
        assert param is not None, "title param missing"
        assert param.kind in {
            inspect.Parameter.KEYWORD_ONLY,
            inspect.Parameter.VAR_KEYWORD,
        }, f"CockpitView.edit_task title must be keyword-only, got {param.kind}"


# ---------------------------------------------------------------------------
# Sweep contracts
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewSweep:
    """CockpitView.sweep regression coverage."""

    def test_sweep_returns_exactly_the_expired_task_ids_no_extras_and_no_missing(self, tmp_path: Path) -> None:
        """sweep returns exactly the expired claim IDs and nothing else."""
        kanban_dir = _make_board(tmp_path)
        expired_ts = (datetime.now(tz=UTC) - timedelta(hours=2)).isoformat()
        fresh_ts = (datetime.now(tz=UTC) - timedelta(minutes=1)).isoformat()
        _write_task(kanban_dir, 1, claimed_at=f'"{expired_ts}"')
        _write_task(kanban_dir, 2, title="Task Two", claimed_at=f'"{fresh_ts}"')
        _write_task(kanban_dir, 3, title="Task Three", claimed_at="null")
        cv = _make_cockpit_view(kanban_dir)

        released = cv.sweep()

        assert set(released) == {1}

    def test_sweep_cas_stale_task_skipped_no_error_raised(self, tmp_path: Path) -> None:
        """CAS ERR_STALE causes sweep to skip the task without mutating disk or logs."""
        kanban_dir = _make_board(tmp_path)
        expired_ts = (datetime.now(tz=UTC) - timedelta(hours=2)).isoformat()
        task_path = _write_task(kanban_dir, 1, claimed_at=f'"{expired_ts}"')
        cv = _make_cockpit_view(kanban_dir)
        stale_error = ConcurrencyError("ERR_STALE", "Task modified concurrently")

        with mock.patch(
            "owlbear_kanban.storage.write_task_if_unchanged",
            side_effect=stale_error,
        ) as mock_cas:
            released = cv.sweep()

        mock_cas.assert_called_once()
        assert 1 not in released
        raw = task_path.read_text(encoding="utf-8")
        assert "claimed_at: null" not in raw
        sweep_events = cv.list_activity(task_id=1, action="sweep-release")
        assert sweep_events == []

    def test_sweep_cas_stale_task_skipped_and_later_eligible_task_still_released(self, tmp_path: Path) -> None:
        """sweep continues after ERR_STALE and still releases later eligible tasks."""
        kanban_dir = _make_board(tmp_path)
        expired_ts = (datetime.now(tz=UTC) - timedelta(hours=2)).isoformat()
        _write_task(kanban_dir, 1, claimed_at=f'"{expired_ts}"')
        _write_task(kanban_dir, 2, title="Task Two", claimed_at=f'"{expired_ts}"')
        cv = _make_cockpit_view(kanban_dir)
        stale_error = ConcurrencyError("ERR_STALE", "Task modified concurrently")

        with mock.patch(
            "owlbear_kanban.storage.write_task_if_unchanged",
            side_effect=[stale_error, None],
        ) as mock_cas:
            released = cv.sweep()

        assert mock_cas.call_count == 2
        assert 1 not in released
        assert 2 in released


# ---------------------------------------------------------------------------
# Activity/session reads
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewListActivity:
    """CockpitView.list_activity filter behavior."""

    def _board_with_events(self, tmp_path: Path) -> tuple[Path, CockpitView]:
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1)
        _write_task(kanban_dir, 2, title="Task Two")
        _write_activity_event(
            kanban_dir,
            task_id=1,
            action="start_work",
            source="agent",
            detail="claimed",
            timestamp="2026-01-01T10:00:00+00:00",
        )
        _write_activity_event(
            kanban_dir,
            task_id=1,
            action="end_work",
            source="agent",
            detail="success",
            timestamp="2026-01-01T11:00:00+00:00",
        )
        _write_activity_event(
            kanban_dir,
            task_id=2,
            action="start_work",
            source="agent",
            detail="claimed",
            timestamp="2026-01-01T12:00:00+00:00",
        )
        _write_activity_event(
            kanban_dir,
            task_id=2,
            action="release",
            source="cockpit",
            detail="released by admin",
            timestamp="2026-01-01T13:00:00+00:00",
        )
        return kanban_dir, _make_cockpit_view(kanban_dir)

    def test_list_activity_filter_by_source(self, tmp_path: Path) -> None:
        """source='cockpit' returns only cockpit-sourced events."""
        _, cv = self._board_with_events(tmp_path)
        events = cv.list_activity(source="cockpit")
        assert len(events) == 1
        assert events[0].source == "cockpit"

    def test_list_activity_since_returns_only_events_within_window_exact_identity(self, tmp_path: Path) -> None:
        """since filter preserves exact task/action identity, not just event count."""
        _, cv = self._board_with_events(tmp_path)
        events = cv.list_activity(since="2026-01-01T12:00:00+00:00")
        assert len(events) == 2
        task_ids = {event.task_id for event in events}
        actions = {event.action for event in events}
        assert task_ids == {2}
        assert actions == {"start_work", "release"}

    def test_list_activity_until_returns_only_events_within_window_exact_identity(self, tmp_path: Path) -> None:
        """until filter preserves exact task/action identity, not just event count."""
        _, cv = self._board_with_events(tmp_path)
        events = cv.list_activity(until="2026-01-01T11:00:00+00:00")
        assert len(events) == 2
        task_ids = {event.task_id for event in events}
        actions = {event.action for event in events}
        assert task_ids == {1}
        assert actions == {"start_work", "end_work"}

    def test_list_activity_on_empty_log_returns_empty_list(self, tmp_path: Path) -> None:
        """Boards with no activity log produce an empty list."""
        kanban_dir = _make_board(tmp_path)
        cv = _make_cockpit_view(kanban_dir)
        assert cv.list_activity() == []


class TestFromAC_CockpitViewListSessions:
    """CockpitView.list_sessions facade behavior."""

    def _board_with_completed_session(self, tmp_path: Path) -> tuple[Path, CockpitView]:
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1)
        _write_activity_event(
            kanban_dir,
            task_id=1,
            action="start_work",
            source="agent",
            detail="claimed",
            timestamp="2026-01-01T10:00:00+00:00",
        )
        _write_activity_event(
            kanban_dir,
            task_id=1,
            action="end_work",
            source="agent",
            detail="success: research -> backlog",
            timestamp="2026-01-01T11:00:00+00:00",
        )
        return kanban_dir, _make_cockpit_view(kanban_dir)

    def test_list_sessions_returns_list_of_session_records(self, tmp_path: Path) -> None:
        """list_sessions returns list[SessionRecord]."""
        _, cv = self._board_with_completed_session(tmp_path)
        sessions = cv.list_sessions()
        assert isinstance(sessions, list)
        assert all(isinstance(session, SessionRecord) for session in sessions)

    def test_list_sessions_filter_released_returns_release_outcome_sessions(self, tmp_path: Path) -> None:
        """filter='released' returns release sessions with released state."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1)
        _write_activity_event(
            kanban_dir,
            task_id=1,
            action="start_work",
            source="agent",
            detail="claimed",
            timestamp="2026-01-01T10:00:00+00:00",
        )
        _write_activity_event(
            kanban_dir,
            task_id=1,
            action="release",
            source="cockpit",
            detail="released by admin",
            timestamp="2026-01-01T11:00:00+00:00",
        )
        cv = _make_cockpit_view(kanban_dir)

        sessions = cv.list_sessions(filter="released")

        assert len(sessions) == 1
        assert sessions[0].outcome == "release"
        assert sessions[0].state == "released"

    def test_list_sessions_canonical_claim_action_opens_session(self, tmp_path: Path) -> None:
        """Canonical claim events open running sessions."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1)
        fresh_ts = (datetime.now(tz=UTC) - timedelta(minutes=5)).isoformat()
        _write_activity_event(
            kanban_dir,
            task_id=1,
            action="claim",
            source="agent",
            detail="claimed",
            timestamp=fresh_ts,
        )
        cv = _make_cockpit_view(kanban_dir)

        sessions = cv.list_sessions(filter="active")
        active = [session for session in sessions if session.task_id == 1]

        assert len(active) == 1
        assert active[0].state == "running"

    def test_list_sessions_canonical_blocked_colon_detail_creates_blocked_session(self, tmp_path: Path) -> None:
        """Canonical 'blocked: ...' detail yields blocked state."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1)
        _write_activity_event(
            kanban_dir,
            task_id=1,
            action="claim",
            source="agent",
            detail="claimed",
            timestamp="2026-01-01T10:00:00+00:00",
        )
        _write_activity_event(
            kanban_dir,
            task_id=1,
            action="end_work",
            source="agent",
            detail="blocked: needs external clarification",
            timestamp="2026-01-01T11:00:00+00:00",
        )
        cv = _make_cockpit_view(kanban_dir)

        sessions = cv.list_sessions(filter="blocked-or-rejected")
        blocked = [session for session in sessions if session.task_id == 1]

        assert len(blocked) == 1
        assert blocked[0].state == "blocked"

    def test_list_sessions_canonical_outcome_fail_detail_creates_blocked_session(self, tmp_path: Path) -> None:
        """Canonical outcome=fail detail yields blocked state with fail outcome."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1)
        _write_activity_event(
            kanban_dir,
            task_id=1,
            action="claim",
            source="agent",
            detail="claimed",
            timestamp="2026-01-01T10:00:00+00:00",
        )
        _write_activity_event(
            kanban_dir,
            task_id=1,
            action="end_work",
            source="agent",
            detail="outcome=fail",
            timestamp="2026-01-01T11:00:00+00:00",
        )
        cv = _make_cockpit_view(kanban_dir)

        sessions = cv.list_sessions(filter="blocked-or-rejected")
        blocked = [session for session in sessions if session.task_id == 1]

        assert len(blocked) == 1
        assert blocked[0].state == "blocked"
        assert blocked[0].outcome == "fail"


# ---------------------------------------------------------------------------
# Admin operations
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewScanCorruption:
    """scan_corruption read-only guarantees."""

    def test_scan_corruption_clean_board_returns_empty_list(self, tmp_path: Path) -> None:
        """Clean boards produce no corruption records."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1)
        cv = _make_cockpit_view(kanban_dir)
        assert cv.scan_corruption() == []

    def test_scan_corruption_with_corrupt_file_returns_corruption_errors(self, tmp_path: Path) -> None:
        """Corrupt task files return CorruptionError instances."""
        kanban_dir = _make_board(tmp_path)
        (kanban_dir / "tasks" / "99-corrupt.md").write_text(
            "no yaml frontmatter here at all",
            encoding="utf-8",
        )
        cv = _make_cockpit_view(kanban_dir)
        result = cv.scan_corruption()
        assert len(result) >= 1
        assert all(isinstance(item, CorruptionError) for item in result)

    def test_scan_corruption_checks_archive_directory(self, tmp_path: Path) -> None:
        """scan_corruption scans archive/ as well as tasks/."""
        kanban_dir = _make_board(tmp_path)
        (kanban_dir / "archive" / "88-archive-corrupt.md").write_text(
            "not valid frontmatter",
            encoding="utf-8",
        )
        cv = _make_cockpit_view(kanban_dir)
        result = cv.scan_corruption()
        assert len(result) >= 1

    def test_scan_corruption_does_not_mutate_corrupt_file_contents(self, tmp_path: Path) -> None:
        """scan_corruption never rewrites corrupt files in place."""
        kanban_dir = _make_board(tmp_path)
        corrupt_content = b"no yaml frontmatter here at all"
        corrupt_path = kanban_dir / "tasks" / "99-corrupt.md"
        corrupt_path.write_bytes(corrupt_content)
        cv = _make_cockpit_view(kanban_dir)
        cv.scan_corruption()
        assert corrupt_path.exists()
        assert corrupt_path.read_bytes() == corrupt_content


class TestFromAC_CockpitViewRepairStorage:
    """repair_storage contracts preserved from the archived CockpitView suite."""

    def test_repair_storage_returns_list_of_repair_outcomes(self, tmp_path: Path) -> None:
        """repair_storage returns list[RepairOutcome]."""
        kanban_dir = _make_board(tmp_path)
        cv = _make_cockpit_view(kanban_dir)
        result = cv.repair_storage()
        assert isinstance(result, list)
        assert all(isinstance(item, RepairOutcome) for item in result)

    def test_repair_storage_phase1_quarantines_corrupt_file(self, tmp_path: Path) -> None:
        """repair_storage phase 1 calls scan_and_fix and quarantines corrupt files."""
        from owlbear_kanban.corruption import scan_and_fix as real_scan_and_fix  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        (kanban_dir / "tasks" / "99-corrupt.md").write_text(
            "no yaml here",
            encoding="utf-8",
        )
        cv = _make_cockpit_view(kanban_dir)

        with mock.patch(
            "owlbear_kanban.corruption.scan_and_fix",
            wraps=real_scan_and_fix,
        ) as mock_scan_and_fix:
            outcomes = cv.repair_storage()

        mock_scan_and_fix.assert_called_once()
        assert mock_scan_and_fix.call_args[0][0] == kanban_dir
        quarantined = [outcome for outcome in outcomes if outcome.action == "quarantined"]
        assert len(quarantined) >= 1

    def test_repair_storage_phase2_ar_creation_uses_engine_create_task_method(self, tmp_path: Path) -> None:
        """repair_storage phase 2 creates the follow-up AR task via engine.create_task."""
        kanban_dir = _make_board(tmp_path)
        (kanban_dir / "tasks" / "99-corrupt.md").write_text(
            "no yaml here",
            encoding="utf-8",
        )
        engine = KanbanEngine(kanban_dir)
        cv = CockpitView(engine)
        original_create_task = KanbanEngine.create_task

        with mock.patch.object(
            KanbanEngine,
            "create_task",
            wraps=original_create_task,
        ) as mock_create:
            outcomes = cv.repair_storage()

        quarantined = [outcome for outcome in outcomes if outcome.action == "quarantined"]
        assert len(quarantined) >= 1
        mock_create.assert_called_once()
        assert "type:user-action" in mock_create.call_args.kwargs.get("tags", [])

    def test_repair_storage_not_called_implicitly_at_engine_startup(self, tmp_path: Path) -> None:
        """KanbanEngine.__init__ never auto-runs repair_storage."""
        kanban_dir = _make_board(tmp_path)
        corrupt_path = kanban_dir / "tasks" / "99-corrupt.md"
        corrupt_path.write_text("no yaml here", encoding="utf-8")

        _ = KanbanEngine(kanban_dir)
        assert corrupt_path.exists()

        cv = CockpitView(KanbanEngine(kanban_dir))
        assert hasattr(cv, "repair_storage")
        cv.repair_storage()
        quarantine_dir = kanban_dir / "quarantine"
        assert quarantine_dir.exists()


class TestFromAC_CockpitViewCompactActivity:
    """compact_activity delegation and empty-log behavior."""

    def test_compact_activity_delegates_to_storage_compact_activity_log(self, tmp_path: Path) -> None:
        """compact_activity delegates to storage.compact_activity_log."""
        kanban_dir = _make_board(tmp_path)
        cv = _make_cockpit_view(kanban_dir)

        with mock.patch("owlbear_kanban.engine.compact_activity_log") as mock_compact:
            mock_compact.return_value = ActivityCompactionResult(
                before_bytes=0,
                after_bytes=0,
                records_compacted=0,
            )
            cv.compact_activity()

        mock_compact.assert_called_once()

    def test_compact_activity_on_board_with_no_log_does_not_raise(self, tmp_path: Path) -> None:
        """Boards without activity.jsonl still return ActivityCompactionResult."""
        kanban_dir = _make_board(tmp_path)
        cv = _make_cockpit_view(kanban_dir)
        result = cv.compact_activity()
        assert isinstance(result, ActivityCompactionResult)


# ---------------------------------------------------------------------------
# Role separation and activity sources
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewRoleSeparation:
    """CockpitView exposes admin APIs and not agent-only operations."""

    def test_cockpit_view_exposes_all_required_admin_methods(self, tmp_path: Path) -> None:
        """CockpitView exposes sweep, scan_corruption, repair_storage, compact_activity, list reads."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        required_admin = {
            "sweep",
            "scan_corruption",
            "repair_storage",
            "compact_activity",
            "list_activity",
            "list_sessions",
        }
        missing = {name for name in required_admin if not hasattr(cv, name)}
        assert not missing, f"Missing required admin methods on CockpitView: {missing}"

    def test_cockpit_view_does_not_expose_create_task(self, tmp_path: Path) -> None:
        """create_task remains agent-only."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        assert hasattr(cv, "sweep")
        assert not hasattr(cv, "create_task")

    def test_cockpit_view_does_not_expose_start_work(self, tmp_path: Path) -> None:
        """start_work remains agent-only."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        assert hasattr(cv, "sweep")
        assert not hasattr(cv, "start_work")

    def test_cockpit_view_does_not_expose_end_work(self, tmp_path: Path) -> None:
        """end_work remains agent-only."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        assert hasattr(cv, "compact_activity")
        assert not hasattr(cv, "end_work")

    def test_cockpit_view_does_not_expose_pick_tasks(self, tmp_path: Path) -> None:
        """pick_tasks remains agent-only."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        assert hasattr(cv, "list_activity")
        assert not hasattr(cv, "pick_tasks")


class TestFromAC_ActivityEventSource:
    """ActivityEvent.source values emitted through CockpitView operations."""

    def test_cockpit_view_mutation_emits_source_cockpit(self, tmp_path: Path) -> None:
        """CockpitView.release_task emits release events with source='cockpit'."""
        from owlbear_kanban.activity_store import list_activity_events  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, claimed_at='"2026-01-01T09:00:00+00:00"')
        cv = _make_cockpit_view(kanban_dir)

        cv.release_task(1, expected_updated="2026-01-01T10:00:00+00:00")

        events = list_activity_events(kanban_dir, action="release", task_id=1)
        assert len(events) == 1
        assert events[0].source == "cockpit"

    def test_sweep_operation_emits_source_engine(self, tmp_path: Path) -> None:
        """sweep emits sweep-release events with source='engine'."""
        from owlbear_kanban.activity_store import list_activity_events  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        expired_ts = (datetime.now(tz=UTC) - timedelta(hours=2)).isoformat()
        _write_task(kanban_dir, 1, claimed_at=f'"{expired_ts}"')
        cv = _make_cockpit_view(kanban_dir)

        cv.sweep()

        events = list_activity_events(kanban_dir, action="sweep-release", task_id=1)
        assert len(events) == 1
        assert events[0].source == "engine"

    def test_cockpit_view_edit_task_emits_source_cockpit(self, tmp_path: Path) -> None:
        """CockpitView.edit_task emits edit events with source='cockpit'."""
        from owlbear_kanban.activity_store import list_activity_events  # noqa: PLC0415

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
