"""Failing tests for #1207: Direct dep lookup in AgentView.show_task.

AC coverage:
  AC1/AC2 — AgentView.show_task resolves dep status via direct engine.show_task()
             per dep ID; no list_tasks() call remains for dep enrichment
  AC3     — engine.show_task() raises FileNotFoundError for dep → dep_status 'blocked'
  AC4     — engine.show_task() raises CorruptionError/ValueError/KeyError → dep_status 'blocked'
  AC5     — Archival reason effects preserved: dropped/wontfix→blocked,
             deprecated/duplicate→redirect, else→ok
  AC6     — KanbanEngine.show_task warm-cache path: when _id_to_filename resolves an
             ID to a tasks/ filename AND archive_dir/filename also exists, return the
             archive copy and evict the ID from _id_to_filename (AC-C19 mode 7 parity)
  AC7     — CockpitView.show_task (delegates to AgentView.show_task) unaffected
  AC8     — tests pass

All tests must FAIL before the implementation is changed (RED phase).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest import mock

from owlbear_kanban import KanbanEngine
from owlbear_kanban.corruption import CorruptionError
from owlbear_kanban.engine import AgentView
from owlbear_kanban.models import ShowTaskResponse
from owlbear_cockpit.view import CockpitView

# ---------------------------------------------------------------------------
# Board / task helpers
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
next_id: 1
"""

_TASK_TMPL = """\
---
id: {task_id}
title: {title}
status: {status}
priority: {priority}
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: {tags}
parent: null
depends_on: {depends_on}
blocked: false
block_reason: null
claimed_at: null
archival_reason: {archival_reason}
archival_refs: []
---
{body}
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
    *,
    task_id: int = 1,
    title: str = "Task",
    status: str = "todo",
    priority: str = "needed",
    tags: str = "[]",
    depends_on: str = "[]",
    body: str = "Body.",
    archival_reason: str = "null",
    subdir: str = "tasks",
) -> Path:
    content = _TASK_TMPL.format(
        task_id=task_id,
        title=title,
        status=status,
        priority=priority,
        tags=tags,
        depends_on=depends_on,
        body=body,
        archival_reason=archival_reason,
    )
    path = kanban_dir / subdir / f"{task_id}-task.md"
    path.write_text(content, encoding="utf-8")
    return path


def _make_agent_view(kanban_dir: Path) -> AgentView:
    engine = KanbanEngine(kanban_dir, activity_log=False)
    return AgentView(engine)


def _make_cockpit_view(kanban_dir: Path) -> CockpitView:
    engine = KanbanEngine(kanban_dir, activity_log=False)
    return CockpitView(engine)


def _raise_list_tasks_called(*_a: object, **_kw: object) -> None:
    """Side-effect that fails loudly if list_tasks is invoked during dep enrichment."""
    msg = "list_tasks must not be called for dep enrichment"
    raise NotImplementedError(msg)


# ---------------------------------------------------------------------------
# AC1 + AC2: No list_tasks() call for dep enrichment
#
# Strategy: mock engine.list_tasks to raise NotImplementedError.
# Current code calls list_tasks for active_ids / archived_reasons → crashes.
# New code uses engine.show_task() per dep → list_tasks never called → passes.
# ---------------------------------------------------------------------------


class TestFromAC_DirectDepLookup:
    """AC1/AC2: AgentView.show_task resolves deps via engine.show_task(), not list_tasks().

    All tests mock engine.list_tasks to raise NotImplementedError so that the
    current O(N) implementation fails immediately.  The new implementation must
    never call list_tasks for dep enrichment.
    """

    def test_no_list_tasks_for_task_with_no_deps(self, tmp_path: Path) -> None:
        """Task with no deps: list_tasks must not be called at all."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="NoDeps", depends_on="[]")
        view = _make_agent_view(kanban_dir)
        with mock.patch.object(view.engine, "list_tasks", side_effect=_raise_list_tasks_called):
            resp = view.show_task(1)
        assert resp.dep_status is None, "No deps → dep_status must be None (not computed via list_tasks)"

    def test_no_list_tasks_for_active_dep(self, tmp_path: Path) -> None:
        """Active dep: dep_status='ok' computed via direct show_task, not list_tasks."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Consumer", depends_on="[2]")
        _write_task(kanban_dir, task_id=2, title="ActiveDep", status="todo")
        view = _make_agent_view(kanban_dir)
        view.engine.list_tasks(archived=False)  # warm the _id_to_filename index
        with mock.patch.object(view.engine, "list_tasks", side_effect=_raise_list_tasks_called):
            resp = view.show_task(1)
        assert resp.dep_status == "ok", f"Active dep → dep_status must be 'ok' but got {resp.dep_status!r}"

    def test_no_list_tasks_for_archived_completed_dep(self, tmp_path: Path) -> None:
        """Archived-completed dep: dep_status='ok' without list_tasks."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Consumer", depends_on="[2]")
        _write_task(
            kanban_dir,
            task_id=2,
            title="CompletedDep",
            status="archived",
            archival_reason="completed",
            subdir="archive",
        )
        view = _make_agent_view(kanban_dir)
        view.engine.list_tasks(archived=False)  # warm index
        with mock.patch.object(view.engine, "list_tasks", side_effect=_raise_list_tasks_called):
            resp = view.show_task(1)
        assert resp.dep_status == "ok", f"Archived-completed dep → dep_status must be 'ok' but got {resp.dep_status!r}"


# ---------------------------------------------------------------------------
# AC3: FileNotFoundError for dep ID → dep_status 'blocked'
#
# Strategy: mock engine.show_task to raise FileNotFoundError for the dep ID
# while returning the real task for the main task ID.  Current code consults
# list_tasks (not show_task) for deps → sees dep as active → dep_status='ok'.
# New code raises FileNotFoundError → dep_status='blocked'.
# ---------------------------------------------------------------------------


class TestFromAC_FileNotFoundError:
    """AC3: engine.show_task raises FileNotFoundError for dep → dep_status 'blocked'."""

    def test_file_not_found_dep_returns_blocked(self, tmp_path: Path) -> None:
        """FileNotFoundError for dep → dep_status='blocked' (AC3)."""
        kanban_dir = _make_board(tmp_path)
        # dep 2 is on disk as active so list_tasks reports it → current code: 'ok'
        _write_task(kanban_dir, task_id=1, title="Consumer", depends_on="[2]")
        _write_task(kanban_dir, task_id=2, title="ActiveDep", status="todo")
        view = _make_agent_view(kanban_dir)
        view.engine.list_tasks(archived=False)  # warm index
        original = view.engine.show_task

        def _side_effect(task_id_str: str) -> Any:
            if task_id_str == "2":
                msg = f"Dep {task_id_str!r} not found (simulated race)"
                raise FileNotFoundError(msg)
            return original(task_id_str)

        with mock.patch.object(view.engine, "show_task", side_effect=_side_effect):
            resp = view.show_task(1)
        assert resp.dep_status == "blocked", (
            f"FileNotFoundError for dep → must be 'blocked' but got {resp.dep_status!r}"
        )

    def test_one_missing_dep_blocks_even_with_active_other_dep(self, tmp_path: Path) -> None:
        """One missing dep + one active dep → dep_status='blocked' (worst wins)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Consumer", depends_on="[2, 3]")
        _write_task(kanban_dir, task_id=2, title="ActiveDep", status="todo")
        _write_task(kanban_dir, task_id=3, title="ActiveDep2", status="todo")
        view = _make_agent_view(kanban_dir)
        view.engine.list_tasks(archived=False)
        original = view.engine.show_task

        def _side_effect(task_id_str: str) -> Any:
            if task_id_str == "3":
                msg = "dep 3 vanished"
                raise FileNotFoundError(msg)
            return original(task_id_str)

        with mock.patch.object(view.engine, "show_task", side_effect=_side_effect):
            resp = view.show_task(1)
        assert resp.dep_status == "blocked", "One missing dep among two must still yield dep_status='blocked'"


# ---------------------------------------------------------------------------
# AC4: CorruptionError / ValueError / KeyError for dep → dep_status 'blocked'
#
# Strategy: mock engine.show_task to raise for the dep ID; current code uses
# list_tasks which sees the dep as active → dep_status='ok'.  New code raises
# on the direct lookup → dep_status='blocked'.
# ---------------------------------------------------------------------------


class TestFromAC_CorruptionErrorHandling:
    """AC4: CorruptionError/ValueError/KeyError for dep → dep_status 'blocked'."""

    def test_corruption_error_for_active_dep_returns_blocked(self, tmp_path: Path) -> None:
        """engine.show_task raises CorruptionError for active dep → dep_status='blocked'.

        Current code: list_tasks sees dep 2 as active → dep_status='ok'.
        New code: show_task raises CorruptionError → dep_status='blocked'.
        """
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Consumer", depends_on="[2]")
        _write_task(kanban_dir, task_id=2, title="ActiveDep", status="todo")
        view = _make_agent_view(kanban_dir)
        view.engine.list_tasks(archived=False)
        original = view.engine.show_task

        def _side_effect(task_id_str: str) -> Any:
            if task_id_str == "2":
                raise CorruptionError(code="ERR_CORRUPT_MISSING_FIELD", detail="id missing")
            return original(task_id_str)

        with mock.patch.object(view.engine, "show_task", side_effect=_side_effect):
            resp = view.show_task(1)
        assert resp.dep_status == "blocked", f"CorruptionError for dep → must be 'blocked' but got {resp.dep_status!r}"

    def test_corruption_error_for_archived_dep_overrides_archival_reason(self, tmp_path: Path) -> None:
        """engine.show_task raises CorruptionError for archived dep → 'blocked' not 'ok'.

        Dep 2 is on disk as archived 'completed' (would give dep_status='ok').
        When show_task raises CorruptionError, the result must be 'blocked'.
        Current code: list_tasks returns archival_reason='completed' → 'ok'.
        New code: CorruptionError from show_task → 'blocked'.
        """
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Consumer", depends_on="[2]")
        _write_task(
            kanban_dir,
            task_id=2,
            title="CompletedDep",
            status="archived",
            archival_reason="completed",
            subdir="archive",
        )
        view = _make_agent_view(kanban_dir)
        view.engine.list_tasks(archived=False)
        original = view.engine.show_task

        def _side_effect(task_id_str: str) -> Any:
            if task_id_str == "2":
                raise CorruptionError(code="ERR_CORRUPT_MISSING_FIELD", detail="corrupt on direct lookup")
            return original(task_id_str)

        with mock.patch.object(view.engine, "show_task", side_effect=_side_effect):
            resp = view.show_task(1)
        assert resp.dep_status == "blocked", (
            f"CorruptionError overrides archival_reason='completed'; must be 'blocked' but got {resp.dep_status!r}"
        )

    def test_value_error_from_show_task_returns_blocked(self, tmp_path: Path) -> None:
        """engine.show_task raises ValueError for dep → dep_status='blocked'."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Consumer", depends_on="[2]")
        _write_task(kanban_dir, task_id=2, title="ActiveDep", status="todo")
        view = _make_agent_view(kanban_dir)
        view.engine.list_tasks(archived=False)
        original = view.engine.show_task

        def _side_effect(task_id_str: str) -> Any:
            if task_id_str == "2":
                msg = "malformed task data"
                raise ValueError(msg)
            return original(task_id_str)

        with mock.patch.object(view.engine, "show_task", side_effect=_side_effect):
            resp = view.show_task(1)
        assert resp.dep_status == "blocked", f"ValueError for dep → must be 'blocked' but got {resp.dep_status!r}"

    def test_key_error_from_show_task_returns_blocked(self, tmp_path: Path) -> None:
        """engine.show_task raises KeyError for dep → dep_status='blocked'."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Consumer", depends_on="[2]")
        _write_task(kanban_dir, task_id=2, title="ActiveDep", status="todo")
        view = _make_agent_view(kanban_dir)
        view.engine.list_tasks(archived=False)
        original = view.engine.show_task

        def _side_effect(task_id_str: str) -> Any:
            if task_id_str == "2":
                msg = "missing key in task data"
                raise KeyError(msg)
            return original(task_id_str)

        with mock.patch.object(view.engine, "show_task", side_effect=_side_effect):
            resp = view.show_task(1)
        assert resp.dep_status == "blocked", f"KeyError for dep → must be 'blocked' but got {resp.dep_status!r}"


# ---------------------------------------------------------------------------
# AC5: Archival reason effects preserved via _dep_effect_from_archival_reason
#
# Strategy: all tests mock engine.list_tasks to raise (AC2 enforcement) and
# use real archived dep files on disk.  Current code calls list_tasks → crash.
# New code reads dep via engine.show_task → checks archival_reason → effect.
# ---------------------------------------------------------------------------


class TestFromAC_ArchivalReasonEffects:
    """AC5: dropped/wontfix→blocked, deprecated/duplicate→redirect, else→ok.

    All tests block list_tasks so they fail with the current implementation.
    """

    def _setup_archived_dep(
        self,
        tmp_path: Path,
        *,
        dep_archival_reason: str,
    ) -> AgentView:
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Consumer", depends_on="[2]")
        _write_task(
            kanban_dir,
            task_id=2,
            title="DepTask",
            status="archived",
            archival_reason=dep_archival_reason,
            subdir="archive",
        )
        view = _make_agent_view(kanban_dir)
        view.engine.list_tasks(archived=False)  # warm index so show_task can find task 1
        return view

    def test_archived_dropped_dep_returns_blocked(self, tmp_path: Path) -> None:
        """archival_reason='dropped' → dep_status='blocked'."""
        view = self._setup_archived_dep(tmp_path, dep_archival_reason="dropped")
        with mock.patch.object(view.engine, "list_tasks", side_effect=_raise_list_tasks_called):
            resp = view.show_task(1)
        assert resp.dep_status == "blocked", f"dropped dep → must be 'blocked' but got {resp.dep_status!r}"

    def test_archived_wontfix_dep_returns_blocked(self, tmp_path: Path) -> None:
        """archival_reason='wontfix' → dep_status='blocked'."""
        view = self._setup_archived_dep(tmp_path, dep_archival_reason="wontfix")
        with mock.patch.object(view.engine, "list_tasks", side_effect=_raise_list_tasks_called):
            resp = view.show_task(1)
        assert resp.dep_status == "blocked", f"wontfix dep → must be 'blocked' but got {resp.dep_status!r}"

    def test_archived_deprecated_dep_returns_redirect(self, tmp_path: Path) -> None:
        """archival_reason='deprecated' → dep_status='redirect'."""
        view = self._setup_archived_dep(tmp_path, dep_archival_reason="deprecated")
        with mock.patch.object(view.engine, "list_tasks", side_effect=_raise_list_tasks_called):
            resp = view.show_task(1)
        assert resp.dep_status == "redirect", f"deprecated dep → must be 'redirect' but got {resp.dep_status!r}"

    def test_archived_duplicate_dep_returns_redirect(self, tmp_path: Path) -> None:
        """archival_reason='duplicate' → dep_status='redirect'."""
        view = self._setup_archived_dep(tmp_path, dep_archival_reason="duplicate")
        with mock.patch.object(view.engine, "list_tasks", side_effect=_raise_list_tasks_called):
            resp = view.show_task(1)
        assert resp.dep_status == "redirect", f"duplicate dep → must be 'redirect' but got {resp.dep_status!r}"

    def test_archived_completed_dep_returns_ok(self, tmp_path: Path) -> None:
        """archival_reason='completed' → dep_status='ok'."""
        view = self._setup_archived_dep(tmp_path, dep_archival_reason="completed")
        with mock.patch.object(view.engine, "list_tasks", side_effect=_raise_list_tasks_called):
            resp = view.show_task(1)
        assert resp.dep_status == "ok", f"completed dep → must be 'ok' but got {resp.dep_status!r}"

    def test_blocked_beats_redirect_for_mixed_deps(self, tmp_path: Path) -> None:
        """blocked > redirect: wontfix dep + duplicate dep → 'blocked' wins."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Consumer", depends_on="[2, 3]")
        _write_task(
            kanban_dir,
            task_id=2,
            title="WontfixDep",
            status="archived",
            archival_reason="wontfix",
            subdir="archive",
        )
        _write_task(
            kanban_dir,
            task_id=3,
            title="DuplicateDep",
            status="archived",
            archival_reason="duplicate",
            subdir="archive",
        )
        view = _make_agent_view(kanban_dir)
        view.engine.list_tasks(archived=False)
        with mock.patch.object(view.engine, "list_tasks", side_effect=_raise_list_tasks_called):
            resp = view.show_task(1)
        assert resp.dep_status == "blocked", (
            f"wontfix + duplicate → 'blocked' must win over 'redirect', got {resp.dep_status!r}"
        )

    def test_archive_wins_over_tasks_copy_for_dep_status(self, tmp_path: Path) -> None:
        """AC5 archive-wins: dep in both tasks/ and archive/ → archive takes precedence.

        Existing engine semantics (AC-C19 mode 7 in list_tasks): when an archive
        copy of a dep exists, the tasks/ copy is ignored.  The new direct show_task
        lookup must replicate this: the archived state (here 'dropped' → 'blocked')
        must govern dep_status, not the active tasks/ copy ('ok').

        Current (pre-fix) implementation: engine.show_task checks tasks/ first
        via cold-path glob → returns active copy → dep_status='ok' (REGRESSION).
        """
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Consumer", depends_on="[2]")
        # dep 2 present in tasks/ as active — would give dep_status='ok' if returned
        _write_task(kanban_dir, task_id=2, title="DepActive", status="todo")
        # dep 2 also present in archive/ as 'dropped' — must win → dep_status='blocked'
        _write_task(
            kanban_dir,
            task_id=2,
            title="DepDropped",
            status="archived",
            archival_reason="dropped",
            subdir="archive",
        )
        view = _make_agent_view(kanban_dir)
        # Warm the index: list_tasks sees archive-wins and skips tasks/ copy for dep 2.
        # After this call, _id_to_filename does NOT contain dep 2 (popped by AC-C19 mode 7).
        view.engine.list_tasks(archived=False)
        with mock.patch.object(view.engine, "list_tasks", side_effect=_raise_list_tasks_called):
            resp = view.show_task(1)
        assert resp.dep_status == "blocked", (
            f"archive-wins: dep 2 in both tasks/ (active) and archive/ (dropped) "
            f"must yield dep_status='blocked', got {resp.dep_status!r}"
        )


# ---------------------------------------------------------------------------
# AC6: CockpitView.show_task unaffected — no API change (regression guard)
#
# CockpitView.show_task delegates to AgentView.show_task (view.py:68).
# Block list_tasks so the test fails with current code but passes with new code.
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewRegression:
    """AC6: CockpitView.show_task unchanged — same signature, same return type."""

    def test_cockpit_view_show_task_returns_show_task_response(self, tmp_path: Path) -> None:
        """CockpitView.show_task returns ShowTaskResponse with correct dep_status."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Consumer", depends_on="[2]")
        _write_task(kanban_dir, task_id=2, title="ActiveDep", status="todo")
        cv = _make_cockpit_view(kanban_dir)
        cv.engine.list_tasks(archived=False)  # warm index
        with mock.patch.object(cv.engine, "list_tasks", side_effect=_raise_list_tasks_called):
            resp = cv.show_task(1)
        assert isinstance(resp, ShowTaskResponse), (
            "CockpitView.show_task must still return ShowTaskResponse after refactor"
        )
        assert resp.dep_status == "ok", (
            f"CockpitView.show_task: active dep → dep_status must be 'ok', got {resp.dep_status!r}"
        )

    def test_cockpit_view_show_task_accepts_section_parameter(self, tmp_path: Path) -> None:
        """CockpitView.show_task still accepts optional section parameter (no API change)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            title="WithSection",
            depends_on="[]",
            body="## Notes\ncontent here\n",
        )
        cv = _make_cockpit_view(kanban_dir)
        cv.engine.list_tasks(archived=False)
        with mock.patch.object(cv.engine, "list_tasks", side_effect=_raise_list_tasks_called):
            resp = cv.show_task(1, section="Notes")
        assert isinstance(resp, ShowTaskResponse)
        assert resp.body is not None, "section extraction must still work after refactor"

    def test_cockpit_view_show_task_section_extracts_correct_content(self, tmp_path: Path) -> None:
        """AC6 (stronger): CockpitView.show_task section= returns the extracted content.

        Discriminating assertion: body must equal the section's content text,
        not merely be non-null.  A non-null but wrong body (e.g. full body or
        wrong section) would still pass the weaker test above but fail here.
        """
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            title="WithSection",
            depends_on="[]",
            body="## Notes\ncontent here\n",
        )
        cv = _make_cockpit_view(kanban_dir)
        cv.engine.list_tasks(archived=False)
        with mock.patch.object(cv.engine, "list_tasks", side_effect=_raise_list_tasks_called):
            resp = cv.show_task(1, section="Notes")
        assert isinstance(resp, ShowTaskResponse)
        assert resp.body == "content here\n\n", (
            f"section='Notes' must extract only the section content, got {resp.body!r}"
        )


# ---------------------------------------------------------------------------
# AC6 (cycle 2): KanbanEngine.show_task warm-cache archive precedence
#
# New AC added after cycle-2 architecture review.
# Strategy: warm _id_to_filename with dep 2 present only in tasks/, THEN place
# an archive copy (simulating concurrent archival).  The warm-cache path finds
# dep 2 in _id_to_filename → gets filename → stat(tasks/2-task.md) succeeds →
# current code returns active copy without checking archive → dep_status='ok'
# (REGRESSION).  Fix must check archive_dir/filename after stat succeeds and
# return the archive copy if it exists, evicting the ID from _id_to_filename.
# ---------------------------------------------------------------------------


class TestFromAC_WarmCacheArchivePrecedence:
    """AC6 (cycle 2): show_task warm-cache branch must honour archive precedence.

    KanbanEngine.show_task warm-cache path (engine.py ~line 781):
    when _id_to_filename resolves an ID to a tasks/ filename AND
    archive_dir / filename also exists, the archive copy must be returned and
    the ID evicted from _id_to_filename (AC-C19 mode 7 parity).
    """

    def test_warm_cache_dep_returns_archive_when_archive_appears_after_index(self, tmp_path: Path) -> None:
        """Discriminating warm-cache archive-wins test (AC6).

        Setup:
          1. dep 2 written to tasks/ only — no archive copy.
          2. list_tasks(archived=False) called → _id_to_filename gains dep 2 (warm).
          3. Archive copy of dep 2 added ('dropped') to simulate concurrent archival.
          4. AgentView.show_task(1) called → warm-cache hit for dep 2.

        Expected: dep_status='blocked' (archive copy, archival_reason='dropped').
        Current (pre-fix): dep_status='ok' (tasks/ copy returned; archive not checked).
        """
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Consumer", depends_on="[2]")
        # dep 2 in tasks/ only — no archive copy yet.
        _write_task(kanban_dir, task_id=2, title="ActiveDep", status="todo")
        view = _make_agent_view(kanban_dir)

        # Warm the index: dep 2 is added to _id_to_filename.
        view.engine.list_tasks(archived=False)
        assert 2 in view.engine._id_to_filename, (
            "Test precondition failed: dep 2 must be in _id_to_filename after list_tasks"
        )

        # Simulate concurrent archival: place archive copy AFTER index is warm.
        _write_task(
            kanban_dir,
            task_id=2,
            title="DepDropped",
            status="archived",
            archival_reason="dropped",
            subdir="archive",
        )

        # Warm-cache hit for dep 2 — must return archive copy, not active copy.
        with mock.patch.object(view.engine, "list_tasks", side_effect=_raise_list_tasks_called):
            resp = view.show_task(1)
        assert resp.dep_status == "blocked", (
            f"warm-cache archive-wins: dep 2 in tasks/ (active) and archive/ (dropped) "
            f"after index warmed with active-only. Expected dep_status='blocked', "
            f"got {resp.dep_status!r}"
        )

    def test_warm_cache_id_evicted_from_index_after_archive_precedence_applied(self, tmp_path: Path) -> None:
        """After archive-wins on warm-cache hit, dep ID is evicted from _id_to_filename.

        AC6 states: 'return the archive copy and evict the ID from _id_to_filename'.
        After the archive-precedence branch fires, dep 2 must no longer be cached in
        _id_to_filename so that subsequent lookups use the cold archive-glob path.

        Current (pre-fix): dep 2 remains in _id_to_filename because the warm-cache
        path returns the active tasks/ copy and never reaches the eviction branch.
        """
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Consumer", depends_on="[2]")
        _write_task(kanban_dir, task_id=2, title="ActiveDep", status="todo")
        engine = KanbanEngine(kanban_dir, activity_log=False)

        # Warm the index.
        engine.list_tasks(archived=False)
        assert 2 in engine._id_to_filename, (
            "Test precondition failed: dep 2 must be in _id_to_filename after list_tasks"
        )

        # Concurrent archival: place archive copy after index is warm.
        _write_task(
            kanban_dir,
            task_id=2,
            title="DepDropped",
            status="archived",
            archival_reason="dropped",
            subdir="archive",
        )

        # Trigger the warm-cache archive-wins path for dep 2 directly.
        engine.show_task("2")

        # After archive-wins, dep 2 must be evicted from _id_to_filename.
        assert 2 not in engine._id_to_filename, (
            "After warm-cache archive-wins, dep 2 must be evicted from _id_to_filename"
        )
