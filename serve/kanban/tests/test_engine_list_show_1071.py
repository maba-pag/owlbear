"""Failing tests for B-06: list_tasks (parent filter), show_task (dep_status),
and CockpitView.list_tasks / CockpitView.show_task (task #1071).

AC coverage:
  AC-sig      — list_tasks signature includes parent per §1.1
  AC-par-ok   — list_tasks(parent=N) returns only tasks whose parent == N
  AC-par-excl — list_tasks(parent=N) excludes tasks with a different parent
  AC-par-none — list_tasks(parent=N) excludes tasks with no parent
  AC-par-miss — list_tasks(parent=999) → empty list (no match)
  AC-ids-par  — list_tasks(ids=[...], parent=N) → ValidationError(ERR_IDS_EXCLUSIVE)
  AC-dep-ok   — show_task dep_status="ok" when dep is active (§3.3 every read)
  AC-dep-blk  — show_task dep_status="blocked" when dep archived w/ "dropped" (§3.3)
  AC-dep-rdr  — show_task dep_status="redirect" when dep archived w/ "duplicate" (§3.3)
  AC-cv-list  — CockpitView.list_tasks same signature/behaviour as AgentView.list_tasks
  AC-cv-show  — CockpitView.show_task same signature/behaviour as AgentView.show_task

All tests FAIL (RED phase).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView, CockpitView
from owlbear_kanban.models import (
    ListTasksResponse,
    NotFoundError,
    ShowTaskResponse,
    ValidationError,
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
parent: {parent}
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
    parent: str = "null",
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
        parent=parent,
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


# ---------------------------------------------------------------------------
# AC-sig / AC-par-*: parent filter on list_tasks (§1.1 signature)
# Expectation: list_tasks(parent=N) filters by parent field.
# Current state: list_tasks has no parent parameter → TypeError → tests FAIL.
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksParentFilter:
    """AC-sig + AC-par: list_tasks accepts parent filter per §1.1.

    parent=N returns tasks whose parent field equals N;
    excludes tasks with a different or absent parent.
    """

    def test_parent_filter_returns_matching_child(self, tmp_path: Path) -> None:
        """AC-par-ok: list_tasks(parent=10) returns task whose parent==10."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Child", parent="10")
        _write_task(kanban_dir, task_id=2, title="Root", parent="null")
        view = _make_agent_view(kanban_dir)
        resp = view.list_tasks(parent=10)
        ids = [t.id for t in resp.tasks]
        assert 1 in ids, "Task with parent=10 must appear in list_tasks(parent=10)"

    def test_parent_filter_excludes_tasks_without_matching_parent(
        self, tmp_path: Path
    ) -> None:
        """AC-par-excl: list_tasks(parent=10) excludes tasks whose parent != 10."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Child", parent="10")
        _write_task(kanban_dir, task_id=2, title="Root", parent="null")
        _write_task(kanban_dir, task_id=3, title="OtherChild", parent="99")
        view = _make_agent_view(kanban_dir)
        resp = view.list_tasks(parent=10)
        ids = [t.id for t in resp.tasks]
        assert 2 not in ids, "Task without parent must not appear in list_tasks(parent=10)"
        assert 3 not in ids, "Task with different parent must not appear in list_tasks(parent=10)"

    def test_parent_filter_excludes_tasks_with_no_parent(
        self, tmp_path: Path
    ) -> None:
        """AC-par-none: list_tasks(parent=5) excludes top-level (parent=null) tasks."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="TopLevel", parent="null")
        _write_task(kanban_dir, task_id=2, title="Child", parent="5")
        view = _make_agent_view(kanban_dir)
        resp = view.list_tasks(parent=5)
        ids = [t.id for t in resp.tasks]
        assert 1 not in ids, "Top-level task must not appear when parent filter is active"
        assert 2 in ids

    def test_parent_filter_returns_empty_when_no_match(self, tmp_path: Path) -> None:
        """AC-par-miss: list_tasks(parent=999) returns empty list when no tasks match."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Child", parent="10")
        view = _make_agent_view(kanban_dir)
        resp = view.list_tasks(parent=999)
        assert isinstance(resp, ListTasksResponse)
        assert resp.tasks == [], (
            f"No tasks have parent=999; expected empty list, got {resp.tasks!r}"
        )

    def test_parent_filter_result_is_list_tasks_response(self, tmp_path: Path) -> None:
        """AC-sig: list_tasks(parent=N) returns a ListTasksResponse envelope."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Child", parent="1")
        view = _make_agent_view(kanban_dir)
        resp = view.list_tasks(parent=1)
        assert isinstance(resp, ListTasksResponse)
        assert hasattr(resp, "guidance"), "ListTasksResponse must carry guidance field (D39)"


# ---------------------------------------------------------------------------
# AC-ids-par: ids exclusive with parent → ERR_IDS_EXCLUSIVE
# Expectation: ids + parent → ValidationError(ERR_IDS_EXCLUSIVE).
# Current state: parent param missing → TypeError → test FAILS.
# ---------------------------------------------------------------------------


class TestFromAC_IdsParentExclusive:
    """AC-ids-par: ids cannot be combined with parent — ERR_IDS_EXCLUSIVE."""

    def test_ids_exclusive_with_parent_raises(self, tmp_path: Path) -> None:
        """ids + parent → ValidationError(ERR_IDS_EXCLUSIVE)."""
        view = _make_agent_view(_make_board(tmp_path))
        with pytest.raises(ValidationError) as exc_info:
            view.list_tasks(ids=[1], parent=2)
        assert exc_info.value.code == "ERR_IDS_EXCLUSIVE"


# ---------------------------------------------------------------------------
# AC-dep-*: dep_status computed in show_task (§3.3 every read)
# Expectation: show_task computes and returns dep_status on the response envelope.
# Current state: dep_status never set in show_task payload → always None → FAIL.
# ---------------------------------------------------------------------------


class TestFromAC_ShowTaskDepStatus:
    """AC-dep: show_task computes dep_status per §3.3 on every read.

    The dep_status field on ShowTaskResponse must reflect the actual state of
    the task's dependencies at the time of the read — it is not persisted.
    """

    def test_show_task_dep_status_ok_when_dep_is_active(self, tmp_path: Path) -> None:
        """dep_status='ok' when all deps are active (§3.3)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Consumer", depends_on="[2]")
        _write_task(kanban_dir, task_id=2, title="ActiveDep", status="research")
        view = _make_agent_view(kanban_dir)
        resp = view.show_task(1)
        assert isinstance(resp, ShowTaskResponse)
        assert resp.dep_status == "ok", (
            f"All deps active; §3.3 requires dep_status='ok' but got {resp.dep_status!r}"
        )

    def test_show_task_dep_status_blocked_when_dep_archived_dropped(
        self, tmp_path: Path
    ) -> None:
        """dep_status='blocked' when dep is archived with reason 'dropped' (§3.3)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=3, title="Consumer", depends_on="[4]")
        _write_task(
            kanban_dir,
            task_id=4,
            title="DroppedDep",
            status="archived",
            archival_reason="dropped",
            subdir="archive",
        )
        view = _make_agent_view(kanban_dir)
        resp = view.show_task(3)
        assert resp.dep_status == "blocked", (
            f"Dep archived w/ 'dropped'; §3.3 requires dep_status='blocked' "
            f"but got {resp.dep_status!r}"
        )

    def test_show_task_dep_status_redirect_when_dep_archived_duplicate(
        self, tmp_path: Path
    ) -> None:
        """dep_status='redirect' when dep is archived with reason 'duplicate' (§3.3)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=5, title="Consumer", depends_on="[6]")
        _write_task(
            kanban_dir,
            task_id=6,
            title="DupDep",
            status="archived",
            archival_reason="duplicate",
            subdir="archive",
        )
        view = _make_agent_view(kanban_dir)
        resp = view.show_task(5)
        assert resp.dep_status == "redirect", (
            f"Dep archived w/ 'duplicate'; §3.3 requires dep_status='redirect' "
            f"but got {resp.dep_status!r}"
        )

    def test_show_task_dep_status_worst_wins_blocked_over_redirect(
        self, tmp_path: Path
    ) -> None:
        """dep_status='blocked' when mixed deps: one dropped, one duplicate (§3.3 precedence)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=7, title="Consumer", depends_on="[8, 9]")
        _write_task(
            kanban_dir,
            task_id=8,
            title="Dropped",
            status="archived",
            archival_reason="dropped",
            subdir="archive",
        )
        _write_task(
            kanban_dir,
            task_id=9,
            title="Duplicate",
            status="archived",
            archival_reason="duplicate",
            subdir="archive",
        )
        view = _make_agent_view(kanban_dir)
        resp = view.show_task(7)
        assert resp.dep_status == "blocked", (
            f"blocked > redirect per §3.3; expected 'blocked' but got {resp.dep_status!r}"
        )


# ---------------------------------------------------------------------------
# AC-cv-list: CockpitView.list_tasks — identical signature and behaviour
# Expectation: CockpitView.list_tasks delegates to engine with same contract.
# Current state: raises NotImplementedError → tests FAIL.
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewListTasks:
    """AC-cv-list: CockpitView.list_tasks has identical signature/behaviour to AgentView."""

    def test_cockpit_list_tasks_returns_list_tasks_response(
        self, tmp_path: Path
    ) -> None:
        """CockpitView.list_tasks() returns a ListTasksResponse."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Task A")
        view = _make_cockpit_view(kanban_dir)
        resp = view.list_tasks()
        assert isinstance(resp, ListTasksResponse), (
            f"CockpitView.list_tasks must return ListTasksResponse; got {type(resp)!r}"
        )

    def test_cockpit_list_tasks_status_filter_works(self, tmp_path: Path) -> None:
        """CockpitView.list_tasks(status='todo') returns matching tasks only."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Todo Task", status="todo")
        _write_task(kanban_dir, task_id=2, title="Research Task", status="research")
        view = _make_cockpit_view(kanban_dir)
        resp = view.list_tasks(status="todo")
        ids = [t.id for t in resp.tasks]
        assert 1 in ids, "todo task must appear in list_tasks(status='todo')"
        assert 2 not in ids, "research task must not appear in list_tasks(status='todo')"

    def test_cockpit_list_tasks_ids_filter_works(self, tmp_path: Path) -> None:
        """CockpitView.list_tasks(ids=[N]) returns only the requested task."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Task A")
        _write_task(kanban_dir, task_id=2, title="Task B")
        view = _make_cockpit_view(kanban_dir)
        resp = view.list_tasks(ids=[1])
        ids = [t.id for t in resp.tasks]
        assert ids == [1], f"ids=[1] must return exactly task 1; got {ids!r}"

    def test_cockpit_list_tasks_ids_exclusive_with_status_raises(
        self, tmp_path: Path
    ) -> None:
        """CockpitView.list_tasks(ids=[1], status='todo') → ERR_IDS_EXCLUSIVE."""
        view = _make_cockpit_view(_make_board(tmp_path))
        with pytest.raises(ValidationError) as exc_info:
            view.list_tasks(ids=[1], status="todo")
        assert exc_info.value.code == "ERR_IDS_EXCLUSIVE"


# ---------------------------------------------------------------------------
# AC-cv-show: CockpitView.show_task — identical signature and behaviour
# Expectation: CockpitView.show_task(id, section) delegates to engine.
# Current state: raises NotImplementedError → tests FAIL.
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewShowTask:
    """AC-cv-show: CockpitView.show_task has identical signature/behaviour to AgentView."""

    def test_cockpit_show_task_returns_show_task_response(self, tmp_path: Path) -> None:
        """CockpitView.show_task(id) returns a ShowTaskResponse."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Show Me")
        view = _make_cockpit_view(kanban_dir)
        resp = view.show_task(1)
        assert isinstance(resp, ShowTaskResponse), (
            f"CockpitView.show_task must return ShowTaskResponse; got {type(resp)!r}"
        )
        assert resp.id == 1

    def test_cockpit_show_task_section_filter_returns_filtered_body(
        self, tmp_path: Path
    ) -> None:
        """CockpitView.show_task(id, section='Goals') returns section-filtered body."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            task_id=2,
            title="Sectioned",
            body="## Goals\nGoal content.\n\n## Notes\nNote content.\n",
        )
        view = _make_cockpit_view(kanban_dir)
        view.engine.list_tasks()  # warm _id_to_filename index
        resp = view.show_task(2, section="Goals")
        assert resp.body is not None, "Section-matched body must not be None"
        assert "Goal content." in resp.body
        assert "Note content." not in resp.body, (
            "Section filter must exclude unmatched headings"
        )

    def test_cockpit_show_task_not_found_raises_err_not_found(
        self, tmp_path: Path
    ) -> None:
        """CockpitView.show_task(99999) → NotFoundError(ERR_NOT_FOUND)."""
        view = _make_cockpit_view(_make_board(tmp_path))
        with pytest.raises(NotFoundError) as exc_info:
            view.show_task(99999)
        assert exc_info.value.code == "ERR_NOT_FOUND"
