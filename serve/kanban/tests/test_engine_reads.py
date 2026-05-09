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

import shutil
from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView
from owlbear_kanban.models import NotFoundError, ShowTaskResponse, ValidationError

# ---------------------------------------------------------------------------
# Board and task helpers
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
        assert "Unrelated note." not in resp.body, (
            "Section filter must exclude non-matching headings from concatenated result"
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

    def test_dep_status_blocked_when_dep_archived_dropped(self, tmp_path: Path) -> None:
        """dep_status='blocked' when dep is archived with reason 'dropped' (§3.3)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="A", status="todo", depends_on="[2]")
        _write_task(
            kanban_dir,
            task_id=2,
            title="B",
            status="archived",
            archival_reason="dropped",
            subdir="archive",
        )
        view = _make_view(kanban_dir)
        resp = view.list_tasks(status="todo")
        task_a = next((t for t in resp.tasks if t.id == 1), None)
        assert task_a is not None, "Task A must appear in todo result"
        assert task_a.dep_status == "blocked", (
            f"Dep B archived with 'dropped'; §3.3 requires dep_status='blocked' "
            f"but got {task_a.dep_status!r}"
        )

    def test_dep_status_redirect_when_dep_archived_duplicate(
        self, tmp_path: Path
    ) -> None:
        """dep_status='redirect' when dep is archived with reason 'duplicate' (§3.3)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="A", status="todo", depends_on="[2]")
        _write_task(
            kanban_dir,
            task_id=2,
            title="B",
            status="archived",
            archival_reason="duplicate",
            subdir="archive",
        )
        view = _make_view(kanban_dir)
        resp = view.list_tasks(status="todo")
        task_a = next((t for t in resp.tasks if t.id == 1), None)
        assert task_a is not None, "Task A must appear in todo result"
        assert task_a.dep_status == "redirect", (
            f"Dep B archived with 'duplicate'; §3.3 requires dep_status='redirect' "
            f"but got {task_a.dep_status!r}"
        )

    def test_dep_status_none_when_task_has_no_deps(self, tmp_path: Path) -> None:
        """dep_status=None when task has no dependencies (§3.3)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="NoDeps", status="todo")
        view = _make_view(kanban_dir)
        resp = view.list_tasks(status="todo")
        task = next((t for t in resp.tasks if t.id == 1), None)
        assert task is not None
        assert task.dep_status is None, (
            f"No deps → dep_status must be None but got {task.dep_status!r}"
        )

    def test_dep_status_blocked_beats_redirect_with_mixed_deps(
        self, tmp_path: Path
    ) -> None:
        """Task with two deps: one archived/dropped (→blocked), one archived/duplicate (→redirect).

        §3.3 precedence: blocked > redirect → result must be 'blocked'.
        """
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir, task_id=1, title="A", status="todo", depends_on="[2, 3]"
        )
        _write_task(
            kanban_dir,
            task_id=2,
            title="DepDropped",
            status="archived",
            archival_reason="dropped",
            subdir="archive",
        )
        _write_task(
            kanban_dir,
            task_id=3,
            title="DepDuplicate",
            status="archived",
            archival_reason="duplicate",
            subdir="archive",
        )
        view = _make_view(kanban_dir)
        resp = view.list_tasks(status="todo")
        task_a = next((t for t in resp.tasks if t.id == 1), None)
        assert task_a is not None
        assert task_a.dep_status == "blocked", (
            f"Mixed deps (dropped+duplicate); §3.3 blocked > redirect → "
            f"expected 'blocked' but got {task_a.dep_status!r}"
        )

    def test_dep_status_redirect_beats_ok_with_mixed_deps(self, tmp_path: Path) -> None:
        """Task with two deps: one archived/duplicate (→redirect), one active (→ok).

        §3.3 precedence: redirect > ok → result must be 'redirect'.
        """
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir, task_id=1, title="A", status="todo", depends_on="[2, 3]"
        )
        _write_task(
            kanban_dir,
            task_id=2,
            title="DepDuplicate",
            status="archived",
            archival_reason="duplicate",
            subdir="archive",
        )
        _write_task(kanban_dir, task_id=3, title="DepActive", status="research")
        view = _make_view(kanban_dir)
        resp = view.list_tasks(status="todo")
        task_a = next((t for t in resp.tasks if t.id == 1), None)
        assert task_a is not None
        assert task_a.dep_status == "redirect", (
            f"Mixed deps (duplicate+active); §3.3 redirect > ok → "
            f"expected 'redirect' but got {task_a.dep_status!r}"
        )


# ---------------------------------------------------------------------------
# AC1 — archival_refs field + warm-cache archive transition (retry gaps)
# ---------------------------------------------------------------------------


class TestFromAC_ShowTaskArchivedFields:
    """AC1 retry: archival_refs field asserted; warm-cache-move scenario covered."""

    def test_show_archived_task_archival_refs_is_list(self, tmp_path: Path) -> None:
        """AC1: archival_refs is present as a list on the returned response."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            task_id=7,
            title="Archived",
            status="archived",
            archival_reason="completed",
            subdir="archive",
        )
        view = _make_view(kanban_dir)
        resp = view.show_task(7)
        assert isinstance(resp.archival_refs, list)
        assert resp.archival_refs == []

    def test_show_archived_task_after_warm_cache_move(self, tmp_path: Path) -> None:
        """AC1: show_task succeeds when active-cached task file is moved to archive.

        Scenario: engine warms _id_to_filename with task in tasks/, then the
        file is moved to archive/ externally. show_task must not raise and must
        return the archived task (stale active-path cache invalidated correctly).
        """
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            task_id=7,
            title="Will Be Archived",
            status="todo",
            subdir="tasks",
        )
        view = _make_view(kanban_dir)
        view.list_tasks()  # warm _id_to_filename + _task_cache for task 7

        src = kanban_dir / "tasks" / "7-task.md"
        dst = kanban_dir / "archive" / "7-task.md"
        shutil.move(str(src), str(dst))

        resp = view.show_task(7)
        assert resp.id == 7


# ---------------------------------------------------------------------------
# AC3 — exact cardinality and exact missing_ids equality (retry gaps)
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksIdsExact:
    """AC3 retry: exact task count and exact missing_ids equality."""

    def test_ids_result_count_is_exactly_two(self, tmp_path: Path) -> None:
        """AC3: ids=[active, archived, missing] → exactly 2 tasks returned."""
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
        assert len(resp.tasks) == 2, (
            f"Expected exactly 2 tasks (active + archived), got {len(resp.tasks)}"
        )

    def test_ids_missing_ids_exact_equality(self, tmp_path: Path) -> None:
        """AC3: missing_ids is exactly [999] — no extra ids, correct value."""
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
        assert resp.missing_ids == [999], (
            f"missing_ids must be exactly [999], got {resp.missing_ids!r}"
        )


# ---------------------------------------------------------------------------
# AC10/11/12 section lookup + validation errors (retry gaps)
# ---------------------------------------------------------------------------


class TestFromAC_ShowTaskSectionLookup:
    """AC10: case-insensitive section. AC11: missing section. ERR_SECTION_EMPTY.
    ERR_NOT_FOUND. AC12: guidance occurrence count (added to existing test class
    below via direct assertion here for orthogonality).
    """

    def test_case_insensitive_section_lookup_returns_content(
        self, tmp_path: Path
    ) -> None:
        """AC10: section='GOALS' matches '## Goals' heading (case-insensitive)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            task_id=11,
            title="CaseTest",
            body="## Goals\nSome goal text.\n\n## Notes\nIrrelevant note.\n",
        )
        view = _make_view(kanban_dir)
        view.engine.list_tasks()  # warm index
        resp = view.show_task(11, section="GOALS")
        assert resp.body is not None, "Case-insensitive match must return body content"
        assert "Some goal text." in resp.body
        assert "Irrelevant note." not in resp.body, (
            "Section filter must exclude unrelated headings"
        )

    def test_missing_section_body_is_none(self, tmp_path: Path) -> None:
        """AC11: section not found → body=None."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            task_id=12,
            title="MissSection",
            body="## Goals\nContent.\n",
        )
        view = _make_view(kanban_dir)
        view.engine.list_tasks()
        resp = view.show_task(12, section="nonexistent")
        assert resp.body is None, "Missing section must return body=None"

    def test_missing_section_populates_missing_sections(self, tmp_path: Path) -> None:
        """AC11: section not found → missing_sections=[section_name]."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            task_id=13,
            title="MissSection2",
            body="## Goals\nContent.\n",
        )
        view = _make_view(kanban_dir)
        view.engine.list_tasks()
        resp = view.show_task(13, section="nonexistent")
        assert resp.missing_sections == ["nonexistent"]

    def test_empty_section_raises_err_section_empty(self, tmp_path: Path) -> None:
        """Empty string section → ValidationError(ERR_SECTION_EMPTY)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=14, title="EmptySection")
        view = _make_view(kanban_dir)
        view.engine.list_tasks()
        with pytest.raises(ValidationError) as exc_info:
            view.show_task(14, section="")
        assert exc_info.value.code == "ERR_SECTION_EMPTY"

    def test_not_found_id_raises_err_not_found(self, tmp_path: Path) -> None:
        """Non-existent task id → NotFoundError(ERR_NOT_FOUND)."""
        kanban_dir = _make_board(tmp_path)
        view = _make_view(kanban_dir)
        with pytest.raises(NotFoundError) as exc_info:
            view.show_task(99999)
        assert exc_info.value.code == "ERR_NOT_FOUND"


# ---------------------------------------------------------------------------
# Default exclusion of archived (retry gap)
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksDefaultExclusion:
    """Default list_tasks() must exclude archived tasks."""

    def test_default_list_excludes_archived_task(self, tmp_path: Path) -> None:
        """Bare list_tasks() must not return archived tasks."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Active", status="todo")
        _write_task(
            kanban_dir,
            task_id=2,
            title="Archived",
            status="archived",
            archival_reason="completed",
            subdir="archive",
        )
        view = _make_view(kanban_dir)
        resp = view.list_tasks()
        ids = [t.id for t in resp.tasks]
        assert 2 not in ids, "Archived task must not appear in default list_tasks()"
        assert 1 in ids, "Active task must appear in default list_tasks()"


# ---------------------------------------------------------------------------
# AC12 guidance occurrence count (added test alongside existing section-concat)
# ---------------------------------------------------------------------------


class TestFromAC_ShowTaskSectionGuidance:
    """AC12: multiple section matches → guidance includes occurrence count."""

    def test_multiple_section_matches_guidance_has_occurrence_count(
        self, tmp_path: Path
    ) -> None:
        """AC12: guidance must mention occurrence count when >1 sections matched."""
        kanban_dir = _make_board(tmp_path)
        body = "## Goals\nFirst goal.\n\n## Notes\nA note.\n\n## Goals\nSecond goal.\n"
        _write_task(kanban_dir, task_id=20, title="GuidanceTest", body=body)
        view = _make_view(kanban_dir)
        view.engine.list_tasks()
        resp = view.show_task(20, section="Goals")
        assert resp.guidance, "guidance must be non-empty for multiple section matches"
        assert any("2 occurrences" in g for g in resp.guidance), (
            f"guidance must include numeric occurrence count; got {resp.guidance!r}"
        )
