"""Tests for task #952: Fix end_work() detail format for session classification.

AC coverage:
  1. end_work(outcome="success") writes detail f"success: {old} -> {new}"
  2. end_work(outcome="reject") writes detail f"reject: {old} -> {target}"
  3. end_work(outcome="fail") / end_work(outcome="block") details unchanged
  4. Existing _classify_end_work() works without modification
    5. Integration: end_work(success) → list_sessions(filter="all") returns completed
    6. Integration: end_work(reject) → list_sessions(filter="all") returns rejected

AC1/AC2/AC5/AC6 tests FAIL in RED phase — end_work() writes unprefixed detail strings.
AC3 tests exercise already-correct behaviour (fail/block were never changed) and PASS
in both RED and GREEN phases; they are regression guards ensuring the builder cannot
accidentally alter the fail/block format strings.
AC4 is exercised transitively by the AC5/AC6 integration tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine

# ---------------------------------------------------------------------------
# Board / task helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
version: 10
board:
  name: TestBoard
tasks_dir: tasks
statuses:
- name: research
- name: backlog
- name: todo
- name: in-progress
- name: review
- name: docs
- name: done
priorities:
- someday
- nice-to-have
- important
- needed
- critical
defaults:
  status: research
  priority: important
claim_timeout: 1h
next_id: 10
archive_dir: archive
activity_log: true
"""

_TASK_TEMPLATE = """\
---
id: {task_id}
title: "Task {task_id}"
status: {status}
priority: important
created: 2026-04-18T10:00:00.000000+00:00
updated: 2026-04-18T10:00:00.000000+00:00
tags: []
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Task body.
"""


def _make_board(base_dir: Path) -> Path:
    """Create a minimal board with activity_log enabled. Returns kanban_dir."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write_task(kanban_dir: Path, task_id: int, status: str = "todo") -> None:
    """Write a synthetic task file into the board's tasks directory."""
    content = _TASK_TEMPLATE.format(task_id=task_id, status=status)
    slug = f"{task_id}-task-{task_id}.md"
    (kanban_dir / "tasks" / slug).write_text(content, encoding="utf-8")


def _last_end_work_detail(log_path: Path) -> str:
    """Return the detail field of the last end_work entry in the activity log."""
    entries = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    end_work_entries = [e for e in entries if e.get("action") == "end_work"]
    assert end_work_entries, "No end_work entry found in activity log"
    return end_work_entries[-1]["detail"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def board(tmp_path: Path) -> Path:
    """Minimal board with activity_log=true. Returns kanban_dir."""
    return _make_board(tmp_path)


@pytest.fixture
def engine(board: Path) -> KanbanEngine:
    """KanbanEngine for the board fixture."""
    return KanbanEngine(board, agent_name="test-agent", activity_log=True)


@pytest.fixture
def log_path(board: Path) -> Path:
    """Path to activity.jsonl inside the board fixture."""
    return board / "activity.jsonl"


# ---------------------------------------------------------------------------
# TestFromAC_EndWorkDetailPrefix
# ---------------------------------------------------------------------------


class TestFromAC_EndWorkDetailPrefix:
    """Verifies end_work() detail prefix contract per task #952 AC."""

    # ------------------------------------------------------------------ AC1: success prefix

    def test_end_work_success_detail_has_success_prefix(
        self, board: Path, engine: KanbanEngine, log_path: Path
    ) -> None:
        """end_work(success) writes a detail string that starts with 'success:'."""
        _write_task(board, 1, status="todo")
        engine.start_work("1")
        engine.end_work("1", note="done", outcome="success")

        detail = _last_end_work_detail(log_path)
        assert detail.startswith("success:"), (
            f"Expected detail to start with 'success:' but got: {detail!r}"
        )

    def test_end_work_success_detail_exact_format(
        self, board: Path, engine: KanbanEngine, log_path: Path
    ) -> None:
        """end_work(success) detail is exactly 'success: {old} -> {new}'."""
        _write_task(board, 2, status="todo")
        engine.start_work("2")
        engine.end_work("2", note="done", outcome="success")

        detail = _last_end_work_detail(log_path)
        assert detail == "success: todo -> in-progress", (
            f"Expected 'success: todo -> in-progress' but got: {detail!r}"
        )

    def test_end_work_success_from_non_todo_status(
        self, board: Path, engine: KanbanEngine, log_path: Path
    ) -> None:
        """end_work(success) reflects the actual old status in the prefix."""
        _write_task(board, 3, status="in-progress")
        engine.start_work("3")
        engine.end_work("3", note="done", outcome="success")

        detail = _last_end_work_detail(log_path)
        assert detail == "success: in-progress -> review", (
            f"Expected 'success: in-progress -> review' but got: {detail!r}"
        )

    # ------------------------------------------------------------------ AC2: reject prefix

    def test_end_work_reject_detail_has_reject_prefix(
        self, board: Path, engine: KanbanEngine, log_path: Path
    ) -> None:
        """end_work(reject) writes a detail string that starts with 'reject:'."""
        _write_task(board, 4, status="todo")
        engine.start_work("4")
        engine.end_work("4", note="rejected", outcome="reject", move_to="research")

        detail = _last_end_work_detail(log_path)
        assert detail.startswith("reject:"), (
            f"Expected detail to start with 'reject:' but got: {detail!r}"
        )

    def test_end_work_reject_detail_exact_format(
        self, board: Path, engine: KanbanEngine, log_path: Path
    ) -> None:
        """end_work(reject) detail is exactly 'reject: {old} -> {target}'."""
        _write_task(board, 5, status="todo")
        engine.start_work("5")
        engine.end_work("5", note="rejected", outcome="reject", move_to="research")

        detail = _last_end_work_detail(log_path)
        assert detail == "reject: todo -> research", (
            f"Expected 'reject: todo -> research' but got: {detail!r}"
        )

    def test_end_work_reject_detail_reflects_explicit_move_to(
        self, board: Path, engine: KanbanEngine, log_path: Path
    ) -> None:
        """end_work(reject, move_to='backlog') detail shows the explicit target."""
        _write_task(board, 6, status="in-progress")
        engine.start_work("6")
        engine.end_work("6", note="rejected", outcome="reject", move_to="backlog")

        detail = _last_end_work_detail(log_path)
        assert detail == "reject: in-progress -> backlog", (
            f"Expected 'reject: in-progress -> backlog' but got: {detail!r}"
        )

    # ------------------------------------------------------------------ AC5: integration success → completed

    def test_integration_end_work_success_classifies_as_completed_pass(
        self, board: Path, engine: KanbanEngine
    ) -> None:
        """Integration: start_work → end_work(success) → list_sessions returns completed."""
        _write_task(board, 7, status="todo")
        engine.start_work("7")
        engine.end_work("7", note="done", outcome="success")

        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 7]
        assert task_sessions, "No session found for task 7"
        assert task_sessions[-1].state == "completed", (
            f"Expected 'completed' but got: {task_sessions[-1].state!r}"
        )

    def test_integration_end_work_success_not_misclassified_as_completed_fail(
        self, board: Path, engine: KanbanEngine
    ) -> None:
        """Regression: end_work(success) must NOT produce blocked."""
        _write_task(board, 8, status="todo")
        engine.start_work("8")
        engine.end_work("8", note="done", outcome="success")

        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 8]
        assert task_sessions, "No session found for task 8"
        assert task_sessions[-1].state != "blocked", (
            "end_work(success) was misclassified as blocked"
        )

    # ------------------------------------------------------------------ AC6: integration reject → rejected

    def test_integration_end_work_reject_classifies_as_completed_rejected(
        self, board: Path, engine: KanbanEngine
    ) -> None:
        """Integration: start_work → end_work(reject) → list_sessions returns rejected."""
        _write_task(board, 9, status="todo")
        engine.start_work("9")
        engine.end_work("9", note="rejected", outcome="reject", move_to="research")

        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 9]
        assert task_sessions, "No session found for task 9"
        assert task_sessions[-1].state == "rejected", (
            f"Expected 'rejected' but got: {task_sessions[-1].state!r}"
        )

    def test_integration_end_work_reject_not_misclassified_as_completed_fail(
        self, board: Path, engine: KanbanEngine
    ) -> None:
        """Regression: end_work(reject) must NOT produce blocked."""
        _write_task(board, 10, status="todo")
        engine.start_work("10")
        engine.end_work("10", note="rejected", outcome="reject", move_to="research")

        sessions = engine.list_sessions(filter="all")
        task_sessions = [s for s in sessions if s.task_id == 10]
        assert task_sessions, "No session found for task 10"
        assert task_sessions[-1].state != "blocked", (
            "end_work(reject) was misclassified as blocked"
        )

    # ------------------------------------------------------------------ AC3: fail/block details unchanged

    def test_end_work_fail_detail_is_outcome_equals_fail(
        self, board: Path, engine: KanbanEngine, log_path: Path
    ) -> None:
        """end_work(fail) writes detail 'outcome=fail' — unchanged from pre-fix format."""
        _write_task(board, 1, status="in-progress")
        engine.start_work("1")
        engine.end_work("1", note="failed", outcome="fail")

        detail = _last_end_work_detail(log_path)
        assert detail == "outcome=fail", f"Expected 'outcome=fail' but got: {detail!r}"

    def test_end_work_block_detail_is_blocked_with_reason(
        self, board: Path, engine: KanbanEngine, log_path: Path
    ) -> None:
        """end_work(block) writes detail 'blocked: {reason}' — unchanged from pre-fix format."""
        _write_task(board, 1, status="in-progress")
        engine.start_work("1")
        engine.end_work(
            "1",
            note="blocked",
            outcome="block",
            block_reason="external dependency",
        )

        detail = _last_end_work_detail(log_path)
        assert detail == "blocked: external dependency", (
            f"Expected 'blocked: external dependency' but got: {detail!r}"
        )
