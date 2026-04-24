"""RED-phase tests for AgentView.list_tasks and AgentView.show_task (task #1069).

Covers list_tasks and show_task read operations per Brief B
paper-integration.md §1.1, §1.2, §3.3, and §4.

AC coverage:
  AC1  — show_task(<archived_id>) returns TaskFull with archived fields populated
  AC2  — list_tasks(status="archived") returns archived only
  AC3  — list_tasks(ids=[active, archived, missing]) → 2 + missing_ids=[missing]
  AC12 — Multiple section matches → body concatenated in document order (D56)
  AC14 — dep_status per §3.3 honours all active tasks, not just filtered result
  AC15 — list_tasks(ids=[1], status="todo") → ValidationError(ERR_IDS_EXCLUSIVE)
  —    — ids exclusive with priority, tag, unclaimed, blocked, search → ERR_IDS_EXCLUSIVE
  —    — Invalid status enum → ValidationError(ERR_INVALID_STATUS)
  —    — Invalid priority enum → ValidationError(ERR_INVALID_PRIORITY)
  —    — Invalid archival_reason enum → ValidationError(ERR_ARCHIVAL_REASON_INVALID)

All tests FAIL (RED phase).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView
from owlbear_kanban.models import ShowTaskResponse, ValidationError

# ---------------------------------------------------------------------------
# Board and task helpers
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


def _make_view(kanban_dir: Path) -> AgentView:
    engine = KanbanEngine(kanban_dir, activity_log=False)
    return AgentView(engine)


# ---------------------------------------------------------------------------
# AC15 + invalid enum validations
# Expectation: AgentView.list_tasks validates ids-exclusive and enum params.
# Current state: no validation → no ValidationError raised → tests FAIL.
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksValidation:
    """AC15: ids exclusive with other filters → ValidationError(ERR_IDS_EXCLUSIVE).
    Invalid status/priority/archival_reason enum → ERR_INVALID_STATUS /
    ERR_INVALID_PRIORITY / ERR_ARCHIVAL_REASON_INVALID.
    """

    def test_ids_exclusive_with_status_raises(self, tmp_path: Path) -> None:
        """ids + status → ERR_IDS_EXCLUSIVE (AC15)."""
        view = _make_view(_make_board(tmp_path))
        with pytest.raises(ValidationError) as exc_info:
            view.list_tasks(ids=[1], status="todo")
        assert exc_info.value.code == "ERR_IDS_EXCLUSIVE"

    def test_ids_exclusive_with_priority_raises(self, tmp_path: Path) -> None:
        """ids + priority → ERR_IDS_EXCLUSIVE."""
        view = _make_view(_make_board(tmp_path))
        with pytest.raises(ValidationError) as exc_info:
            view.list_tasks(ids=[1], priority="needed")
        assert exc_info.value.code == "ERR_IDS_EXCLUSIVE"

    def test_ids_exclusive_with_tag_raises(self, tmp_path: Path) -> None:
        """ids + tag → ERR_IDS_EXCLUSIVE."""
        view = _make_view(_make_board(tmp_path))
        with pytest.raises(ValidationError) as exc_info:
            view.list_tasks(ids=[1], tag="some-tag")
        assert exc_info.value.code == "ERR_IDS_EXCLUSIVE"

    def test_ids_exclusive_with_unclaimed_raises(self, tmp_path: Path) -> None:
        """ids + unclaimed=True → ERR_IDS_EXCLUSIVE."""
        view = _make_view(_make_board(tmp_path))
        with pytest.raises(ValidationError) as exc_info:
            view.list_tasks(ids=[1], unclaimed=True)
        assert exc_info.value.code == "ERR_IDS_EXCLUSIVE"

    def test_ids_exclusive_with_blocked_raises(self, tmp_path: Path) -> None:
        """ids + blocked=True → ERR_IDS_EXCLUSIVE."""
        view = _make_view(_make_board(tmp_path))
        with pytest.raises(ValidationError) as exc_info:
            view.list_tasks(ids=[1], blocked=True)
        assert exc_info.value.code == "ERR_IDS_EXCLUSIVE"

    def test_ids_exclusive_with_search_raises(self, tmp_path: Path) -> None:
        """ids + search → ERR_IDS_EXCLUSIVE."""
        view = _make_view(_make_board(tmp_path))
        with pytest.raises(ValidationError) as exc_info:
            view.list_tasks(ids=[1], search="keyword")
        assert exc_info.value.code == "ERR_IDS_EXCLUSIVE"

    def test_invalid_status_raises_err_invalid_status(self, tmp_path: Path) -> None:
        """Non-existent status value → ERR_INVALID_STATUS."""
        view = _make_view(_make_board(tmp_path))
        with pytest.raises(ValidationError) as exc_info:
            view.list_tasks(status="not-a-real-status")
        assert exc_info.value.code == "ERR_INVALID_STATUS"

    def test_invalid_priority_raises_err_invalid_priority(self, tmp_path: Path) -> None:
        """Non-existent priority value → ERR_INVALID_PRIORITY."""
        view = _make_view(_make_board(tmp_path))
        with pytest.raises(ValidationError) as exc_info:
            view.list_tasks(priority="ultra-mega")
        assert exc_info.value.code == "ERR_INVALID_PRIORITY"

    def test_invalid_archival_reason_raises_err_archival_reason_invalid(
        self, tmp_path: Path
    ) -> None:
        """Non-existent archival_reason value → ERR_ARCHIVAL_REASON_INVALID.
        Note: archival_reason parameter does not yet exist on AgentView.list_tasks.
        """
        view = _make_view(_make_board(tmp_path))
        with pytest.raises(ValidationError) as exc_info:
            view.list_tasks(archival_reason="not-a-real-reason")
        assert exc_info.value.code == "ERR_ARCHIVAL_REASON_INVALID"


# ---------------------------------------------------------------------------
# AC2 + AC3 — archived task reads via list_tasks
# Expectation: status="archived" reads from archive/; ids=[...] searches both.
# Current state: status="archived" returns empty; ids ignores archive/ → FAIL.
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksArchivedReads:
    """AC2: list_tasks(status='archived') returns archived tasks only.
    AC3: list_tasks(ids=[active, archived, missing]) → 2 found + missing_ids=[missing].
    """

    def test_status_archived_returns_archived_task(self, tmp_path: Path) -> None:
        """AC2: task in archive/ appears when status='archived'."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            task_id=2,
            title="Archived Task",
            status="archived",
            archival_reason="completed",
            subdir="archive",
        )
        view = _make_view(kanban_dir)
        resp = view.list_tasks(status="archived")
        assert 2 in [t.id for t in resp.tasks], (
            "Archived task must appear when status='archived'"
        )

    def test_status_archived_excludes_active_tasks(self, tmp_path: Path) -> None:
        """AC2: active tasks must not appear when status='archived'."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Active Task", status="todo")
        _write_task(
            kanban_dir,
            task_id=2,
            title="Archived Task",
            status="archived",
            archival_reason="completed",
            subdir="archive",
        )
        view = _make_view(kanban_dir)
        resp = view.list_tasks(status="archived")
        ids = [t.id for t in resp.tasks]
        assert 1 not in ids, "Active task must not appear when status='archived'"
        assert 2 in ids

    def test_ids_with_archived_task_returns_it(self, tmp_path: Path) -> None:
        """AC3: archived task is returned when its id is in the ids list."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Active")
        _write_task(
            kanban_dir,
            task_id=2,
            title="Archived",
            status="archived",
            archival_reason="completed",
            subdir="archive",
        )
        view = _make_view(kanban_dir)
        resp = view.list_tasks(ids=[1, 2])
        ids = [t.id for t in resp.tasks]
        assert 1 in ids, "Active task must be found"
        assert 2 in ids, "Archived task must be found when ids is used"

    def test_ids_found_archived_not_in_missing_ids(self, tmp_path: Path) -> None:
        """AC3: found archived task must not appear in missing_ids."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Active")
        _write_task(
            kanban_dir,
            task_id=2,
            title="Archived",
            status="archived",
            archival_reason="completed",
            subdir="archive",
        )
        view = _make_view(kanban_dir)
        resp = view.list_tasks(ids=[1, 2])
        missing = resp.missing_ids or []
        assert 2 not in missing, "Found archived task must not appear in missing_ids"

    def test_ids_truly_missing_id_in_missing_ids(self, tmp_path: Path) -> None:
        """AC3: ids=[active, archived, missing] → missing_ids=[missing]."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Active")
        _write_task(
            kanban_dir,
            task_id=2,
            title="Archived",
            status="archived",
            archival_reason="completed",
            subdir="archive",
        )
        view = _make_view(kanban_dir)
        resp = view.list_tasks(ids=[1, 2, 999])
        assert resp.missing_ids is not None
        assert 999 in resp.missing_ids
        assert 1 not in resp.missing_ids
        assert 2 not in resp.missing_ids


# ---------------------------------------------------------------------------
# AC1 — show_task on an archived task
# Expectation: engine reads from archive/ when id not found in tasks/.
# Current state: only tasks_dir is searched → FileNotFoundError → NotFoundError.
# ---------------------------------------------------------------------------


class TestFromAC_ShowTaskArchived:
    """AC1: show_task(<archived_id>) returns ShowTaskResponse with archived fields."""

    def test_show_archived_task_returns_response(self, tmp_path: Path) -> None:
        """AC1: show_task on archived task must not raise NotFoundError."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            task_id=5,
            title="Archived Work",
            status="archived",
            archival_reason="completed",
            subdir="archive",
        )
        view = _make_view(kanban_dir)
        resp = view.show_task(5)
        assert isinstance(resp, ShowTaskResponse)

    def test_show_archived_task_id_matches(self, tmp_path: Path) -> None:
        """AC1: returned TaskFull has the correct id."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            task_id=5,
            title="Archived Work",
            status="archived",
            archival_reason="completed",
            subdir="archive",
        )
        view = _make_view(kanban_dir)
        resp = view.show_task(5)
        assert resp.id == 5

    def test_show_archived_task_archival_reason_populated(self, tmp_path: Path) -> None:
        """AC1: archived fields (archival_reason) are present on the response."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            task_id=5,
            title="Archived Work",
            status="archived",
            archival_reason="completed",
            subdir="archive",
        )
        view = _make_view(kanban_dir)
        resp = view.show_task(5)
        assert resp.archival_reason == "completed"

    def test_show_archived_task_status_is_archived(self, tmp_path: Path) -> None:
        """AC1: status field on archived TaskFull is 'archived'."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            task_id=5,
            title="Archived Work",
            status="archived",
            archival_reason="completed",
            subdir="archive",
        )
        view = _make_view(kanban_dir)
        resp = view.show_task(5)
        assert resp.status == "archived"


# ---------------------------------------------------------------------------
# AC12 / D56 — multiple section matches: body concatenated in document order
# Expectation: all matching sections concatenated; current code returns only first.
# Current state: payload["body"] = matches[0].content → FAIL for second match.
# ---------------------------------------------------------------------------


class TestFromAC_ShowTaskSectionConcat:
    """AC12 / D56: Multiple heading matches concatenated in document order.

    Current implementation returns only the first match (matches[0].content).
    D56 requires: all matches serialized back to markdown and concatenated.
    """

    def test_multiple_section_matches_body_contains_all_content(
        self, tmp_path: Path
    ) -> None:
        """Body must include content from every matching heading section."""
        kanban_dir = _make_board(tmp_path)
        body = (
            "## Goals\n"
            "First goal content.\n\n"
            "## Notes\n"
            "Unrelated note.\n\n"
            "## Goals\n"
            "Second goal content.\n"
        )
        _write_task(kanban_dir, task_id=10, title="Multi-Section", body=body)
        view = _make_view(kanban_dir)
        view.engine.list_tasks()  # warm id→filename index
        resp = view.show_task(10, section="Goals")
        assert resp.body is not None
        assert "First goal content." in resp.body
        assert "Second goal content." in resp.body, (
            "D56 requires ALL matches concatenated in document order; "
            "current impl returns only the first section."
        )


# ---------------------------------------------------------------------------
# AC14 — dep_status per §3.3: active dep in different status bucket
# Expectation: dep_status="ok" when dep is active, regardless of status filter.
# Current state: active_ids built from filtered result only → dep in different
# status not found → dep_status="blocked" (wrong). Test FAILS.
# ---------------------------------------------------------------------------


class TestFromAC_DepStatus:
    """AC14: dep_status per §3.3 — all active tasks count as 'active',
    not just those passing the current status filter.
    """

    def test_dep_status_ok_when_dep_active_in_different_status(
        self, tmp_path: Path
    ) -> None:
        """Task A (todo) depends on task B (research). Both active.

        list_tasks(status='todo') must return A with dep_status='ok'.
        §3.3: 'All deps active' → 'ok', regardless of the status filter applied.

        Current bug: active_ids is built from the filtered result only.
        B (research) is not in the filtered result, so the engine checks
        archived_reasons for B, finds it absent, and returns 'blocked'.
        """
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="A", status="todo", depends_on="[2]")
        _write_task(kanban_dir, task_id=2, title="B", status="research")
        view = _make_view(kanban_dir)
        resp = view.list_tasks(status="todo")
        task_a = next((t for t in resp.tasks if t.id == 1), None)
        assert task_a is not None, "Task A (todo) must appear in filtered result"
        assert task_a.dep_status == "ok", (
            f"Dep B is active (research); §3.3 requires dep_status='ok' "
            f"but got {task_a.dep_status!r}"
        )
