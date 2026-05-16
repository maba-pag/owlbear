"""RED-phase failing tests for #1526: dep-status guidance in start_work (AC1-AC3).

AC coverage:
  AC1 → TestFromAC_DepGuidanceBlocked — start_work() on dep-blocked task emits
         guidance string containing dep IDs and confirmation prompt.
  AC2 → TestFromAC_DepGuidanceNoDeps — start_work() on task with no/resolved deps
         returns guidance == [].
  AC3 → TestFromAC_DepGuidanceResilience — dep lookup exceptions (FileNotFoundError,
         CorruptionError, ValueError, KeyError) silently skipped, no crash.

RED-phase note:
  AC1 tests FAIL against current code — start_work() returns guidance=[] for all tasks.
  AC2/AC3 tests pass trivially: start_work() has no dep lookup so absent files and
  mocked exceptions are never triggered.  These are kept as regression/resilience guards
  per AC spec; they catch implementation bugs that incorrectly emit or surface errors.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from owlbear_kanban import CorruptionError, KanbanEngine
from owlbear_kanban.models import SingleTaskResponse

# ---------------------------------------------------------------------------
# Board + task fixtures
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
schema: grouped
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
next_id: 1
paths:
    tasks_dir: tasks
    archive_dir: archive
pipeline:
    entry_status: research
    terminal_status: done
    wave_size: 4
    claim_timeout: 1h
agents:
    agent_map:
        research: researcher
        backlog: architect
        todo: builder
        in-progress: builder
        review: reviewer
        done: auditor
    agent_types: {}
    agent_compatibility: {}
policy:
    non_impl_tags: [research, docs]
    archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
    status_predicates: {}
"""

_TASK_TMPL = """\
---
id: {task_id}
title: {title}
status: {status}
priority: needed
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: []
parent: null
depends_on: {depends_on}
blocked: false
block_reason: null
claimed_at: null
archival_reason: null
archival_refs: []
---
Body.
"""

_ARCHIVE_TMPL = """\
---
id: {task_id}
title: Archived Task
status: archived
priority: needed
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: {archival_reason}
archival_refs: []
---
Archived body.
"""


def _make_board(base_dir: Path) -> Path:
    board = base_dir / "board"
    board.mkdir(parents=True, exist_ok=True)
    (board / "config.yml").write_text(_BASE_CONFIG, encoding="utf-8")
    (board / "tasks").mkdir(exist_ok=True)
    (board / "archive").mkdir(exist_ok=True)
    return board


def _write_task(
    board: Path,
    task_id: int = 1,
    title: str = "Task",
    status: str = "todo",
    depends_on: str = "[]",
) -> Path:
    content = _TASK_TMPL.format(
        task_id=task_id,
        title=title,
        status=status,
        depends_on=depends_on,
    )
    path = board / "tasks" / f"{task_id}-task.md"
    path.write_text(content, encoding="utf-8")
    return path


def _write_archived_task(
    board: Path,
    task_id: int,
    archival_reason: str = "completed",
) -> Path:
    content = _ARCHIVE_TMPL.format(
        task_id=task_id,
        archival_reason=archival_reason,
    )
    path = board / "archive" / f"{task_id}-archived.md"
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# AC1: dep-blocked task → guidance string  [FAILING in RED phase]
# ---------------------------------------------------------------------------


class TestFromAC_DepGuidanceBlocked:
    """AC1: start_work() on dep-blocked task returns guidance with dep IDs.

    Current behaviour: guidance is always [].  These tests FAIL until the
    dep-lookup feature is implemented in agent_view.start_work().
    """

    def test_single_blocked_dep_guidance_has_one_item(self, tmp_path: Path) -> None:
        """Single active dep → exactly one guidance string (not empty list)."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[99]")
        _write_task(board, task_id=99, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().start_work(1)
        assert len(resp.guidance) == 1

    def test_single_blocked_dep_guidance_contains_dep_id(self, tmp_path: Path) -> None:
        """Single active dep → guidance string mentions dep ID 99."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[99]")
        _write_task(board, task_id=99, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().start_work(1)
        assert "99" in resp.guidance[0]

    def test_single_blocked_dep_guidance_exact_format(self, tmp_path: Path) -> None:
        """Guidance string matches exact AC1 format: ⚠️ ... (IDs: 99). Review ..."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[99]")
        _write_task(board, task_id=99, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().start_work(1)
        expected = (
            "⚠️ This task has unresolved dependencies (IDs: 99). "
            "Review and confirm with the user that starting this work is intentional."
        )
        assert resp.guidance[0] == expected

    def test_multiple_blocked_deps_guidance_exact_format(self, tmp_path: Path) -> None:
        """Two active deps → guidance is exactly the AC1 format with comma-separated IDs."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[98, 99]")
        _write_task(board, task_id=98, status="todo")
        _write_task(board, task_id=99, status="in-progress")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().start_work(1)
        expected = (
            "⚠️ This task has unresolved dependencies (IDs: 98, 99). "
            "Review and confirm with the user that starting this work is intentional."
        )
        assert resp.guidance == [expected]


# ---------------------------------------------------------------------------
# AC2: no deps / resolved deps → guidance == []  [regression guards]
# ---------------------------------------------------------------------------


class TestFromAC_DepGuidanceNoDeps:
    """AC2: start_work() on task with no/resolved deps returns guidance == [].

    These tests pass trivially against current code (start_work() always returns
    guidance=[]).  They are kept as regression guards: they will catch bugs where
    the implementation incorrectly emits guidance for non-blocked tasks.
    """

    def test_no_deps_guidance_is_empty_list(self, tmp_path: Path) -> None:
        """Task with no dependencies → guidance == []."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[]")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().start_work(1)
        assert resp.guidance == []

    def test_resolved_dep_archived_completed_guidance_is_empty(self, tmp_path: Path) -> None:
        """Task whose dep is archived/completed → dep resolved, guidance == []."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[99]")
        _write_archived_task(board, task_id=99, archival_reason="completed")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().start_work(1)
        assert resp.guidance == []


# ---------------------------------------------------------------------------
# AC3: dep lookup exceptions silently skipped  [resilience guards]
# ---------------------------------------------------------------------------


class TestFromAC_DepGuidanceResilience:
    """AC3: start_work() silently continues when a dep lookup raises an exception.

    These tests pass trivially against current code (no dep lookup in start_work()).
    After implementation they verify the exception tuple
    (FileNotFoundError, CorruptionError, ValueError, KeyError) is caught and
    the task claim succeeds with guidance == [].
    """

    def test_dep_file_not_found_silently_continues(self, tmp_path: Path) -> None:
        """Dep ID references non-existent file → FileNotFoundError silently skipped."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[99]")
        # task 99 file intentionally absent — triggers FileNotFoundError on dep lookup
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().start_work(1)
        assert isinstance(resp, SingleTaskResponse)
        assert resp.claimed_at is not None
        assert resp.guidance == []

    def test_dep_corruption_error_silently_continues(self, tmp_path: Path) -> None:
        """Dep lookup raising CorruptionError → silently skipped, claim succeeds."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[99]")
        _write_task(board, task_id=99, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        main_task = engine.show_task("1")

        def _side_effect(tid: str) -> object:
            if tid == "99":
                code = "ERR_CORRUPT_YAML_PARSE"
                msg = "malformed yaml"
                raise CorruptionError(code, msg)
            return main_task

        with patch.object(engine, "show_task", side_effect=_side_effect):
            resp = engine.agent_view().start_work(1)
        assert isinstance(resp, SingleTaskResponse)
        assert resp.claimed_at is not None
        assert resp.guidance == []

    def test_dep_value_error_silently_continues(self, tmp_path: Path) -> None:
        """Dep lookup raising ValueError → silently skipped, claim succeeds."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[99]")
        _write_task(board, task_id=99, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        main_task = engine.show_task("1")

        def _side_effect(tid: str) -> object:
            if tid == "99":
                msg = "unexpected value in dep record"
                raise ValueError(msg)
            return main_task

        with patch.object(engine, "show_task", side_effect=_side_effect):
            resp = engine.agent_view().start_work(1)
        assert isinstance(resp, SingleTaskResponse)
        assert resp.claimed_at is not None
        assert resp.guidance == []

    def test_dep_key_error_silently_continues(self, tmp_path: Path) -> None:
        """Dep lookup raising KeyError → silently skipped, claim succeeds."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[99]")
        _write_task(board, task_id=99, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        main_task = engine.show_task("1")

        def _side_effect(tid: str) -> object:
            if tid == "99":
                msg = "missing_field"
                raise KeyError(msg)
            return main_task

        with patch.object(engine, "show_task", side_effect=_side_effect):
            resp = engine.agent_view().start_work(1)
        assert isinstance(resp, SingleTaskResponse)
        assert resp.claimed_at is not None
        assert resp.guidance == []

    def test_mixed_dep_one_fails_one_blocked_guidance_lists_surviving_dep(self, tmp_path: Path) -> None:
        """One dep raises FileNotFoundError (skipped), other dep is active blocked.

        Verifies that start_work() continues processing remaining deps after a
        failing lookup and emits guidance only for the surviving blocked dep.
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[98, 99]")
        # task 98 intentionally absent → FileNotFoundError, silently skipped
        _write_task(board, task_id=99, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().start_work(1)
        expected = (
            "⚠️ This task has unresolved dependencies (IDs: 99). "
            "Review and confirm with the user that starting this work is intentional."
        )
        assert resp.guidance == [expected]
