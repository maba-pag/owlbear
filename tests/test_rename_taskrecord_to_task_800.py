"""Failing tests for Rename TaskRecord → Task internal refs (#800, RED phase).

AC coverage:
  AC1 - Task is the canonical class in models.py — covered by #799; confirmed here
        via source inspection (already satisfied, defers to #799 GREEN tests)
  AC2 - TaskRecord = Task compat alias exported — covered by #799
  AC3 - All internal engine refs use Task — source inspection tests (RED now)
  AC4 - #799 tests pass GREEN — meta-criterion; no direct pytest equivalent
  AC5 - Existing MCP tests pass unchanged (O4) — server.py TYPE_CHECKING
        import preserved; verified via source inspection (N/A for RED: already
        satisfied pre-implementation; confirmed in notes)

RED guarantee: engine.py and task_io.py currently import and use TaskRecord
throughout. Source inspection assertions that TaskRecord is absent (or Task
is present) fail against the current source → every test in this suite FAILS.
"""

from __future__ import annotations

import ast
from pathlib import Path

# ---------------------------------------------------------------------------
# Source file paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parent.parent
_ENGINE_PY = _PROJECT_ROOT / "serve/kanban/src/owlbear_kanban/engine.py"
_TASK_IO_PY = _PROJECT_ROOT / "serve/kanban/src/owlbear_kanban/task_io.py"
_SERVER_PY = _PROJECT_ROOT / "serve/mcp-kanban/src/owlbear_mcp_kanban/server.py"


def _import_names_from(source: str, module: str) -> set[str]:
    """Return the set of names imported from *module* in the given source text.

    Handles both plain imports and TYPE_CHECKING guards by walking the full
    AST; all ``from <module> import ...`` nodes are collected regardless of
    whether they are nested inside an ``if TYPE_CHECKING:`` block.
    """
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module:
            names.update(alias.asname or alias.name for alias in node.names)
    return names


# ===========================================================================
# TestFromAC_RenameTaskRecordToTaskInternals
# ===========================================================================


class TestFromAC_RenameTaskRecordToTaskInternals:
    """AC3 source inspection: engine.py and task_io.py use Task, not TaskRecord."""

    # --- AC3: engine.py import uses Task ---

    def test_engine_imports_task_from_models(self) -> None:
        """engine.py imports Task (not TaskRecord) from owlbear_kanban.models."""
        source = _ENGINE_PY.read_text(encoding="utf-8")
        names = _import_names_from(source, "owlbear_kanban.models")
        assert "Task" in names, (
            f"engine.py must import Task from owlbear_kanban.models; got: {names}"
        )

    def test_engine_does_not_import_taskrecord_from_models(self) -> None:
        """engine.py does not import TaskRecord from owlbear_kanban.models.

        After the rename, TaskRecord is the alias kept only for consumers
        (server.py TYPE_CHECKING). engine.py's internal import must use Task.
        """
        source = _ENGINE_PY.read_text(encoding="utf-8")
        names = _import_names_from(source, "owlbear_kanban.models")
        assert "TaskRecord" not in names, (
            f"engine.py must not import TaskRecord directly; got: {names}"
        )

    # --- AC3: task_io.py import uses Task ---

    def test_task_io_imports_task_from_models(self) -> None:
        """task_io.py imports Task (not TaskRecord) from owlbear_kanban.models."""
        source = _TASK_IO_PY.read_text(encoding="utf-8")
        names = _import_names_from(source, "owlbear_kanban.models")
        assert "Task" in names, (
            f"task_io.py must import Task from owlbear_kanban.models; got: {names}"
        )

    def test_task_io_does_not_import_taskrecord_from_models(self) -> None:
        """task_io.py does not import TaskRecord from owlbear_kanban.models."""
        source = _TASK_IO_PY.read_text(encoding="utf-8")
        names = _import_names_from(source, "owlbear_kanban.models")
        assert "TaskRecord" not in names, (
            f"task_io.py must not import TaskRecord directly; got: {names}"
        )

    # --- AC3: engine.py type annotations / usage ---

    def test_engine_no_list_taskrecord_annotation(self) -> None:
        """engine.py does not use list[TaskRecord] in any type annotation.

        After rename: list_tasks return type and internal variable become
        list[Task].
        """
        source = _ENGINE_PY.read_text(encoding="utf-8")
        assert "list[TaskRecord]" not in source, (
            "engine.py still has list[TaskRecord]; expected list[Task] after rename"
        )

    def test_engine_no_taskrecord_return_annotations(self) -> None:
        """engine.py does not use '-> TaskRecord:' in any function signature.

        After rename: show_task, create_task, edit_task, move_task,
        claim_task, release_task, start_work all return -> Task:.
        """
        source = _ENGINE_PY.read_text(encoding="utf-8")
        assert "-> TaskRecord:" not in source, (
            "engine.py still has '-> TaskRecord:' return annotations; "
            "expected '-> Task:' after rename"
        )

    def test_engine_no_taskrecord_constructor_call(self) -> None:
        """engine.py does not call TaskRecord(...) constructor.

        After rename: create_task uses Task(...) to construct the new record.
        """
        source = _ENGINE_PY.read_text(encoding="utf-8")
        assert "TaskRecord(" not in source, (
            "engine.py still calls TaskRecord(...); expected Task(...) after rename"
        )

    # --- AC3: task_io.py type annotations / usage ---

    def test_task_io_no_taskrecord_return_annotation(self) -> None:
        """task_io.py does not use '-> TaskRecord:' in any function signature.

        After rename: read_task return type becomes -> Task:.
        """
        source = _TASK_IO_PY.read_text(encoding="utf-8")
        assert "-> TaskRecord:" not in source, (
            "task_io.py still has '-> TaskRecord:' return annotation; "
            "expected '-> Task:' after rename"
        )

    def test_task_io_no_taskrecord_record_parameter(self) -> None:
        """task_io.py does not annotate the record parameter as TaskRecord.

        After rename: write_task signature uses record: Task.
        """
        source = _TASK_IO_PY.read_text(encoding="utf-8")
        assert "record: TaskRecord" not in source, (
            "task_io.py still has 'record: TaskRecord'; "
            "expected 'record: Task' after rename"
        )

    def test_task_io_no_taskrecord_model_validate_call(self) -> None:
        """task_io.py does not call TaskRecord.model_validate.

        After rename: read_task uses Task.model_validate(data) to parse
        the YAML frontmatter into a Task instance.
        """
        source = _TASK_IO_PY.read_text(encoding="utf-8")
        assert "TaskRecord.model_validate" not in source, (
            "task_io.py still calls TaskRecord.model_validate; "
            "expected Task.model_validate after rename"
        )
