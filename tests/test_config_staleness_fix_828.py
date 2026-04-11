"""Failing tests for create_task config staleness fix (#828, RED phase).

AC coverage:
  AC1 - create_task updates self._config (not just a local variable) —
        observable via engine.board_config().next_id reflecting the increment
        immediately after the call (consistent with refresh_config() pattern)
  AC2 - self._tasks_dir updated after config reload — observable via a
        subsequent create_task writing to a new tasks_dir when config was
        externally changed between calls

All tests in this file MUST FAIL until #828 is implemented GREEN.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.config_loader import load_config

# ---------------------------------------------------------------------------
# Shared config content — mirrors _BASE_CONFIG_YAML from test_kanban_engine_crud.py
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
    """Minimal kanban directory with config.yml and empty tasks/ sub-dir."""
    (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
    (tmp_path / "tasks").mkdir()
    return tmp_path


@pytest.fixture()
def engine(kanban_dir: Path) -> KanbanEngine:
    """KanbanEngine instance wired to the temp kanban_dir."""
    return KanbanEngine(kanban_dir)


# ===========================================================================
# TestFromAC_ConfigStalenessInCreateTask
# AC1: board_config().next_id reflects the update made inside create_task
# AC2: _tasks_dir updated in sync with the reloaded config's tasks_dir
# ===========================================================================


class TestFromAC_ConfigStalenessInCreateTask:
    """Tests that create_task keeps self._config (and derived dirs) in sync."""

    # --- Happy path --------------------------------------------------------

    def test_board_config_next_id_incremented_after_one_create(
        self, engine: KanbanEngine
    ) -> None:
        """board_config().next_id is 101 immediately after one create_task call.

        Bug: create_task assigns load_config() to a local variable and never
        updates self._config, so board_config() returns the stale initial value.
        """
        engine.create_task("First task")
        assert engine.board_config().next_id == 101

    def test_board_config_next_id_incremented_after_two_creates(
        self, engine: KanbanEngine
    ) -> None:
        """board_config().next_id is 102 after two consecutive create_task calls."""
        engine.create_task("First task")
        engine.create_task("Second task")
        assert engine.board_config().next_id == 102

    # --- Edge cases --------------------------------------------------------

    def test_board_config_matches_disk_config_after_create(
        self, kanban_dir: Path, engine: KanbanEngine
    ) -> None:
        """board_config().next_id matches a fresh load_config() from disk after create.

        Currently broken: board sees stale 100, disk has 101.
        """
        engine.create_task("Consistency check")
        disk_config = load_config(kanban_dir)
        assert engine.board_config().next_id == disk_config.next_id

    def test_board_config_consistent_without_manual_refresh(
        self, engine: KanbanEngine
    ) -> None:
        """board_config() should agree with refresh_config() without a manual call.

        If self._config is updated by create_task (the fix), calling
        refresh_config() afterwards should return the same next_id as
        board_config() already reports.  Currently they disagree (100 vs 101).
        """
        engine.create_task("Task without manual refresh")
        stale_next_id = engine.board_config().next_id  # should be 101 post-fix
        engine.refresh_config()
        refreshed_next_id = engine.board_config().next_id  # 101 from disk
        assert stale_next_id == refreshed_next_id  # both must be 101

    # --- Boundary conditions -----------------------------------------------

    def test_board_config_next_id_tracks_n_creates(
        self, engine: KanbanEngine
    ) -> None:
        """board_config().next_id equals 100 + N after N sequential creates."""
        n = 5
        for i in range(n):
            engine.create_task(f"Task {i}")
        assert engine.board_config().next_id == 100 + n

    def test_tasks_dir_updated_after_create_when_config_changes(
        self, kanban_dir: Path, engine: KanbanEngine
    ) -> None:
        """_tasks_dir reflects tasks_dir from the reloaded config after create_task.

        Setup: externally change tasks_dir in config.yml to 'tasks2' while the
        engine is alive.  After the first create_task (which reloads config),
        the fix must update self._tasks_dir so the *next* create writes into
        the new directory.

        Without the fix, self._tasks_dir is never updated and both creates land
        in the original 'tasks/' directory; 'tasks2/' stays empty (assertion fails).
        """
        new_tasks_dir = kanban_dir / "tasks2"
        new_tasks_dir.mkdir()

        # Change tasks_dir in config while engine is live
        new_config_yaml = _BASE_CONFIG_YAML.replace(
            "tasks_dir: tasks", "tasks_dir: tasks2"
        )
        (kanban_dir / "config.yml").write_text(new_config_yaml, encoding="utf-8")

        # First create_task triggers config reload; fix must update _tasks_dir
        engine.create_task("Trigger config reload")

        # Second create must now target the new tasks_dir
        engine.create_task("New tasks_dir task")

        files_in_new_dir = list(new_tasks_dir.glob("*.md"))
        assert len(files_in_new_dir) >= 1
