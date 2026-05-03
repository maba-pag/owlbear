"""RED-phase tests for task #1214: port TDD and clarity gates to AgentView.pick_tasks.

AC coverage:
- AC1: pick_tasks() applies TDD gate in filter stage (before sort/wave) (td:2)
- AC2: pick_tasks() applies clarity gate in filter stage (before sort/wave) (td:2)
- AC3: Gate predicates imported from dispatch.py — no duplication (td:1)
- AC4: pick_dispatchable() emits DeprecationWarning via warnings.warn() (td:1)
- AC5: pick_dispatchable in owlbear_kanban.__all__ — SKIPPED (td:0)
- AC6: Wave-assembly, agent-bucket, and sort logic unchanged — regression guard (td:1)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.dispatch import pick_dispatchable
from owlbear_kanban.engine import AgentView
from owlbear_kanban.models import PickTasksResponse

# ---------------------------------------------------------------------------
# Fixtures / helpers
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
next_id: 20
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


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_BASE_CONFIG, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_engine(base_dir: Path) -> KanbanEngine:
    return KanbanEngine(_make_board(base_dir), activity_log=False)


def _make_view(base_dir: Path) -> AgentView:
    return AgentView(_make_engine(base_dir))


def _write_task(  # noqa: PLR0913
    tasks_dir: Path,
    *,
    task_id: int,
    title: str,
    status: str,
    priority: str = "needed",
    tags: list[str] | None = None,
    body: str = "",
) -> None:
    """Write a minimal valid task file to tasks_dir."""
    tag_items = "\n".join(f"  - {tag}" for tag in (tags or []))
    tags_block = f"tags:\n{tag_items}\n" if tags else "tags: []\n"
    content = (
        "---\n"
        f"id: {task_id}\n"
        f"title: {title}\n"
        f"status: {status}\n"
        f"priority: {priority}\n"
        "created: 2024-01-01T00:00:00+00:00\n"
        "updated: 2024-01-01T00:00:00+00:00\n"
        f"{tags_block}"
        "---\n"
        f"{body}"
    )
    (tasks_dir / f"{task_id}-task.md").write_text(content, encoding="utf-8")


def _all_task_ids(response: PickTasksResponse) -> set[int]:
    """Return the set of task IDs across all waves."""
    return {entry.id for wave in response.waves for entry in wave.tasks}


# ---------------------------------------------------------------------------
# AC1: TDD gate applied in pick_tasks filter stage
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksTDDGate:
    """AC1: in-progress tasks without ## Test-Writer Notes AND without non-impl tag
    must be excluded from pick_tasks output (gated before sort/wave assembly).
    """

    def test_tdd_gate_excludes_in_progress_without_notes_section(
        self, tmp_path: Path
    ) -> None:
        """Error path: in-progress task with bullets but no ## Test-Writer Notes → excluded.

        Currently: pick_tasks includes it (no TDD gate applied).
        After fix: excluded from all waves.
        """
        board = _make_board(tmp_path)
        _write_task(
            board / "tasks",
            task_id=1,
            title="No TDD notes",
            status="in-progress",
            body="## AC\n- item one\n- item two\n",
        )
        view = AgentView(KanbanEngine(board, activity_log=False))

        result = view.pick_tasks()

        assert 1 not in _all_task_ids(result), (
            "pick_tasks must exclude in-progress tasks without ## Test-Writer Notes"
        )

    def test_tdd_gate_excludes_in_progress_with_empty_body(
        self, tmp_path: Path
    ) -> None:
        """Boundary: in-progress task with empty body → excluded by TDD gate.

        Currently: pick_tasks includes it.
        After fix: excluded.
        """
        board = _make_board(tmp_path)
        _write_task(
            board / "tasks",
            task_id=2,
            title="Empty body in-progress",
            status="in-progress",
            body="",
        )
        view = AgentView(KanbanEngine(board, activity_log=False))

        result = view.pick_tasks()

        assert 2 not in _all_task_ids(result), (
            "pick_tasks must exclude in-progress tasks with no body (fails TDD gate)"
        )

    def test_tdd_gate_passes_in_progress_with_notes_section(
        self, tmp_path: Path
    ) -> None:
        """Happy path: in-progress WITH ## Test-Writer Notes → included.
        Gated task (no notes) in same board must not appear.

        Currently: BOTH tasks appear (no gate). After fix: only notes-bearing task appears.
        Test fails now because the gated task (id=4) appears in waves.
        """
        board = _make_board(tmp_path)
        tasks_dir = board / "tasks"
        _write_task(
            tasks_dir,
            task_id=3,
            title="Has TDD notes",
            status="in-progress",
            body="## Test-Writer Notes\n- covered\n\n## AC\n- item one\n",
        )
        _write_task(
            tasks_dir,
            task_id=4,
            title="No TDD notes — should be gated",
            status="in-progress",
            body="## AC\n- item one\n",
        )
        view = AgentView(KanbanEngine(board, activity_log=False))

        result = view.pick_tasks()

        assert 4 not in _all_task_ids(result), (
            "in-progress task without ## Test-Writer Notes must be excluded by TDD gate"
        )

    def test_tdd_gate_non_impl_tag_bypasses_tdd_gate(
        self, tmp_path: Path
    ) -> None:
        """Edge: in-progress + non-impl tag (research) without notes → passes TDD gate.
        Alongside a task that fails TDD gate, the non-impl tag task should appear
        but the untagged one must not.

        Test fails now because the untagged in-progress task (id=6) still appears.
        """
        board = _make_board(tmp_path)
        tasks_dir = board / "tasks"
        _write_task(
            tasks_dir,
            task_id=5,
            title="Research tag exempts from TDD gate",
            status="in-progress",
            tags=["research"],
            body="## AC\n- item one\n",
        )
        _write_task(
            tasks_dir,
            task_id=6,
            title="No tag, no notes — gated out",
            status="in-progress",
            body="## AC\n- item one\n",
        )
        view = AgentView(KanbanEngine(board, activity_log=False))

        result = view.pick_tasks()

        assert 6 not in _all_task_ids(result), (
            "in-progress task without notes or non-impl tag must be excluded"
        )

    def test_tdd_gate_only_applies_to_in_progress_status(
        self, tmp_path: Path
    ) -> None:
        """Edge: non-in-progress task (todo) without ## Test-Writer Notes is NOT subject
        to TDD gate. Must appear in waves if it passes clarity gate.
        Alongside a gated in-progress task, the gated one must not appear.

        Test fails now because the gated in-progress task (id=8) still appears.
        """
        board = _make_board(tmp_path)
        tasks_dir = board / "tasks"
        _write_task(
            tasks_dir,
            task_id=7,
            title="Todo without notes — passes (todo not gated by TDD)",
            status="todo",
            body="## AC\n- item one\n",
        )
        _write_task(
            tasks_dir,
            task_id=8,
            title="In-progress without notes — TDD gated",
            status="in-progress",
            body="## AC\n- item one\n",
        )
        view = AgentView(KanbanEngine(board, activity_log=False))

        result = view.pick_tasks()

        assert 8 not in _all_task_ids(result), (
            "in-progress task without notes must be excluded even when todo peers are present"
        )


# ---------------------------------------------------------------------------
# AC2: Clarity gate applied in pick_tasks filter stage
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksClarityGate:
    """AC2: tasks in {todo, in-progress, review, docs, done} without a bullet or
    numbered AC line must be excluded from pick_tasks output.
    """

    def test_clarity_gate_excludes_todo_with_prose_only_body(
        self, tmp_path: Path
    ) -> None:
        """Error path: todo task with prose-only body (no bullets) → excluded.

        Currently: pick_tasks includes it.
        After fix: excluded.
        """
        board = _make_board(tmp_path)
        _write_task(
            board / "tasks",
            task_id=10,
            title="Todo prose only",
            status="todo",
            body="This task has no bullet points at all. Just prose.",
        )
        view = AgentView(KanbanEngine(board, activity_log=False))

        result = view.pick_tasks()

        assert 10 not in _all_task_ids(result), (
            "pick_tasks must exclude todo tasks with no bullet/numbered AC line"
        )

    def test_clarity_gate_excludes_done_task_without_bullets(
        self, tmp_path: Path
    ) -> None:
        """Error path: done task with prose-only body → excluded.

        done is in _CLARITY_STATUSES; tasks without bullets must be excluded.
        Currently: pick_tasks includes it.
        After fix: excluded.
        """
        board = _make_board(tmp_path)
        _write_task(
            board / "tasks",
            task_id=11,
            title="Done task prose only",
            status="done",
            body="Prose without bullets.",
        )
        view = AgentView(KanbanEngine(board, activity_log=False))

        result = view.pick_tasks()

        assert 11 not in _all_task_ids(result), (
            "pick_tasks must exclude done tasks with no bullet/numbered AC line"
        )

    def test_clarity_gate_passes_todo_with_bullet_ac(
        self, tmp_path: Path
    ) -> None:
        """Happy path: todo task with bullet AC line → included.
        Alongside a gated task (prose-only todo) that must be excluded.

        Test fails now because the gated task (id=13) still appears.
        """
        board = _make_board(tmp_path)
        tasks_dir = board / "tasks"
        _write_task(
            tasks_dir,
            task_id=12,
            title="Todo with bullets — passes clarity gate",
            status="todo",
            body="## AC\n- item one\n- item two\n",
        )
        _write_task(
            tasks_dir,
            task_id=13,
            title="Todo prose only — clarity gated",
            status="todo",
            body="No bullets here at all.",
        )
        view = AgentView(KanbanEngine(board, activity_log=False))

        result = view.pick_tasks()

        assert 13 not in _all_task_ids(result), (
            "todo task without bullets must be excluded by clarity gate"
        )

    def test_clarity_gate_backlog_not_subject_to_gate(
        self, tmp_path: Path
    ) -> None:
        """Edge: backlog task without bullets → passes clarity gate (not in _CLARITY_STATUSES).
        A todo without bullets in same board must still be excluded.

        Test fails because the gated todo task (id=15) currently appears.
        """
        board = _make_board(tmp_path)
        tasks_dir = board / "tasks"
        _write_task(
            tasks_dir,
            task_id=14,
            title="Backlog no bullets — passes (backlog exempt from clarity gate)",
            status="backlog",
            body="Prose only, no bullets needed.",
        )
        _write_task(
            tasks_dir,
            task_id=15,
            title="Todo no bullets — clarity gated",
            status="todo",
            body="Just prose here.",
        )
        view = AgentView(KanbanEngine(board, activity_log=False))

        result = view.pick_tasks()

        assert 15 not in _all_task_ids(result), (
            "todo task without bullets must be excluded; backlog exemption must not mask it"
        )

    def test_clarity_gate_numbered_ac_line_qualifies(
        self, tmp_path: Path
    ) -> None:
        """Boundary: numbered list item (1. text) qualifies as AC line — task passes.
        Alongside a gated prose-only todo that must be excluded.

        Test fails because the gated task (id=17) currently appears.
        """
        board = _make_board(tmp_path)
        tasks_dir = board / "tasks"
        _write_task(
            tasks_dir,
            task_id=16,
            title="Todo with numbered AC",
            status="todo",
            body="1. do this\n2. do that\n",
        )
        _write_task(
            tasks_dir,
            task_id=17,
            title="Todo prose only — clarity gated",
            status="todo",
            body="Pure prose, no list items.",
        )
        view = AgentView(KanbanEngine(board, activity_log=False))

        result = view.pick_tasks()

        assert 17 not in _all_task_ids(result), (
            "todo task without any list items must be excluded by clarity gate"
        )


# ---------------------------------------------------------------------------
# AC3: Gate predicates imported from dispatch.py (no duplication)
# ---------------------------------------------------------------------------


class TestFromAC_GateImportedFromDispatch:
    """AC3: pick_tasks must use _passes_tdd_gate from dispatch.py.
    Patching dispatch._passes_tdd_gate to return False must cause in-progress
    tasks (with notes) to be excluded from pick_tasks output.

    Test fails now because pick_tasks does not call dispatch._passes_tdd_gate.
    """

    def test_tdd_gate_predicate_from_dispatch_controls_pick_tasks(
        self, tmp_path: Path
    ) -> None:
        """Patching dispatch._passes_tdd_gate to always False must exclude a
        normally-passing in-progress task from pick_tasks.

        This verifies the gate is not reimplemented inline in engine.py but
        imported and called from dispatch.py.

        Currently: pick_tasks does not call dispatch._passes_tdd_gate at all →
        patching has no effect → task appears in waves → assertion FAILS.
        """
        board = _make_board(tmp_path)
        _write_task(
            board / "tasks",
            task_id=1,
            title="Normally passes TDD gate",
            status="in-progress",
            body="## Test-Writer Notes\n- covered\n\n## AC\n- item one\n",
        )
        view = AgentView(KanbanEngine(board, activity_log=False))

        with patch(
            "owlbear_kanban.dispatch._passes_tdd_gate", return_value=False
        ):
            result = view.pick_tasks()

        assert 1 not in _all_task_ids(result), (
            "pick_tasks must use _passes_tdd_gate from dispatch.py; "
            "patching the predicate must gate the task out"
        )


# ---------------------------------------------------------------------------
# AC4: pick_dispatchable() emits DeprecationWarning
# ---------------------------------------------------------------------------


class TestFromAC_PickDispatchableDeprecation:
    """AC4: pick_dispatchable() must emit DeprecationWarning via warnings.warn()."""

    def test_pick_dispatchable_emits_deprecation_warning(
        self, tmp_path: Path
    ) -> None:
        """pick_dispatchable() call must produce exactly one DeprecationWarning.

        Currently: no warning is emitted → pytest.warns() context raises AssertionError.
        After fix: warnings.warn() fires at call entry.
        """
        engine = _make_engine(tmp_path)

        with pytest.warns(DeprecationWarning, match="pick_dispatchable"):
            pick_dispatchable(engine)


# ---------------------------------------------------------------------------
# AC6: Wave-assembly, sort logic unchanged — regression guard
# ---------------------------------------------------------------------------


class TestFromAC_WaveAssemblyRegressionGuard:
    """AC6: Adding gates must not disturb wave-assembly or sort logic.
    Tasks that pass all gates must still be sorted by priority and placed into
    waves as before.
    """

    def test_gated_task_excluded_wave_assembly_slot_unaffected(
        self, tmp_path: Path
    ) -> None:
        """Gated task must not consume a wave slot; passing task must still appear.

        Currently: gated in-progress task (id=2) appears → assertion on id=2 FAILS.
        After fix: id=1 in waves, id=2 not in waves.
        """
        board = _make_board(tmp_path)
        tasks_dir = board / "tasks"
        _write_task(
            tasks_dir,
            task_id=1,
            title="Passes all gates",
            status="todo",
            priority="critical",
            body="## AC\n- item one\n",
        )
        _write_task(
            tasks_dir,
            task_id=2,
            title="In-progress no notes — TDD gated",
            status="in-progress",
            priority="critical",
            body="## AC\n- item one\n",
        )
        view = AgentView(KanbanEngine(board, activity_log=False))

        result = view.pick_tasks()

        assert 2 not in _all_task_ids(result), (
            "gated task must not consume a wave slot"
        )

    def test_sort_order_preserved_after_gate_filtering(
        self, tmp_path: Path
    ) -> None:
        """Priority sort order is preserved for tasks that pass gates.

        Wave 0 should contain critical task before someday task.
        A gated in-progress task must not interfere.

        Currently: gated in-progress task (id=3) appears → first assertion FAILS.
        After fix: id=3 absent, id=1 and id=2 in correct priority order.
        """
        board = _make_board(tmp_path)
        tasks_dir = board / "tasks"
        _write_task(
            tasks_dir,
            task_id=1,
            title="Critical todo — passes gates",
            status="todo",
            priority="critical",
            body="## AC\n- item one\n",
        )
        _write_task(
            tasks_dir,
            task_id=2,
            title="Someday todo — passes gates",
            status="todo",
            priority="someday",
            body="## AC\n- item one\n",
        )
        _write_task(
            tasks_dir,
            task_id=3,
            title="In-progress no notes — TDD gated",
            status="in-progress",
            priority="needed",
            body="## AC\n- item one\n",
        )
        view = AgentView(KanbanEngine(board, activity_log=False))

        result = view.pick_tasks()

        assert 3 not in _all_task_ids(result), (
            "gated in-progress task must not appear in waves"
        )
        all_ids = _all_task_ids(result)
        assert 1 in all_ids, "critical todo must appear in waves"
        assert 2 in all_ids, "someday todo must appear in waves"
        # Verify wave 0 contains id=1 (critical) before id=2 (someday) — sort unchanged
        wave0_ids = [entry.id for entry in result.waves[0].tasks] if result.waves else []
        assert wave0_ids.index(1) < wave0_ids.index(2), (
            "critical task (id=1) must sort before someday task (id=2) in wave 0"
        )
