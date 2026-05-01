"""Failing tests for CockpitView archival validation block (#1240).

RED phase — all tests must fail until B3 implementation (CockpitView.move_task
validation block) is complete.

AC coverage:
  AC1:  status="archived" + archival_reason=None → ERR_ARCHIVAL_REASON_REQUIRED
  AC2:  reason="completed" + non-empty refs → ERR_ARCHIVAL_REFS_FORBIDDEN
  AC3:  reason="dropped" + non-empty refs → ERR_ARCHIVAL_REFS_FORBIDDEN
  AC4:  reason="wontfix" + non-empty refs → ERR_ARCHIVAL_REFS_FORBIDDEN
  AC5:  reason="deprecated" + empty refs → ERR_ARCHIVAL_REFS_REQUIRED
  AC6:  reason="duplicate" + empty refs → ERR_ARCHIVAL_REFS_REQUIRED
  AC7:  reason="completed" when task.status != "done" → ERR_COMPLETED_REQUIRES_DONE
  AC8:  archival_refs contains non-existent ID → ERR_ARCHIVAL_REF_MISSING (422)
  AC9:  archival_refs contains task's own ID (self-reference) → ERR_ARCHIVAL_REF_SELF (422)
  AC10: archival_refs creates a dependency cycle → ERR_ARCHIVAL_REF_CYCLE (422)
  AC11: Valid archival (completed, done, empty refs) succeeds and persists both
        fields — test added in retry cycle per reviewer AC11 gap.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_cockpit.view import CockpitView
from owlbear_kanban import KanbanEngine
from owlbear_kanban.errors import ValidationError

# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
statuses:
    - research
    - backlog
    - todo
    - in-progress
    - review
    - docs
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
    todo: test-writer
    in-progress: builder
    review: reviewer
    docs: doc-writer
    done: auditor
agent_types: {}
agent_compatibility: {}
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1
"""


def _make_board(base_dir: Path) -> Path:
    """Create a minimal kanban board directory."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def board_dir(tmp_path: Path) -> Path:
    """Board with two tasks: one at 'done', one at 'todo'."""
    kanban_dir = _make_board(tmp_path)
    seed = KanbanEngine(kanban_dir, agent_name="seed")
    seed.create_task("Done task", status="done", priority="important")
    seed.create_task("Todo task", status="todo", priority="important")
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine bound to the test board."""
    eng = KanbanEngine(board_dir, agent_name="cockpit")
    eng.list_tasks()
    return eng


@pytest.fixture
def view(engine: KanbanEngine) -> CockpitView:
    """CockpitView bound to the test engine."""
    return CockpitView(engine)


def _get_updated(engine: KanbanEngine, task_id: int) -> str:
    """Return the current 'updated' timestamp for the given task ID."""
    return str(engine.show_task(str(task_id)).updated)


# ---------------------------------------------------------------------------
# AC1-AC10 -- CockpitView.move_task archival validation block
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewArchivalValidation:
    """Archival validation block in CockpitView.move_task (B3, task #1240)."""

    # -- AC1: reason required when status="archived" --

    def test_archive_without_reason_raises_archival_reason_required(
        self, view: CockpitView, engine: KanbanEngine
    ) -> None:
        """AC1: move_task(id, "archived", archival_reason=None) must raise
        ERR_ARCHIVAL_REASON_REQUIRED.

        CockpitView currently passes through to engine unconditionally; no
        validation block exists. The call succeeds without raising.
        """
        updated = _get_updated(engine, 1)
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1, "archived", expected_updated=updated, archival_reason=None
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REASON_REQUIRED"

    # -- AC2-AC4: refs forbidden for completed / dropped / wontfix --

    def test_archive_completed_with_refs_raises_archival_refs_forbidden(
        self, view: CockpitView, engine: KanbanEngine
    ) -> None:
        """AC2: move_task with reason='completed' and non-empty refs raises
        ERR_ARCHIVAL_REFS_FORBIDDEN.

        CockpitView has no validation block; the call passes through to the
        engine which stores the fields without error.
        """
        updated = _get_updated(engine, 1)
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1,
                "archived",
                expected_updated=updated,
                archival_reason="completed",
                archival_refs=[2],
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_FORBIDDEN"

    def test_archive_dropped_with_refs_raises_archival_refs_forbidden(
        self, view: CockpitView, engine: KanbanEngine
    ) -> None:
        """AC3: move_task with reason='dropped' and non-empty refs raises
        ERR_ARCHIVAL_REFS_FORBIDDEN.

        CockpitView has no validation block; refs are silently stored.
        """
        updated = _get_updated(engine, 1)
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1,
                "archived",
                expected_updated=updated,
                archival_reason="dropped",
                archival_refs=[2],
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_FORBIDDEN"

    def test_archive_wontfix_with_refs_raises_archival_refs_forbidden(
        self, view: CockpitView, engine: KanbanEngine
    ) -> None:
        """AC4: move_task with reason='wontfix' and non-empty refs raises
        ERR_ARCHIVAL_REFS_FORBIDDEN.

        CockpitView has no validation block; refs are silently stored.
        """
        updated = _get_updated(engine, 1)
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1,
                "archived",
                expected_updated=updated,
                archival_reason="wontfix",
                archival_refs=[2],
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_FORBIDDEN"

    # -- AC5-AC6: refs required for deprecated / duplicate --

    def test_archive_deprecated_without_refs_raises_archival_refs_required(
        self, view: CockpitView, engine: KanbanEngine
    ) -> None:
        """AC5: move_task with reason='deprecated' and empty refs raises
        ERR_ARCHIVAL_REFS_REQUIRED.

        CockpitView has no validation block; the task is archived with
        archival_refs=[] and no error raised.
        """
        updated = _get_updated(engine, 1)
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1,
                "archived",
                expected_updated=updated,
                archival_reason="deprecated",
                archival_refs=[],
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_REQUIRED"

    def test_archive_duplicate_without_refs_raises_archival_refs_required(
        self, view: CockpitView, engine: KanbanEngine
    ) -> None:
        """AC6: move_task with reason='duplicate' and empty refs raises
        ERR_ARCHIVAL_REFS_REQUIRED.

        CockpitView has no validation block; the task is archived with
        archival_refs=[] and no error raised.
        """
        updated = _get_updated(engine, 1)
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1,
                "archived",
                expected_updated=updated,
                archival_reason="duplicate",
                archival_refs=[],
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REFS_REQUIRED"

    # -- AC7: completed requires task.status == "done" --

    def test_archive_completed_from_non_done_status_raises_completed_requires_done(
        self, view: CockpitView, engine: KanbanEngine
    ) -> None:
        """AC7: move_task with reason='completed' when task.status != 'done' raises
        ERR_COMPLETED_REQUIRES_DONE.

        Task 2 is at 'todo', not 'done'. CockpitView has no validation block;
        the engine stores archival_reason='completed' without checking prior status.
        """
        updated = _get_updated(engine, 2)
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                2,
                "archived",
                expected_updated=updated,
                archival_reason="completed",
                archival_refs=[],
            )
        assert exc_info.value.code == "ERR_COMPLETED_REQUIRES_DONE"

    # -- AC8: ref ID does not exist on the board --

    def test_archive_with_nonexistent_ref_raises_archival_ref_missing(
        self, view: CockpitView, engine: KanbanEngine
    ) -> None:
        """AC8: move_task with archival_refs containing a non-existent task ID raises
        a 422 ValidationError.

        Task 99999 does not exist. CockpitView has no validation block; the engine
        silently stores refs=[99999] without verifying existence.
        """
        updated = _get_updated(engine, 1)
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1,
                "archived",
                expected_updated=updated,
                archival_reason="deprecated",
                archival_refs=[99999],
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REF_MISSING"

    # -- AC9: self-reference in archival_refs --

    def test_archive_with_self_ref_raises_archival_ref_self(
        self, view: CockpitView, engine: KanbanEngine
    ) -> None:
        """AC9: move_task with archival_refs=[task_id] (self-reference) raises a
        422 ValidationError.

        Task 1 references its own ID in refs. CockpitView has no validation
        block; the engine silently stores refs=[1] with no self-reference check.
        """
        updated = _get_updated(engine, 1)
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1,
                "archived",
                expected_updated=updated,
                archival_reason="deprecated",
                archival_refs=[1],
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REF_SELF"

    # -- AC10: archival_refs creates a dependency cycle --

    def test_archive_with_cyclic_refs_raises_archival_ref_cycle(
        self, tmp_path: Path
    ) -> None:
        """AC10: move_task with archival_refs that create a cycle raises a
        422 ValidationError.

        Setup:
          - Task A (id=1, done): to be archived via CockpitView with refs=[B.id]
          - Task B (id=2, todo): archived directly via engine with refs=[A.id]

        When the view validates A's archival, it follows B's refs which point
        back to A — a cycle. CockpitView has no validation block; the cycle
        is silently accepted and A is archived with refs=[B.id].
        """
        # Build a fresh board with tasks A (done) and B (todo).
        kanban_dir = _make_board(tmp_path)
        seed = KanbanEngine(kanban_dir, agent_name="seed")
        seed.create_task("Task A", status="done", priority="important")
        seed.create_task("Task B", status="todo", priority="important")

        # Archive task B directly via engine (bypassing view validation):
        # B gets archival_refs=[1] — B references A.
        eng = KanbanEngine(kanban_dir, agent_name="cockpit")
        eng.list_tasks()
        eng.move_task("2", "archived", archival_reason="deprecated", archival_refs=[1])

        # Now try to archive A via CockpitView with refs=[B.id=2].
        # A → B and B → A: cycle.
        view = CockpitView(eng)
        updated_a = _get_updated(eng, 1)
        with pytest.raises(ValidationError) as exc_info:
            view.move_task(
                1,
                "archived",
                expected_updated=updated_a,
                archival_reason="deprecated",
                archival_refs=[2],
            )
        assert exc_info.value.code == "ERR_ARCHIVAL_REF_CYCLE"

    # -- AC11: valid archival persists archival_reason and archival_refs --

    def test_valid_archival_persists_reason_and_refs(
        self, view: CockpitView, engine: KanbanEngine
    ) -> None:
        """AC11: move_task on a done task with status='archived',
        reason='completed', and archival_refs=[] succeeds and persists both
        fields on the returned response and on a fresh reload.

        Task 1 is seeded at 'done'. reason='completed' requires no refs and
        the task is already at terminal status, so all validation rules pass.
        """
        updated = _get_updated(engine, 1)
        response = view.move_task(
            1,
            "archived",
            expected_updated=updated,
            archival_reason="completed",
            archival_refs=[],
        )
        assert response.archival_reason == "completed"
        assert response.archival_refs == []

        # Verify persistence: reload from disk via engine.
        reloaded = engine.show_task("1")
        assert reloaded.archival_reason == "completed"
        assert reloaded.archival_refs == []
