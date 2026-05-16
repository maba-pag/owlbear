"""Failing tests for B-06: list_tasks (parent filter) and show_task (dep_status)
(task #1071).

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
All tests FAIL (RED phase).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView
from owlbear_kanban.models import (
    ListTasksResponse,
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

    def test_parent_filter_excludes_tasks_without_matching_parent(self, tmp_path: Path) -> None:
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

    def test_parent_filter_excludes_tasks_with_no_parent(self, tmp_path: Path) -> None:
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
        assert resp.tasks == [], f"No tasks have parent=999; expected empty list, got {resp.tasks!r}"

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
        assert resp.dep_status == "ok", f"All deps active; §3.3 requires dep_status='ok' but got {resp.dep_status!r}"

    def test_show_task_dep_status_blocked_when_dep_archived_dropped(self, tmp_path: Path) -> None:
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
            f"Dep archived w/ 'dropped'; §3.3 requires dep_status='blocked' but got {resp.dep_status!r}"
        )

    def test_show_task_dep_status_redirect_when_dep_archived_duplicate(self, tmp_path: Path) -> None:
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
            f"Dep archived w/ 'duplicate'; §3.3 requires dep_status='redirect' but got {resp.dep_status!r}"
        )

    def test_show_task_dep_status_worst_wins_blocked_over_redirect(self, tmp_path: Path) -> None:
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
# AC-sort-rev-lim: AgentView.list_tasks forwards sort, reverse, limit
# Removing any one of these from the delegation must cause these tests to fail.
# Expectation: sorted/reversed/limited results returned by AgentView.
# ---------------------------------------------------------------------------


class TestFromAC_AgentViewSortReverseLimitForwarding:
    """AC: AgentView.list_tasks forwards sort, reverse, limit — removing any one must fail a test.

    Tests write tasks in non-trivial ID order so that unsorted results differ
    from sorted results, making each assertion mutation-sensitive.
    """

    def test_sort_id_returns_ascending_order(self, tmp_path: Path) -> None:
        """sort='id' produces ascending task ID order through AgentView."""
        kanban_dir = _make_board(tmp_path)
        # Write in descending ID order so default scan order != sorted order.
        _write_task(kanban_dir, task_id=4, title="Four")
        _write_task(kanban_dir, task_id=2, title="Two")
        _write_task(kanban_dir, task_id=3, title="Three")
        _write_task(kanban_dir, task_id=1, title="One")
        view = _make_agent_view(kanban_dir)
        resp = view.list_tasks(sort="id")
        ids = [t.id for t in resp.tasks]
        assert len(ids) == 4, f"expected 4 tasks, got {len(ids)}"
        assert ids == sorted(ids), f"sort='id' must produce ascending ID order; got {ids}"

    def test_sort_title_produces_non_id_order(self, tmp_path: Path) -> None:
        """sort='title' returns alphabetical title order, provably different from filename order.

        Files are named '{id}-task.md', so os.scandir() on APFS/ext4 enumerates them
        in ID order [1, 2, 3].  Title-alphabetical order for "Apple"(id=2), "Mango"(id=3),
        "Zebra"(id=1) is [2, 3, 1] — a result impossible to produce without sort forwarding.
        Removing sort='title' from AgentView.list_tasks yields [1, 2, 3], failing the assertion.
        """
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Zebra")
        _write_task(kanban_dir, task_id=2, title="Apple")
        _write_task(kanban_dir, task_id=3, title="Mango")
        view = _make_agent_view(kanban_dir)
        resp = view.list_tasks(sort="title")
        ids = [t.id for t in resp.tasks]
        assert ids == [2, 3, 1], f"sort='title' must produce alphabetical title order [2, 3, 1]; got {ids}"

    def test_sort_id_with_reverse_returns_descending_order(self, tmp_path: Path) -> None:
        """reverse=True inverts sort='id' to produce descending ID order through AgentView."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="One")
        _write_task(kanban_dir, task_id=3, title="Three")
        _write_task(kanban_dir, task_id=2, title="Two")
        view = _make_agent_view(kanban_dir)
        resp = view.list_tasks(sort="id", reverse=True)
        ids = [t.id for t in resp.tasks]
        assert len(ids) == 3, f"expected 3 tasks, got {len(ids)}"
        assert ids == sorted(ids, reverse=True), f"reverse=True must produce descending ID order; got {ids}"

    def test_limit_caps_result_count(self, tmp_path: Path) -> None:
        """limit=2 returns exactly 2 tasks even when more exist through AgentView."""
        kanban_dir = _make_board(tmp_path)
        for i in range(1, 6):
            _write_task(kanban_dir, task_id=i, title=f"Task {i}")
        view = _make_agent_view(kanban_dir)
        resp = view.list_tasks(limit=2)
        assert len(resp.tasks) == 2, f"limit=2 must return exactly 2 tasks; got {len(resp.tasks)}"

    def test_limit_zero_returns_all_tasks(self, tmp_path: Path) -> None:
        """limit=0 (default) returns all tasks with no cap through AgentView."""
        kanban_dir = _make_board(tmp_path)
        for i in range(1, 6):
            _write_task(kanban_dir, task_id=i, title=f"Task {i}")
        view = _make_agent_view(kanban_dir)
        resp = view.list_tasks(limit=0)
        assert len(resp.tasks) == 5, f"limit=0 must return all 5 tasks; got {len(resp.tasks)}"

    def test_sort_title_with_reverse_produces_title_descending_order(self, tmp_path: Path) -> None:
        """reverse=True with sort='title' produces reverse-alphabetical title order.

        Title-descending order for Zebra(id=1), Mango(id=3), Apple(id=2) is [1, 3, 2].
        Filename-based scan order is always ID-based [1, 2, 3].
        Forward-sorted title order is [2, 3, 1].
        Neither [1, 2, 3] nor [2, 3, 1] equals [1, 3, 2], so removing reverse=reverse
        OR sort=sort from AgentView.list_tasks always fails this assertion.
        """
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Zebra")
        _write_task(kanban_dir, task_id=2, title="Apple")
        _write_task(kanban_dir, task_id=3, title="Mango")
        view = _make_agent_view(kanban_dir)
        resp = view.list_tasks(sort="title", reverse=True)
        ids = [t.id for t in resp.tasks]
        assert ids == [1, 3, 2], f"sort='title' + reverse=True must produce reverse-title order [1, 3, 2]; got {ids}"


# ---------------------------------------------------------------------------
# AC-D56: section filter matches heading NAME regardless of heading level
# "case-insensitive heading match regardless of level per D56"
# Expectation: show_task(section="X") matches ## X, # X, ### X equally.
# ---------------------------------------------------------------------------


class TestFromAC_SectionHeadingLevelAgnostic:
    """AC-D56: section filter is case-insensitive AND level-agnostic per D56.

    The engine matches on the heading name only, not the markdown heading level.
    These tests prove that # Goals, ## Goals, and ### Goals all match section='Goals'.
    """

    def test_level1_heading_matches_section_filter(self, tmp_path: Path) -> None:
        """show_task(section='Goals') matches a level-1 (# Goals) heading — D56."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            task_id=50,
            title="Level1Section",
            body="# Goals\nLevel-one goal content.\n\n## Notes\nNot included.\n",
        )
        view = _make_agent_view(kanban_dir)
        view.engine.list_tasks()  # warm index
        resp = view.show_task(50, section="Goals")
        assert resp.body is not None, "D56: level-1 '# Goals' heading must match section='Goals'"
        assert "Level-one goal content." in resp.body
        assert "Not included." not in resp.body

    def test_level3_heading_matches_section_filter(self, tmp_path: Path) -> None:
        """show_task(section='GOALS') matches a level-3 (### Goals) heading — D56."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            task_id=51,
            title="Level3Section",
            body="### Goals\nLevel-three goal content.\n\n## Notes\nNot included.\n",
        )
        view = _make_agent_view(kanban_dir)
        view.engine.list_tasks()  # warm index
        resp = view.show_task(51, section="GOALS")
        assert resp.body is not None, "D56: level-3 '### Goals' heading must match case-insensitive section='GOALS'"
        assert "Level-three goal content." in resp.body
        assert "Not included." not in resp.body

    def test_mixed_heading_levels_all_match_same_section_name(self, tmp_path: Path) -> None:
        """show_task(section='Goals') matches # Goals AND ### Goals in the same body — D56."""
        kanban_dir = _make_board(tmp_path)
        body = "# Goals\nLevel-one content.\n\n## Notes\nNotes not included.\n\n### Goals\nLevel-three content.\n"
        _write_task(kanban_dir, task_id=52, title="MixedLevels", body=body)
        view = _make_agent_view(kanban_dir)
        view.engine.list_tasks()  # warm index
        resp = view.show_task(52, section="Goals")
        assert resp.body is not None, "D56: both # Goals and ### Goals must match section='Goals'"
        assert "Level-one content." in resp.body
        assert "Level-three content." in resp.body
        assert "Notes not included." not in resp.body
