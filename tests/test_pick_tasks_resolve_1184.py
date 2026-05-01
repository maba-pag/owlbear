"""Tests for pick_tasks / resolve_pending_drs integration (task #1184).

Verifies the integration contract between AgentView.pick_tasks() and
decisions.resolve_pending_drs() — call ordering, exception isolation,
pre-filter resolution, and graceful no-DR behaviour.

All tests are RED phase (failing) until task #1185 wires the call inside
pick_tasks. The mock target is owlbear_kanban.decisions.resolve_pending_drs;
tests inject the module via sys.modules so they work regardless of whether
the implementation uses a module-level import or a lazy per-call import.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import PickTasksResponse

# ---------------------------------------------------------------------------
# Board helpers — follows test_engine_pick_tasks_1074.py patterns
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
  - critical
  - needed
  - important
  - nice-to-have
  - someday
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
    agent_types:
        researcher: research
        architect: design
        builder: impl
        reviewer: review
        auditor: audit
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
priority: {priority}
created: "2026-01-15T10:00:00+00:00"
updated: "2026-04-01T12:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: {blocked}
block_reason: null
claimed_at: null
archival_reason: null
archival_refs: []
---
Body text.
"""


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
    status: str = "todo",
    priority: str = "important",
    blocked: str = "false",
) -> Path:
    content = _TASK_TMPL.format(
        task_id=task_id,
        title=title,
        status=status,
        priority=priority,
        blocked=blocked,
    )
    path = board / "tasks" / f"{task_id}-task.md"
    path.write_text(content, encoding="utf-8")
    return path


def _all_ids(resp: PickTasksResponse) -> set[int]:
    return {entry.id for wave in resp.waves for entry in wave.tasks}


def _stub_decisions(return_value: list | None = None) -> MagicMock:
    """Return a MagicMock suitable for injection as owlbear_kanban.decisions."""
    mock = MagicMock()
    mock.resolve_pending_drs.return_value = (
        return_value if return_value is not None else []
    )
    return mock


# ---------------------------------------------------------------------------
# TestFromAC_PickTasksResolveIntegration
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksResolveIntegration:
    """Integration contract: pick_tasks calls resolve_pending_drs per the brief spec."""

    def test_resolve_pending_drs_is_called(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """AC1: pick_tasks calls resolve_pending_drs before task selection logic.

        Injects a mock owlbear_kanban.decisions module via sys.modules. After
        pick_tasks returns, the mock must have been called exactly once with
        the engine instance — confirming the call happens during pick_tasks.
        """
        decisions_mock = _stub_decisions()
        monkeypatch.setitem(sys.modules, "owlbear_kanban.decisions", decisions_mock)

        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)

        engine.agent_view().pick_tasks()

        decisions_mock.resolve_pending_drs.assert_called_once_with(engine)

    def test_resolve_exceptions_do_not_propagate(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """AC2: Exceptions from resolve_pending_drs must not reach the pick_tasks caller.

        The try/except guard in the implementation must swallow all exceptions so
        that pick_tasks always returns a valid PickTasksResponse. The call
        assertion also confirms the exception path was exercised, not skipped.
        """
        decisions_mock = MagicMock()
        decisions_mock.resolve_pending_drs.side_effect = RuntimeError(
            "DR resolve failed"
        )
        monkeypatch.setitem(sys.modules, "owlbear_kanban.decisions", decisions_mock)

        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)

        # Must not propagate — pick_tasks must return normally despite the exception.
        resp = engine.agent_view().pick_tasks()

        assert isinstance(resp, PickTasksResponse), (
            "pick_tasks must return PickTasksResponse even when resolve_pending_drs raises"
        )
        decisions_mock.resolve_pending_drs.assert_called_once_with(engine)

    def test_resolve_runs_before_task_filtering(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """AC3: Resolved DRs are processed before task filtering occurs.

        Ordering proof via side-effect mutation: task 1 starts blocked=true
        so it is excluded by list_tasks(blocked=False). The mock side-effect
        rewrites its file to blocked=false before returning. If resolution runs
        before filtering, list_tasks sees the updated state and includes task 1.
        If resolution runs after filtering (or not at all), task 1 is absent.
        """
        board = _make_board(tmp_path)
        task_path = _write_task(board, task_id=1, blocked="true")  # initially excluded
        _write_task(board, task_id=2)  # control: always included

        def _resolve_and_unblock(_eng: KanbanEngine) -> list:
            content = task_path.read_text(encoding="utf-8")
            updated = content.replace("blocked: true", "blocked: false")
            task_path.write_text(updated, encoding="utf-8")
            return []

        decisions_mock = MagicMock()
        decisions_mock.resolve_pending_drs.side_effect = _resolve_and_unblock
        monkeypatch.setitem(sys.modules, "owlbear_kanban.decisions", decisions_mock)

        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks()
        ids = _all_ids(resp)

        assert 2 in ids, "Task 2 (clean) must always appear in results"
        assert 1 in ids, (
            "Task 1 was unblocked by the resolve side-effect before list_tasks ran; "
            "its presence proves that resolution executes before the filter step."
        )

    def test_no_pending_drs_pick_tasks_works(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """AC4: pick_tasks functions correctly when no pending DRs exist.

        resolve_pending_drs returns [] — pick_tasks must still dispatch tasks
        normally and return a valid response.
        """
        decisions_mock = _stub_decisions(return_value=[])
        monkeypatch.setitem(sys.modules, "owlbear_kanban.decisions", decisions_mock)

        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)

        resp = engine.agent_view().pick_tasks()

        assert isinstance(resp, PickTasksResponse)
        assert 1 in _all_ids(resp), (
            "Task 1 must be dispatched when DRs return empty list"
        )
        decisions_mock.resolve_pending_drs.assert_called_once()

    def test_no_decisions_directory_pick_tasks_works(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """AC5: pick_tasks functions correctly when the pending/ directory doesn't exist.

        The board has no decisions/ subdirectory. resolve_pending_drs handles
        the missing directory internally and returns []. pick_tasks must not
        crash and must dispatch tasks normally.
        """
        decisions_mock = _stub_decisions(return_value=[])
        monkeypatch.setitem(sys.modules, "owlbear_kanban.decisions", decisions_mock)

        board = _make_board(tmp_path)
        assert not (board / "decisions").exists(), (
            "Board must not have decisions/ dir for this test"
        )
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)

        resp = engine.agent_view().pick_tasks()

        assert isinstance(resp, PickTasksResponse)
        assert 1 in _all_ids(resp), (
            "Task 1 must be dispatched when decisions/ dir is absent"
        )
        decisions_mock.resolve_pending_drs.assert_called_once()
