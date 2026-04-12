"""Regression tests — KanbanEngine.revision counter (#809).

AC coverage:
  AC1 - engine.revision starts at 0 on a fresh instance
  AC2 - revision increments on every write:
        create_task, edit_task, move_task, claim_task, release_task,
        start_work, end_work (all four outcomes)
  AC3 - revision is read-only (assignment raises AttributeError)
  AC4 - revision is per-instance (two engines have independent counters)

Note (per architect review): the revision counter implementation already exists
in engine.py. These are regression tests verifying existing behaviour, not a
RED-phase stub suite.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from owlbear_kanban import KanbanEngine

# ---------------------------------------------------------------------------
# Shared config — mirrors the real .owlbear/kanban/config.yml layout
# ---------------------------------------------------------------------------

_BASE_CONFIG_YAML = """\
version: 10
board:
    name: OwlBear
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
    class: standard
claim_timeout: 1h
tui:
    title_lines: 2
    hide_empty_columns: true
next_id: 100
"""


@pytest.fixture()
def kanban_dir(tmp_path: Path) -> Path:
    """Minimal kanban directory with config.yml and an empty tasks/ sub-dir."""
    (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
    (tmp_path / "tasks").mkdir()
    return tmp_path


@pytest.fixture()
def engine(kanban_dir: Path) -> KanbanEngine:
    """KanbanEngine wired to a fresh temp kanban_dir."""
    return KanbanEngine(kanban_dir)


# ===========================================================================
# TestFromAC_RevisionCounter
# ===========================================================================


class TestFromAC_RevisionCounter:
    """Regression tests for engine.revision across all AC lines."""

    # --- AC1: starts at zero ------------------------------------------------

    def test_revision_starts_at_zero(self, engine: KanbanEngine) -> None:
        """A freshly created engine reports revision 0 before any writes."""
        assert engine.revision == 0

    # --- AC2: increments on every write -------------------------------------

    def test_create_task_increments_revision(self, engine: KanbanEngine) -> None:
        """create_task increments revision by exactly 1."""
        before = engine.revision
        engine.create_task("Hello world")
        assert engine.revision == before + 1

    def test_edit_task_increments_revision(self, engine: KanbanEngine) -> None:
        """edit_task increments revision by exactly 1."""
        record = engine.create_task("Editable task")
        before = engine.revision
        engine.edit_task(str(record.id), title="Updated title")
        assert engine.revision == before + 1

    def test_move_task_increments_revision(self, engine: KanbanEngine) -> None:
        """move_task increments revision by exactly 1."""
        record = engine.create_task("Movable task")
        before = engine.revision
        engine.move_task(str(record.id), "backlog")
        assert engine.revision == before + 1

    def test_claim_task_increments_revision(self, engine: KanbanEngine) -> None:
        """claim_task increments revision by exactly 1."""
        record = engine.create_task("Claimable task")
        before = engine.revision
        engine.claim_task(str(record.id))
        assert engine.revision == before + 1

    def test_release_task_increments_revision(self, engine: KanbanEngine) -> None:
        """release_task increments revision by exactly 1."""
        record = engine.create_task("Releasable task")
        engine.claim_task(str(record.id))
        before = engine.revision
        engine.release_task(str(record.id))
        assert engine.revision == before + 1

    def test_start_work_increments_revision(self, engine: KanbanEngine) -> None:
        """start_work increments revision (compound — asserts > before)."""
        record = engine.create_task("Start-work task")
        before = engine.revision
        engine.start_work(str(record.id))
        assert engine.revision > before

    def test_end_work_success_increments_revision(self, engine: KanbanEngine) -> None:
        """end_work(success) increments revision (compound — asserts > before)."""
        record = engine.create_task("End-work success task")
        engine.claim_task(str(record.id))
        before = engine.revision
        engine.end_work(str(record.id), note="Done", outcome="success")
        assert engine.revision > before

    def test_end_work_fail_increments_revision(self, engine: KanbanEngine) -> None:
        """end_work(fail) increments revision (compound — asserts > before)."""
        record = engine.create_task("End-work fail task")
        engine.claim_task(str(record.id))
        before = engine.revision
        engine.end_work(str(record.id), note="Failed", outcome="fail")
        assert engine.revision > before

    def test_end_work_block_increments_revision(self, engine: KanbanEngine) -> None:
        """end_work(block) increments revision (compound — asserts > before)."""
        record = engine.create_task("End-work block task")
        engine.claim_task(str(record.id))
        before = engine.revision
        engine.end_work(str(record.id), note="Blocked", outcome="block", block_reason="waiting")
        assert engine.revision > before

    def test_end_work_reject_increments_revision(self, engine: KanbanEngine) -> None:
        """end_work(reject) increments revision (compound — asserts > before)."""
        record = engine.create_task("End-work reject task")
        engine.claim_task(str(record.id))
        before = engine.revision
        engine.end_work(str(record.id), note="Rejected", outcome="reject", move_to="backlog")
        assert engine.revision > before

    # --- AC3: read-only property --------------------------------------------

    def test_revision_is_read_only(self, engine: KanbanEngine) -> None:
        """Assigning to engine.revision raises AttributeError."""
        with pytest.raises(AttributeError):
            engine.revision = 99  # type: ignore[misc]

    # --- AC4: per-instance counters -----------------------------------------

    def test_revision_is_per_instance(self, kanban_dir: Path) -> None:
        """Two engine instances maintain independent revision counters."""
        engine_a = KanbanEngine(kanban_dir)
        engine_b = KanbanEngine(kanban_dir)

        engine_a.create_task("Task for engine A")
        engine_a.create_task("Another task for engine A")

        assert engine_a.revision == 2
        assert engine_b.revision == 0
