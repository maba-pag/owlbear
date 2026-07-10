# --- merged from tests/test_engine_create_edit_1072.py ---
"""RED-phase tests for AgentView.edit_task — semantic diff / D14 (task #1072).

Task #1072 (B-08: GREEN) adds two AC items beyond what #1070 covers:

  D14 — `updated` advanced on any successful change (contract that prevents
         semantic no-ops silently advancing the timestamp).

  D46 — AgentView.edit_task has NO `expected_updated` param (last-writer-wins).
         D46 is already satisfied by the current implementation (the param does not
         exist); no failing test can be written — documented here for audit trail.

  "engine computes diff" — edit_task must detect semantic no-ops (proposed
  value == current value) and raise ERR_NO_OP, not silently write the same
  data and advance `updated`.

AC coverage:
  D14  → TestFromAC_EditTaskSemanticDiff.test_same_priority_raises_no_op
          TestFromAC_EditTaskSemanticDiff.test_add_existing_tag_raises_no_op
          TestFromAC_EditTaskSemanticDiff.test_remove_nonexistent_dep_raises_no_op
          TestFromAC_EditTaskSemanticDiff.test_add_existing_dep_raises_no_op
          TestFromAC_EditTaskSemanticDiff.test_same_body_raises_no_op
          TestFromAC_EditTaskSemanticDiff.test_remove_nonexistent_tag_raises_no_op
  D46  → Not testable as RED: AgentView.edit_task already lacks `expected_updated`.
"""

from __future__ import annotations


from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView
from owlbear_kanban.errors import KANBAN_ERROR_CODES
from owlbear_kanban.models import ValidationError

# ---------------------------------------------------------------------------
# Board + task fixtures (mirrors conventions from test_engine_create_edit_1070.py)
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
parent: {parent}
depends_on: {depends_on}
blocked: {blocked}
block_reason: {block_reason}
claimed_at: null
archival_reason: {archival_reason}
archival_refs: {archival_refs}
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
    task_id: int = 1,
    title: str = "Task",
    status: str = "todo",
    priority: str = "needed",
    tags: str = "[]",
    blocked: str = "false",
    block_reason: str = "null",
    depends_on: str = "[]",
    body: str = "Body.",
    parent: str = "null",
    archival_reason: str = "null",
    archival_refs: str = "[]",
    subdir: str = "tasks",
) -> Path:
    content = _TASK_TMPL.format(
        task_id=task_id,
        title=title,
        status=status,
        priority=priority,
        tags=tags,
        blocked=blocked,
        block_reason=block_reason,
        depends_on=depends_on,
        body=body,
        parent=parent,
        archival_reason=archival_reason,
        archival_refs=archival_refs,
    )
    dest_dir = kanban_dir / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"{task_id}-task.md"
    path.write_text(content, encoding="utf-8")
    return path


def _make_view(base_dir: Path) -> tuple[AgentView, Path]:
    kanban_dir = _make_board(base_dir)
    engine = KanbanEngine(kanban_dir, activity_log=False)
    return AgentView(engine), kanban_dir


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskSemanticDiff
#
# "engine computes diff" (D14 + no-op AC) — proposed value == current value
# must raise ERR_NO_OP, not silently write identical data and advance `updated`.
#
# All tests are RED: the current implementation does not compute a semantic diff;
# it checks only whether any kwargs were supplied, not whether the kwargs would
# produce any actual change.
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskSemanticDiff:
    """Semantic no-op detection: edit_task must compute a field-level diff
    and raise ERR_NO_OP when no field would actually change."""

    def test_same_priority_raises_no_op(self, tmp_path: Path) -> None:
        """D14/diff: edit_task(priority=X) when task.priority == X → ERR_NO_OP.

        The proposed change is identical to the current value; no data would
        change. Current impl writes the same value and advances `updated` without
        raising ERR_NO_OP.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, priority="needed")
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, priority="needed")
        assert exc_info.value.code == "ERR_NO_OP"

    def test_add_existing_tag_raises_no_op(self, tmp_path: Path) -> None:
        """D14/diff: edit_task(add_tag=["t"]) when task.tags already contains "t" → ERR_NO_OP.

        Adding a tag that is already present produces no net change.
        Current impl adds the tag to kwargs, calls engine.edit_task (which deduplicates),
        and advances `updated` without raising ERR_NO_OP.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, tags='["phase:engine"]')
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, add_tag=["phase:engine"])
        assert exc_info.value.code == "ERR_NO_OP"

    def test_remove_nonexistent_tag_raises_no_op(self, tmp_path: Path) -> None:
        """D14/diff: edit_task(remove_tag=["absent"]) when task.tags does not contain
        "absent" → ERR_NO_OP.

        Removing a tag that is not present produces no net change.
        Current impl passes remove_tags to engine which filters an already-absent tag
        silently, advancing `updated` without raising ERR_NO_OP.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, tags="[]")
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, remove_tag=["absent-tag"])
        assert exc_info.value.code == "ERR_NO_OP"

    def test_add_existing_dep_raises_no_op(self, tmp_path: Path) -> None:
        """D14/diff: edit_task(add_dep=[2]) when task.depends_on already contains 2 → ERR_NO_OP.

        Adding a dependency that is already tracked produces no net change.
        Current impl deduplicates in engine.edit_task but still advances `updated`.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=2)  # dependency target must exist
        _write_task(kanban_dir, task_id=1, depends_on="[2]")
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, add_dep=[2])
        assert exc_info.value.code == "ERR_NO_OP"

    def test_remove_nonexistent_dep_raises_no_op(self, tmp_path: Path) -> None:
        """D14/diff: edit_task(remove_dep=[99]) when task.depends_on does not contain 99 →
        ERR_NO_OP.

        Removing a dependency that is not tracked produces no net change.
        Current impl passes remove_deps to engine which filters an already-absent ID
        silently, advancing `updated` without raising ERR_NO_OP.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, depends_on="[]")
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, remove_dep=[99999])
        assert exc_info.value.code == "ERR_NO_OP"

    def test_same_body_raises_no_op(self, tmp_path: Path) -> None:
        """D14/diff: edit_task(body=X) when task.body == X → ERR_NO_OP.

        Replacing the body with an identical string produces no net change.
        Current impl adds the body to kwargs and calls engine.edit_task which
        writes the same content and advances `updated` without raising ERR_NO_OP.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, body="Existing body content.")
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, body="Existing body content.")
        assert exc_info.value.code == "ERR_NO_OP"


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskArchivedNoOp
#
# Regression proof (added in retry cycle per reviewer + builder findings):
# same-value archival_reason / archival_refs on an archived task must raise
# ERR_NO_OP, not silently write identical data.
#
# The archived-status short-circuit that caused these to slip through was
# removed by the builder before this test class was authored.  Tests pass on
# the current implementation and guard against regression.
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskArchivedNoOp:
    """Archived-task semantic no-op: same archival_reason or archival_refs → ERR_NO_OP."""

    def test_same_archival_reason_on_archived_raises_no_op(self, tmp_path: Path) -> None:
        """Archived task: edit_task(archival_reason="dropped") when reason already "dropped" → ERR_NO_OP.

        Sending an identical archival_reason must not advance `updated` or rewrite
        the task file.  Regression guard for the archived-status short-circuit fix.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason="dropped",
            archival_refs="[]",
            subdir="archive",
        )
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, archival_reason="dropped")
        assert exc_info.value.code == "ERR_NO_OP"

    def test_same_archival_refs_on_archived_raises_no_op(self, tmp_path: Path) -> None:
        """Archived task: edit_task(archival_refs=[2]) when refs already [2] → ERR_NO_OP.

        Sending an identical archival_refs list must not advance `updated` or rewrite
        the task file.  Regression guard for the archived-status short-circuit fix.
        Task uses archival_reason "duplicate" (which requires refs) to satisfy the
        archival-matrix validation before the no-op check can fire.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=2)  # reference target must exist
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason="duplicate",
            archival_refs="[2]",
            subdir="archive",
        )
        with pytest.raises(ValidationError) as exc_info:
            view.edit_task(1, archival_refs=[2])
        assert exc_info.value.code == "ERR_NO_OP"


# ---------------------------------------------------------------------------
# TestFromAC_D46NoExpectedUpdatedParam
#
# D46 executable proof (added in retry cycle per reviewer finding):
# AgentView.edit_task must NOT accept an `expected_updated` parameter.
# The param was never present; this test guards against accidental re-addition.
# ---------------------------------------------------------------------------


class TestFromAC_D46NoExpectedUpdatedParam:
    """D46 regression proof: AgentView.edit_task rejects unexpected `expected_updated` kwarg."""

    def test_edit_task_rejects_expected_updated_kwarg(self, tmp_path: Path) -> None:
        """D46: AgentView.edit_task(..., expected_updated=...) raises TypeError.

        The `expected_updated` parameter must never appear in the AgentView signature
        (last-writer-wins contract).  Passing it must produce a TypeError at call time.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1)
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            view.edit_task(1, priority="someday", expected_updated="2026-01-01T10:00:00+00:00")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# TestFromAC_CreateTaskStatusParam
#
# AgentView.create_task accepts an optional `status` parameter for shaped
# routing. Omitting it still creates tasks at BoardConfig.entry_status.
# ---------------------------------------------------------------------------


class TestFromAC_CreateTaskStatusParam:
    """AgentView.create_task supports explicit routing and entry-status defaulting."""

    def test_create_task_accepts_status_kwarg(self, tmp_path: Path) -> None:
        """Explicit status routes a task directly to a valid pipeline gate."""
        view, _kanban_dir = _make_view(tmp_path)
        task = view.create_task(title="Task", status="build")
        assert task.status == "build"

    def test_create_task_without_status_uses_entry_status(self, tmp_path: Path) -> None:
        """Omitted status remains the default shape intake path."""
        view, _kanban_dir = _make_view(tmp_path)
        task = view.create_task(title="Task")
        assert task.status == "shape"


# --- merged from tests/test_engine_create_edit_1203.py ---
"""RED-phase tests for AgentView.create_task empty-title error code fix (task #1203).

Covers:
  AC1 → TestFromAC_EmptyTitleErrorCode.test_err_invalid_title_in_kanban_error_codes
  AC2 → TestFromAC_EmptyTitleErrorCode.test_create_task_empty_title_raises_err_invalid_title
  AC2 → TestFromAC_EmptyTitleErrorCode.test_create_task_whitespace_title_raises_err_invalid_title
"""

# ---------------------------------------------------------------------------
# Minimal board setup helpers (mirrors test_engine_create_edit_1070.py)
# ---------------------------------------------------------------------------

_BASE_CONFIG_1203 = """\
next_id: 1
"""


def _make_view_1203(base_dir: Path) -> AgentView:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_BASE_CONFIG_1203, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    engine = KanbanEngine(kanban_dir, activity_log=False)
    return AgentView(engine)


# ---------------------------------------------------------------------------
# TestFromAC_EmptyTitleErrorCode
# ---------------------------------------------------------------------------


class TestFromAC_EmptyTitleErrorCode:
    """AC1: ERR_INVALID_TITLE in KANBAN_ERROR_CODES.
    AC2: create_task raises ValidationError(code="ERR_INVALID_TITLE") for empty/whitespace titles.
    """

    def test_err_invalid_title_in_kanban_error_codes(self) -> None:
        """AC1: 'ERR_INVALID_TITLE' must be a member of the KANBAN_ERROR_CODES frozenset."""
        assert "ERR_INVALID_TITLE" in KANBAN_ERROR_CODES

    def test_create_task_empty_title_raises_err_invalid_title(self, tmp_path: Path) -> None:
        """AC2: create_task with empty title raises ValidationError with code ERR_INVALID_TITLE."""
        view = _make_view_1203(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            view.create_task(title="")
        assert exc_info.value.code == "ERR_INVALID_TITLE"
        assert exc_info.value.user_message == "title must not be empty"

    def test_create_task_whitespace_title_raises_err_invalid_title(self, tmp_path: Path) -> None:
        """AC2: create_task with whitespace-only title raises ValidationError(ERR_INVALID_TITLE)."""
        view = _make_view_1203(tmp_path)
        with pytest.raises(ValidationError) as exc_info:
            view.create_task(title="   ")
        assert exc_info.value.code == "ERR_INVALID_TITLE"
        assert exc_info.value.user_message == "title must not be empty"
