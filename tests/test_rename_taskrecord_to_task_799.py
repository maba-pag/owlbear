"""Failing tests for Rename TaskRecord → Task (#799, RED phase).

AC coverage:
  AC1 - Task importable from engine_models
  AC2 - TaskRecord alias resolves to Task (same object identity)
  AC3 - Engine CRUD works with renamed model (create, edit, move, show, list) —
        each method returns a Task instance
  AC4 - Tests fail RED before implementation

RED guarantee: Task is not defined in engine_models.py yet → ImportError at
collection time causes every test to fail.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_mcp_kanban.engine import KanbanEngine  # type: ignore[import-not-found]
from owlbear_mcp_kanban.engine_models import Task, TaskRecord  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# Shared config — mirrors _BASE_CONFIG_YAML from test_kanban_engine_crud.py
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
# TestFromAC_RenameTaskRecordToTask
# ===========================================================================


class TestFromAC_RenameTaskRecordToTask:
    """Tests for AC1-AC3: Task importable, alias identity, CRUD returns Task."""

    # --- AC1: Task importable from engine_models ----------------------------

    def test_task_is_importable_as_a_class(self) -> None:
        """Task is importable from engine_models and is a class (not None)."""
        assert isinstance(Task, type)

    # --- AC2: TaskRecord alias resolves to Task (same object identity) ------

    def test_taskrecord_is_same_object_as_task(self) -> None:
        """TaskRecord is an alias for Task — exact same object."""
        assert TaskRecord is Task

    def test_taskrecord_alias_preserves_pydantic_model_config(self) -> None:
        """TaskRecord.model_config is the same object as Task.model_config."""
        assert Task.model_config is TaskRecord.model_config

    # --- AC3: CRUD — create_task returns Task instance ----------------------

    def test_create_task_returns_task_instance(self, engine: KanbanEngine) -> None:
        """create_task returns an instance of Task."""
        result = engine.create_task("Create test for Task rename")
        assert isinstance(result, Task)

    # --- AC3: CRUD — show_task returns Task instance ------------------------

    def test_show_task_returns_task_instance(self, engine: KanbanEngine) -> None:
        """show_task returns an instance of Task."""
        created = engine.create_task("Show test for Task rename")
        result = engine.show_task(str(created.id))
        assert isinstance(result, Task)

    # --- AC3: CRUD — edit_task returns Task instance ------------------------

    def test_edit_task_returns_task_instance(self, engine: KanbanEngine) -> None:
        """edit_task returns an instance of Task."""
        created = engine.create_task("Edit test for Task rename")
        result = engine.edit_task(str(created.id), title="Edited title")
        assert isinstance(result, Task)

    # --- AC3: CRUD — move_task returns Task instance ------------------------

    def test_move_task_returns_task_instance(self, engine: KanbanEngine) -> None:
        """move_task returns an instance of Task."""
        created = engine.create_task("Move test for Task rename")
        result = engine.move_task(str(created.id), "backlog")
        assert isinstance(result, Task)

    # --- AC3: CRUD — list_tasks returns list of Task instances --------------

    def test_list_tasks_returns_list_of_task_instances(self, engine: KanbanEngine) -> None:
        """list_tasks returns Task instances - all items are isinstance(r, Task)."""
        engine.create_task("List item alpha")
        engine.create_task("List item beta")
        results = engine.list_tasks()
        assert len(results) >= 2
        assert all(isinstance(r, Task) for r in results)

    # --- Edge: list_tasks on empty board ------------------------------------

    def test_list_tasks_empty_board_returns_empty_list(self, engine: KanbanEngine) -> None:
        """list_tasks on a board with no tasks returns an empty list."""
        results = engine.list_tasks()
        assert results == []

    # --- Boundary: Task class hierarchy -------------------------------------

    def test_task_is_subclass_of_pydantic_basemodel(self) -> None:
        """Task is a pydantic BaseModel subclass."""
        from pydantic import BaseModel

        assert issubclass(Task, BaseModel)
