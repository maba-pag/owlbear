"""Tests for refresh_config() on KanbanEngine (#803, GREEN phase).

AC coverage:
  AC1 - reload next_id from disk — board_config().next_id reflects new value
  AC2 - reload tasks_dir from disk — create_task writes to new dir
  AC3 - reload statuses from disk — valid_transitions includes new status
  AC4 - reload priorities from disk — board_config().priorities reflects new list
  AC5 - reload added status → move_task accepts new status
  AC6 - reload removed status → move_task raises ValueError for removed status
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
# TestFromAC_RefreshConfig
# ===========================================================================


class TestFromAC_RefreshConfig:
    """Tests that refresh_config() reloads all config state from disk."""

    def test_refresh_config_reloads_yaml_from_disk(
        self, kanban_dir: Path, engine: KanbanEngine
    ) -> None:
        """Change next_id on disk → refresh → board_config().next_id reflects new value."""
        updated_yaml = _BASE_CONFIG_YAML.replace("next_id: 100", "next_id: 999")
        (kanban_dir / "config.yml").write_text(updated_yaml, encoding="utf-8")

        engine.refresh_config()

        assert engine.board_config().next_id == 999

    def test_refresh_config_updates_tasks_dir(
        self, kanban_dir: Path, engine: KanbanEngine
    ) -> None:
        """Change tasks_dir on disk → refresh → create_task writes to new dir."""
        (kanban_dir / "newtasks").mkdir()
        updated_yaml = _BASE_CONFIG_YAML.replace("tasks_dir: tasks", "tasks_dir: newtasks")
        (kanban_dir / "config.yml").write_text(updated_yaml, encoding="utf-8")

        engine.refresh_config()
        task = engine.create_task("Task in new dir")

        new_tasks_dir = kanban_dir / "newtasks"
        written_files = list(new_tasks_dir.glob(f"{task.id}-*.md"))
        assert len(written_files) == 1, f"Expected task file in newtasks/, found: {written_files}"

    def test_refresh_config_updates_statuses(
        self, kanban_dir: Path, engine: KanbanEngine
    ) -> None:
        """Add status on disk → refresh → valid_transitions includes new status."""
        extra_status_yaml = _BASE_CONFIG_YAML.replace(
            "    - name: done\n",
            "    - name: done\n    - name: staging\n",
        )
        (kanban_dir / "config.yml").write_text(extra_status_yaml, encoding="utf-8")

        engine.refresh_config()

        assert "staging" in engine.valid_transitions("research")

    def test_refresh_config_updates_priorities(
        self, kanban_dir: Path, engine: KanbanEngine
    ) -> None:
        """Change priorities on disk → refresh → board_config().priorities reflects new list."""
        new_priorities_yaml = _BASE_CONFIG_YAML.replace(
            "priorities:\n    - someday\n    - nice-to-have\n    - important\n    - needed\n    - critical\n",
            "priorities:\n    - low\n    - high\n",
        )
        (kanban_dir / "config.yml").write_text(new_priorities_yaml, encoding="utf-8")

        engine.refresh_config()

        assert engine.board_config().priorities == ["low", "high"]

    def test_refresh_config_then_move_task_accepts_new_status(
        self, kanban_dir: Path, engine: KanbanEngine
    ) -> None:
        """Add status on disk → refresh → move_task succeeds with new status."""
        task = engine.create_task("Movable task")

        extra_status_yaml = _BASE_CONFIG_YAML.replace(
            "    - name: done\n",
            "    - name: done\n    - name: staging\n",
        )
        (kanban_dir / "config.yml").write_text(extra_status_yaml, encoding="utf-8")
        engine.refresh_config()

        record = engine.move_task(str(task.id), "staging")
        assert record.status == "staging"

    def test_refresh_config_then_move_task_rejects_removed_status(
        self, kanban_dir: Path, engine: KanbanEngine
    ) -> None:
        """Remove status on disk → refresh → move_task raises ValueError for removed status."""
        task = engine.create_task("Task to move")

        removed_status_yaml = _BASE_CONFIG_YAML.replace("    - name: backlog\n", "")
        (kanban_dir / "config.yml").write_text(removed_status_yaml, encoding="utf-8")
        engine.refresh_config()

        with pytest.raises(ValueError, match="backlog"):
            engine.move_task(str(task.id), "backlog")
