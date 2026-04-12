"""RED tests — Compat alias removal + import migration (#821).

AC coverage:
  AC1 — No TaskRecord references remain in engine source, MCP adapter source,
         or test files (grep verification)
  AC2 — All engine imports use owlbear_kanban namespace; no stale
         owlbear_mcp_kanban.{engine,task_io,config_loader} imports in tests;
         server.py does not import TaskRecord
  AC3 — Targeted test files import Task (not TaskRecord) from owlbear_kanban.models
  AC4 — Meta-criterion: all tests fail RED (satisfied by AC1-AC3 failing)

Self-exclusion: this file references "TaskRecord" in docstrings and assertion
messages. The grep tests exclude ``Path(__file__)`` from their scans.
"""

from __future__ import annotations

import ast
from pathlib import Path

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parent.parent
_TESTS_DIR = _PROJECT_ROOT / "tests"
_ENGINE_SRC_DIR = _PROJECT_ROOT / "serve" / "kanban" / "src"
_MCP_ADAPTER_SRC_DIR = _PROJECT_ROOT / "serve" / "mcp-kanban" / "src"
_SERVER_PY = _MCP_ADAPTER_SRC_DIR / "owlbear_mcp_kanban" / "server.py"
_SELF = Path(__file__)

# Stale module namespaces that must be removed from test imports
_STALE_MODULES: frozenset[str] = frozenset({
    "owlbear_mcp_kanban.engine",
    "owlbear_mcp_kanban.task_io",
    "owlbear_mcp_kanban.config_loader",
})

# Test files whose TaskRecord imports must be replaced with Task
_TARGET_TEST_FILES: tuple[str, ...] = (
    "test_kanban_engine_crud.py",
    "test_kanban_engine_listing.py",
    "test_kanban_engine_models.py",
    "test_kanban_mcp_migration.py",
    "test_kanban_task_io.py",
    "test_rename_taskrecord_to_task_799.py",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _taskrecord_refs(root: Path, *, exclude_self: bool = False) -> list[str]:
    """Return ``path:line: text`` for every line containing ``TaskRecord`` in *.py files."""
    hits: list[str] = []
    for py_file in sorted(root.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        if exclude_self and py_file == _SELF:
            continue
        for lineno, line in enumerate(
            py_file.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if "TaskRecord" in line:
                rel = py_file.relative_to(_PROJECT_ROOT)
                hits.append(f"{rel}:{lineno}: {line.strip()}")
    return hits


def _imports_from(source: str, module: str) -> set[str]:
    """Return names imported from *module* in source, including those inside TYPE_CHECKING blocks."""
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == module:
            names.update(alias.asname or alias.name for alias in node.names)
    return names


def _stale_module_imports(source: str) -> list[str]:
    """Return stale owlbear_mcp_kanban.* module names found in import statements."""
    tree = ast.parse(source)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module in _STALE_MODULES:
            found.append(node.module)
    return found


# ===========================================================================
# TestFromAC_NoTaskRecordReferences  — AC1
# ===========================================================================


class TestFromAC_NoTaskRecordReferences:
    """AC1: No TaskRecord references remain in engine source, MCP adapter, or tests."""

    def test_no_taskrecord_in_engine_source(self) -> None:
        """No .py file under serve/kanban/src/ references TaskRecord.

        After alias removal, models.py no longer defines ``TaskRecord = Task``,
        ``__init__.py`` no longer exports it, and all docstrings in engine.py
        and task_io.py no longer mention it.
        """
        hits = _taskrecord_refs(_ENGINE_SRC_DIR)
        assert not hits, (
            f"Engine source still has {len(hits)} TaskRecord reference(s):\n"
            + "\n".join(hits[:15])
        )

    def test_no_taskrecord_in_mcp_adapter_source(self) -> None:
        """No .py file under serve/mcp-kanban/src/ references TaskRecord.

        After migration, server.py no longer imports TaskRecord in the
        TYPE_CHECKING block, the ``_record_to_task`` parameter annotation
        uses Task, and the docstring is updated accordingly.
        """
        hits = _taskrecord_refs(_MCP_ADAPTER_SRC_DIR)
        assert not hits, (
            f"MCP adapter source still has {len(hits)} TaskRecord reference(s):\n"
            + "\n".join(hits[:15])
        )

    def test_no_taskrecord_in_tests(self) -> None:
        """No .py file under tests/ — excluding this file — references TaskRecord.

        After import migration, all test files use Task wherever TaskRecord
        was previously imported or mentioned in code.  Docstrings in test
        files that describe the old name must also be updated.
        """
        hits = _taskrecord_refs(_TESTS_DIR, exclude_self=True)
        assert not hits, (
            f"Test files still have {len(hits)} TaskRecord reference(s) "
            f"(first 15 shown):\n" + "\n".join(hits[:15])
        )


# ===========================================================================
# TestFromAC_EngineImportsOwlbearKanban  — AC2
# ===========================================================================


class TestFromAC_EngineImportsOwlbearKanban:
    """AC2: Engine namespace used cleanly; stale mcp_kanban.* paths removed."""

    def test_server_no_taskrecord_import(self) -> None:
        """server.py does not import TaskRecord from owlbear_kanban.models.

        After migration the TYPE_CHECKING guard must import ``Task``
        (not the alias ``TaskRecord``) and the ``_record_to_task`` signature
        must reference ``Task`` as the parameter type.
        """
        source = _SERVER_PY.read_text(encoding="utf-8")
        names = _imports_from(source, "owlbear_kanban.models")
        assert "TaskRecord" not in names, (
            f"server.py still imports TaskRecord from owlbear_kanban.models; "
            f"found imports: {names}"
        )

    def test_no_stale_mcp_namespace_imports_in_tests(self) -> None:
        """No test file imports from owlbear_mcp_kanban.engine, .task_io, or .config_loader.

        These submodules were relocated to owlbear_kanban.*  during the Phase 2
        extraction.  Four test files (roundtrip, mcp_migration, task_io, archive)
        still use the stale paths and must be updated to the correct namespace.
        """
        violations: list[str] = []
        for py_file in sorted(_TESTS_DIR.glob("*.py")):
            if py_file == _SELF:
                continue
            source = py_file.read_text(encoding="utf-8")
            for mod in _stale_module_imports(source):
                violations.append(f"{py_file.name}: imports from {mod!r}")
        assert not violations, (
            "Test files still use stale owlbear_mcp_kanban.* namespaces:\n"
            + "\n".join(violations)
        )


# ===========================================================================
# TestFromAC_TestFileImports  — AC3
# ===========================================================================


class TestFromAC_TestFileImports:
    """AC3: Targeted test files have replaced TaskRecord with Task imports."""

    def test_target_files_do_not_import_taskrecord(self) -> None:
        """None of the targeted test files import TaskRecord from owlbear_kanban.models.

        The six test files that currently do ``from owlbear_kanban.models import
        TaskRecord`` (or include it in a multi-name import) must have that name
        removed once the alias is deleted.
        """
        violations: list[str] = []
        for fname in _TARGET_TEST_FILES:
            fpath = _TESTS_DIR / fname
            if not fpath.exists():
                continue
            names = _imports_from(fpath.read_text(encoding="utf-8"), "owlbear_kanban.models")
            if "TaskRecord" in names:
                violations.append(
                    f"{fname}: still imports TaskRecord from owlbear_kanban.models"
                )
        assert not violations, "\n".join(violations)

    def test_target_files_import_task(self) -> None:
        """The targeted test files that use the model class import Task from owlbear_kanban.models.

        After removing the TaskRecord alias, callers that relied on it must
        switch to Task.  Files whose only owlbear_kanban.models import was
        TaskRecord must add ``Task`` to their import list.
        """
        # Files that actively use the model in assertions (isinstance, model_validate)
        # must import Task.  test_kanban_engine_listing.py uses an inline import
        # which AST-walking will still detect.
        check_files = (
            "test_kanban_engine_crud.py",
            "test_kanban_engine_models.py",
            "test_kanban_mcp_migration.py",
            "test_kanban_task_io.py",
        )
        violations: list[str] = []
        for fname in check_files:
            fpath = _TESTS_DIR / fname
            if not fpath.exists():
                continue
            names = _imports_from(fpath.read_text(encoding="utf-8"), "owlbear_kanban.models")
            if "Task" not in names:
                violations.append(
                    f"{fname}: must import Task from owlbear_kanban.models (currently imports {names})"
                )
        assert not violations, "\n".join(violations)
