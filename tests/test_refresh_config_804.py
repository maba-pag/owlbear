"""Tests for #804 — refresh_config rank-map ordering + archive_dir contract.

AC coverage:
  AC1 - archive_dir remains usable after refresh_config() (move_task "archived"
        still writes to the correct directory even when tasks_dir has changed)
  AC3 - After refresh_config(), _status_rank() and _priority_rank() use new
        config values — verified via list_tasks(sort=...) returning tasks in
        the updated rank order, not the order from initial engine construction
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine

# ---------------------------------------------------------------------------
# Shared config content
# ---------------------------------------------------------------------------

_BASE_CONFIG_YAML = """\
version: 10
board:
    name: OwlBear
tasks_dir: tasks
statuses:
    - name: research
    - name: todo
    - name: done
priorities:
    - someday
    - important
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
    """Minimal kanban directory with config.yml and empty tasks/ sub-dir."""
    (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
    (tmp_path / "tasks").mkdir()
    return tmp_path


@pytest.fixture()
def engine(kanban_dir: Path) -> KanbanEngine:
    """KanbanEngine instance wired to the temp kanban_dir."""
    return KanbanEngine(kanban_dir)


# ===========================================================================
# TestFromAC_RankMapsAfterRefresh
#
# AC3: After refresh_config(), _status_rank() and _priority_rank() use new
# config values — tested via list_tasks(sort=...) observable contract.
# ===========================================================================


class TestFromAC_RankMapsAfterRefresh:
    """Rank map ordering via list_tasks reflects refreshed config."""

    # --- Happy path --------------------------------------------------------

    def test_list_tasks_sort_status_reflects_new_order_after_refresh(
        self, kanban_dir: Path, engine: KanbanEngine
    ) -> None:
        """list_tasks(sort='status') uses new status rank after refresh_config().

        Initial order: [research=0, todo=1, done=2].
        Engine starts with two tasks: one 'todo', one 'done'.
        Config changes status order to [done, todo, research].
        After refresh_config(), list_tasks(sort='status') must return the
        'done' task first (rank 0) then 'todo' (rank 1).
        """
        t_todo = engine.create_task("Todo task", status="todo")
        t_done = engine.create_task("Done task", status="done")

        # Initial order must be todo first (rank 1 < done rank 2)
        initial = engine.list_tasks(sort="status")
        assert initial[0].id == t_todo.id, "Precondition: todo ranks lower initially"

        # Swap status order on disk
        reversed_statuses_yaml = _BASE_CONFIG_YAML.replace(
            "    - name: research\n    - name: todo\n    - name: done\n",
            "    - name: done\n    - name: todo\n    - name: research\n",
        )
        (kanban_dir / "config.yml").write_text(reversed_statuses_yaml, encoding="utf-8")

        engine.refresh_config()

        # After refresh: done=0, todo=1, research=2 → done task must be first
        result = engine.list_tasks(sort="status")
        assert result[0].id == t_done.id, (
            f"Expected done task (id={t_done.id}) first after refresh, "
            f"got id={result[0].id}"
        )
        assert result[1].id == t_todo.id

    def test_list_tasks_sort_priority_reflects_new_order_after_refresh(
        self, kanban_dir: Path, engine: KanbanEngine
    ) -> None:
        """list_tasks(sort='priority') uses new priority rank after refresh_config().

        Initial order: [someday=0, important=1, critical=2].
        Two tasks: one 'someday', one 'critical'.
        Config reverses priorities to [critical, important, someday].
        After refresh_config(), 'critical' task must sort first (rank 0).
        """
        t_someday = engine.create_task("Someday task", priority="someday")
        t_critical = engine.create_task("Critical task", priority="critical")

        # Verify precondition: someday ranks lower initially
        initial = engine.list_tasks(sort="priority")
        assert initial[0].id == t_someday.id, "Precondition: someday ranks first initially"

        reversed_priorities_yaml = _BASE_CONFIG_YAML.replace(
            "priorities:\n    - someday\n    - important\n    - critical\n",
            "priorities:\n    - critical\n    - important\n    - someday\n",
        )
        (kanban_dir / "config.yml").write_text(reversed_priorities_yaml, encoding="utf-8")

        engine.refresh_config()

        result = engine.list_tasks(sort="priority")
        assert result[0].id == t_critical.id, (
            f"Expected critical task (id={t_critical.id}) first after refresh, "
            f"got id={result[0].id}"
        )
        assert result[1].id == t_someday.id

    # --- Edge cases --------------------------------------------------------

    def test_unknown_priority_after_config_shrink_sorts_last(
        self, kanban_dir: Path, engine: KanbanEngine
    ) -> None:
        """Task with a removed priority sorts after all known priorities.

        Create a critical task, then remove 'critical' from config and refresh.
        After refresh, 'critical' is not in the rank map — the task must sort
        last (after tasks with known priorities).
        """
        t_critical = engine.create_task("Critical task", priority="critical")
        t_important = engine.create_task("Important task", priority="important")

        # Remove 'critical' from the priority list on disk
        no_critical_yaml = _BASE_CONFIG_YAML.replace(
            "priorities:\n    - someday\n    - important\n    - critical\n",
            "priorities:\n    - someday\n    - important\n",
        )
        (kanban_dir / "config.yml").write_text(no_critical_yaml, encoding="utf-8")

        engine.refresh_config()

        result = engine.list_tasks(sort="priority")
        ids_in_order = [t.id for t in result]
        critical_pos = ids_in_order.index(t_critical.id)
        important_pos = ids_in_order.index(t_important.id)
        assert important_pos < critical_pos, (
            "Task with removed priority must sort after tasks with known priorities"
        )

    def test_status_rank_consistent_across_repeated_refreshes(
        self, engine: KanbanEngine
    ) -> None:
        """list_tasks sort order is stable across multiple refresh_config() calls.

        Two refreshes with no disk change in between must produce identical
        sort results — rank maps must not accumulate state from prior calls.
        """
        engine.create_task("Task A", status="todo")
        engine.create_task("Task B", status="done")

        engine.refresh_config()
        first_result = [t.id for t in engine.list_tasks(sort="status")]

        engine.refresh_config()
        second_result = [t.id for t in engine.list_tasks(sort="status")]

        assert first_result == second_result

    # --- Boundary conditions -----------------------------------------------

    def test_rank_order_reverts_when_config_restored(
        self, kanban_dir: Path, engine: KanbanEngine
    ) -> None:
        """Refreshing back to the original config restores the original sort order.

        Sequence: original config → create tasks → reverse statuses → refresh →
        verify reversed order → restore original → refresh → verify original order.
        """
        t_research = engine.create_task("Research task", status="research")
        t_done = engine.create_task("Done task", status="done")

        # Reverse statuses
        reversed_yaml = _BASE_CONFIG_YAML.replace(
            "    - name: research\n    - name: todo\n    - name: done\n",
            "    - name: done\n    - name: todo\n    - name: research\n",
        )
        (kanban_dir / "config.yml").write_text(reversed_yaml, encoding="utf-8")
        engine.refresh_config()

        reversed_result = engine.list_tasks(sort="status")
        assert reversed_result[0].id == t_done.id, "Reversed: done must be first"

        # Restore original config
        (kanban_dir / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
        engine.refresh_config()

        restored_result = engine.list_tasks(sort="status")
        assert restored_result[0].id == t_research.id, "Restored: research must be first again"


# ===========================================================================
# TestFromAC_ArchiveDirAfterRefresh
#
# AC1: refresh_config() updates archive_dir — verified via move_task("archived")
# still routing to the correct archive directory even after tasks_dir changes.
# ===========================================================================


class TestFromAC_ArchiveDirAfterRefresh:
    """archive_dir remains functional after refresh_config() changes tasks_dir."""

    def test_move_to_archived_succeeds_after_refresh_with_tasks_dir_change(
        self, kanban_dir: Path, engine: KanbanEngine
    ) -> None:
        """move_task("archived") writes to archive/ after refresh changes tasks_dir.

        Verifies that archive_dir is correctly set (always kanban_dir/archive/)
        after refresh_config() changes tasks_dir.  A task created AFTER the
        refresh (in the new tasks_dir) must archive into archive/, not into
        the old or new tasks dir.
        """
        # Change tasks_dir on disk and create the new directory
        new_tasks_yaml = _BASE_CONFIG_YAML.replace("tasks_dir: tasks", "tasks_dir: tasks2")
        (kanban_dir / "tasks2").mkdir()
        (kanban_dir / "config.yml").write_text(new_tasks_yaml, encoding="utf-8")

        engine.refresh_config()

        # Create task AFTER refresh — it lands in tasks2/
        task = engine.create_task("Task to archive")
        assert (kanban_dir / "tasks2").glob(f"{task.id}-*.md"), "Precondition: task in tasks2"

        # Archive the task — must land in archive/, not tasks/ or tasks2/
        engine.move_task(str(task.id), "archived")

        archive_dir = kanban_dir / "archive"
        archived_files = list(archive_dir.glob(f"{task.id}-*.md"))
        assert len(archived_files) == 1, (
            f"Expected task file in archive/, found {len(archived_files)} files: {archived_files}"
        )

    def test_archive_dir_path_is_kanban_dir_slash_archive(
        self, kanban_dir: Path, engine: KanbanEngine
    ) -> None:
        """archive_dir is always kanban_dir/archive regardless of config.

        refresh_config() must not change archive_dir's location even if
        config.yml is modified.  Tasks archived before and after a refresh
        must both land in the same archive/ directory.
        """
        task_before = engine.create_task("Pre-refresh task")
        engine.move_task(str(task_before.id), "archived")

        # Change something in config and refresh
        updated_yaml = _BASE_CONFIG_YAML.replace("next_id: 100", "next_id: 200")
        (kanban_dir / "config.yml").write_text(updated_yaml, encoding="utf-8")
        engine.refresh_config()

        task_after = engine.create_task("Post-refresh task")
        engine.move_task(str(task_after.id), "archived")

        archive_dir = kanban_dir / "archive"
        archived_files = list(archive_dir.glob("*.md"))
        assert len(archived_files) == 2, (
            f"Both pre- and post-refresh tasks must be in archive/, found: {archived_files}"
        )
