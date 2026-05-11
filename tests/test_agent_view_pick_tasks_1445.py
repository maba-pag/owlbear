"""Tests: pick_tasks is read-only; expired-claim tasks dispatched (task #1445).

AC-1 (td:1): pick_tasks returns waves without calling resolve_pending_drs or
             any write helper.
AC-2 (td:2): Unblocked backlog task with expired claimed_at appears in a wave
             and claimed_at is left unchanged on disk.
AC-3 (td:1): Pending DR with response=approved stays in decisions/pending;
             linked task body and blocked field are unchanged.

All tests must FAIL against the current implementation and pass once the
builder removes the resolve_pending_drs call and switches to local
_claim_is_active filtering.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import PickTasksResponse

# ---------------------------------------------------------------------------
# Board / task helpers
# ---------------------------------------------------------------------------

_BASE_CONFIG = """
next_id: 1
"""

_TASK_TMPL = """\
---
id: {task_id}
title: {title}
status: {status}
priority: {priority}
created: "2026-01-15T10:00:00+00:00"
updated: "2026-04-01T12:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: {blocked}
block_reason: null
claimed_at: {claimed_at}
archival_reason: null
archival_refs: []
---
Body text.
"""

# DR frontmatter — minimal set required by resolve_pending_drs / parse_dr
_DR_TMPL = """\
---
task_id: {task_id}
response: {response}
created: '2026-05-01'
---

Decision request body.
"""

# Timestamps — always expired (far in the past)
_EXPIRED_TS = '"2020-01-01T00:00:00+00:00"'


def _make_board(base_dir: Path) -> Path:
    board = base_dir / "board"
    board.mkdir(parents=True, exist_ok=True)
    (board / "config.yml").write_text(_BASE_CONFIG, encoding="utf-8")
    (board / "tasks").mkdir(exist_ok=True)
    (board / "archive").mkdir(exist_ok=True)
    return board


def _write_task(  # noqa: PLR0913
    board: Path,
    task_id: int = 1,
    title: str = "Task",
    status: str = "backlog",
    priority: str = "needed",
    blocked: str = "false",
    claimed_at: str = "null",
) -> Path:
    content = _TASK_TMPL.format(
        task_id=task_id,
        title=title,
        status=status,
        priority=priority,
        blocked=blocked,
        claimed_at=claimed_at,
    )
    path = board / "tasks" / f"{task_id}-task.md"
    path.write_text(content, encoding="utf-8")
    return path


def _all_ids(resp: PickTasksResponse) -> set[int]:
    return {entry.id for wave in resp.waves for entry in wave.tasks}


def _stub_decisions_module() -> MagicMock:
    """Return a mock decisions module that records calls and returns []."""
    mock = MagicMock()
    mock.resolve_pending_drs.return_value = []
    return mock


# ---------------------------------------------------------------------------
# AC-1 (td:1): pick_tasks must NOT call resolve_pending_drs
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksReadOnly:
    """AC-1: pick_tasks returns dispatch waves without calling resolve_pending_drs."""

    def test_resolve_pending_drs_not_called(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """pick_tasks must NOT call decisions.resolve_pending_drs.

        Injects a mock owlbear_kanban.decisions module via sys.modules and
        asserts that resolve_pending_drs is never invoked during pick_tasks.

        FAILS today because the current pick_tasks implementation imports and
        calls decisions.resolve_pending_drs at lines 384-391 of agent_view.py.
        """
        decisions_mock = _stub_decisions_module()
        monkeypatch.setitem(sys.modules, "owlbear_kanban.decisions", decisions_mock)

        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="backlog")
        engine = KanbanEngine(board, activity_log=False)

        engine.agent_view().pick_tasks()

        decisions_mock.resolve_pending_drs.assert_not_called()

    def test_no_engine_write_methods_called(self, tmp_path: Path) -> None:
        """AC-1 discriminating sentinel: pick_tasks must NOT call sweep, repair_storage,
        edit_task, or move_task on the engine.

        Patches each named write method on the live engine instance (without wraps)
        so any invocation would be captured.  The read path (list_tasks, show_task)
        remains unpatched.

        Proves the reviewer gap: current proof only pinned resolve_pending_drs;
        this test fails the moment any of the other named helpers is introduced.
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="backlog")
        engine = KanbanEngine(board, activity_log=False)
        av = engine.agent_view()

        with (
            patch.object(engine, "sweep") as mock_sweep,
            patch.object(engine, "repair_storage") as mock_repair,
            patch.object(engine, "edit_task") as mock_edit,
            patch.object(engine, "move_task") as mock_move,
            patch("owlbear_kanban.storage.write_task") as mock_write_task,
        ):
            av.pick_tasks()

        mock_sweep.assert_not_called()
        mock_repair.assert_not_called()
        mock_edit.assert_not_called()
        mock_move.assert_not_called()
        mock_write_task.assert_not_called()


# ---------------------------------------------------------------------------
# AC-2 (td:2): expired-claim task is dispatched; claimed_at unchanged on disk
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksExpiredClaim:
    """AC-2: unblocked backlog task with expired claimed_at appears in waves
    and claimed_at is left unchanged on disk after pick_tasks returns."""

    def test_expired_claim_task_included_in_waves(self, tmp_path: Path) -> None:
        """Happy path: task with claimed_at far in the past appears in a wave.

        FAILS today because list_tasks(unclaimed=True) excludes every task
        that has a non-null claimed_at, regardless of whether the claim is
        expired.  The task therefore never enters the dispatch pipeline.
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="backlog", claimed_at=_EXPIRED_TS)
        engine = KanbanEngine(board, activity_log=False)

        resp = engine.agent_view().pick_tasks()

        assert 1 in _all_ids(resp), (
            "Task with expired claimed_at must appear in dispatch waves"
        )

    def test_expired_claim_claimed_at_unchanged_on_disk(self, tmp_path: Path) -> None:
        """pick_tasks must leave claimed_at unchanged for expired-claim tasks.

        Asserts both that the task appears in waves AND that the file on disk
        still carries the original expired timestamp — i.e. pick_tasks did not
        write to the task file.

        FAILS today on the first assertion (expired tasks excluded by current
        list_tasks(unclaimed=True) call).
        """
        expired_ts_raw = "2020-01-01T00:00:00+00:00"
        board = _make_board(tmp_path)
        task_path = _write_task(
            board, task_id=2, status="backlog", claimed_at=f'"{expired_ts_raw}"'
        )
        engine = KanbanEngine(board, activity_log=False)

        resp = engine.agent_view().pick_tasks()

        # 1. Task must appear in waves
        assert 2 in _all_ids(resp), "Expired-claim task must be dispatched"
        # 2. claimed_at must be unchanged on disk — exact field comparison via frontmatter
        raw = task_path.read_text(encoding="utf-8")
        parts = raw.split("---")
        frontmatter = yaml.safe_load(parts[1])
        assert frontmatter["claimed_at"] == expired_ts_raw, (
            "claimed_at field must remain exactly unchanged on disk after pick_tasks"
        )

    def test_claim_just_expired_beyond_timeout_included(self, tmp_path: Path) -> None:
        """Boundary: a claim expired exactly 1 second beyond claim_timeout is dispatched.

        Default claim_timeout is 1h.  A task claimed (1h + 1s) ago must be
        considered expired and returned in a wave.

        FAILS today: the unclaimed=True filter excludes any non-null claimed_at.
        """
        just_expired = datetime.now(UTC) - timedelta(hours=1, seconds=1)
        just_expired_quoted = f'"{just_expired.isoformat()}"'

        board = _make_board(tmp_path)
        _write_task(board, task_id=3, status="backlog", claimed_at=just_expired_quoted)
        engine = KanbanEngine(board, activity_log=False)

        resp = engine.agent_view().pick_tasks()

        assert 3 in _all_ids(resp), (
            "Claim expired 1 second beyond the 1h timeout must be treated as expired "
            "and dispatched"
        )

    def test_multiple_expired_claim_tasks_all_dispatched(self, tmp_path: Path) -> None:
        """Edge: all tasks with expired claims are included in waves.

        Verifies there is no per-task short-circuit that would stop processing
        after the first expired-claim task.

        FAILS today: all are excluded by list_tasks(unclaimed=True).
        """
        board = _make_board(tmp_path)
        for tid in (4, 5, 6):
            _write_task(board, task_id=tid, status="backlog", claimed_at=_EXPIRED_TS)
        engine = KanbanEngine(board, activity_log=False)

        resp = engine.agent_view().pick_tasks()

        returned = _all_ids(resp)
        assert {4, 5, 6}.issubset(returned), (
            "All tasks with expired claimed_at must appear in dispatch waves"
        )

    def test_expired_claim_respects_configured_timeout(self, tmp_path: Path) -> None:
        """AC-2 discriminating proof: expired-claim eligibility uses the configured
        claim_timeout, not a hardcoded 1-hour constant.

        Sets engine._config.pipeline.claim_timeout to '5m' so the real
        _parse_duration runs with the configured value.  A task claimed 6
        minutes ago is expired under 5 min but would still be active under the
        default 1h timeout.  The task must appear in waves, proving pick_tasks
        reads from config rather than using a literal timedelta(hours=1).
        """
        six_minutes_ago = datetime.now(UTC) - timedelta(minutes=6)
        board = _make_board(tmp_path)
        _write_task(
            board,
            task_id=20,
            status="backlog",
            claimed_at=f'"{six_minutes_ago.isoformat()}"',
        )
        engine = KanbanEngine(board, activity_log=False)
        engine._config.pipeline.claim_timeout = "5m"

        resp = engine.agent_view().pick_tasks()

        assert 20 in _all_ids(resp), (
            "Task claimed 6 minutes ago must be dispatched when claim_timeout is "
            "5 minutes; fails if pick_tasks hardcodes 1h instead of reading "
            "config.pipeline.claim_timeout"
        )


# ---------------------------------------------------------------------------
# AC-3 (td:1): pending DR with approved response is not processed by pick_tasks
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksDRImmutability:
    """AC-3: pick_tasks leaves decisions/pending files and linked tasks unchanged."""

    def test_approved_dr_stays_in_pending_directory(self, tmp_path: Path) -> None:
        """DR with response=approved must remain in decisions/pending after pick_tasks.

        FAILS today because pick_tasks calls the real resolve_pending_drs, which
        moves approved DR files from decisions/pending/ to decisions/resolved/ and
        calls edit_task to clear the linked task's blocked flag.
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, blocked="true", claimed_at="null")

        pending_dir = board / "decisions" / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)
        dr_path = pending_dir / "0001-dr.md"
        dr_path.write_text(
            _DR_TMPL.format(task_id=1, response="approved"), encoding="utf-8"
        )

        engine = KanbanEngine(board, activity_log=False)
        engine.agent_view().pick_tasks()

        assert dr_path.exists(), (
            "Approved DR file must remain in decisions/pending after pick_tasks; "
            "pick_tasks must not call resolve_pending_drs"
        )
        resolved_path = board / "decisions" / "resolved" / "0001-dr.md"
        assert not resolved_path.exists(), (
            "DR must NOT be moved to decisions/resolved by pick_tasks"
        )

    def test_linked_task_not_modified_by_pick_tasks(self, tmp_path: Path) -> None:
        """Linked task body and blocked field must be unchanged after pick_tasks.

        FAILS today because resolve_pending_drs (called inside pick_tasks) appends
        a summary to the task body and calls edit_task(task_id, blocked=False),
        changing the blocked field and the body content.
        """
        board = _make_board(tmp_path)
        task_path = _write_task(board, task_id=2, blocked="true", claimed_at="null")

        pending_dir = board / "decisions" / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)
        (pending_dir / "0002-dr.md").write_text(
            _DR_TMPL.format(task_id=2, response="approved"), encoding="utf-8"
        )

        engine = KanbanEngine(board, activity_log=False)
        engine.agent_view().pick_tasks()

        final_content = task_path.read_text(encoding="utf-8")
        # blocked=true must be unchanged (resolve_pending_drs would have set it to false)
        assert "blocked: true" in final_content, (
            "Task blocked=true must remain unchanged after pick_tasks"
        )
        # No DR summary section must have been appended
        assert "## Decision Request" not in final_content, (
            "Task body must not contain an appended DR summary after pick_tasks"
        )
