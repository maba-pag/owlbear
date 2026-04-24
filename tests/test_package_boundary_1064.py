"""Boundary tests for #1064: C-19 — Boundary test updates.

AC-C45: ``tests/test_package_boundary.py`` enforces:
  - No owlbear_kanban source file except ``engine.py`` imports from
    ``owlbear_kanban.storage`` (the public surface module).
  - No owlbear_kanban source file imports from the deleted ``task_io`` module.

AC-C46: ``tests/test_deny_code_writes.py`` must exist to provide storage-test
  isolation coverage (storage tests prohibited from writing outside ``tmp_path``).

3rd AC: Boundary tests pass with the new module layout (storage.py,
  storage_io.py, body_parser.py, activity_store.py, corruption.py, migrate.py,
  predicates.py).

4th AC: No import of removed ``task_io`` module anywhere in the codebase
  (source files and test files included).

All tests in RED phase:
  - AC-C45 fails because ``dispatch.py`` and ``corruption.py`` import from
    ``owlbear_kanban.storage`` directly (only engine.py is permitted).
  - 4th AC fails because ``test_mtime_cache_942.py`` and
    ``test_yaml12_loader_940.py`` reference ``owlbear_kanban.task_io`` via
    ``__import__`` / direct imports.
  - AC-C46 fails because ``tests/test_deny_code_writes.py`` does not yet exist.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_KANBAN_SRC = _REPO_ROOT / "serve" / "kanban" / "src" / "owlbear_kanban"
_KANBAN_TESTS = _REPO_ROOT / "serve" / "kanban" / "tests"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_storage_imports(py_file: Path) -> list[int]:  # noqa: C901
    """Return line numbers where ``owlbear_kanban.storage`` (the public surface
    module) is imported in *py_file*.

    Detects:
      - ``from owlbear_kanban.storage import X``
      - ``from owlbear_kanban.storage.sub import X``
      - ``import owlbear_kanban.storage``
      - ``from owlbear_kanban import storage``
            - ``__import__("owlbear_kanban.storage", ...)``
            - ``importlib.import_module("owlbear_kanban.storage")``

    Does NOT flag ``owlbear_kanban.storage_io`` — that is the private primitive.
    """
    source = py_file.read_text(encoding="utf-8")
    if "storage" not in source:
        return []
    tree = ast.parse(source, filename=str(py_file))
    lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if (
                module == "owlbear_kanban.storage"
                or module.startswith("owlbear_kanban.storage.")
                or (module == "owlbear_kanban" and any(a.name == "storage" for a in node.names))
            ):
                lines.append(node.lineno)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "owlbear_kanban.storage" or alias.name.startswith(
                    "owlbear_kanban.storage."
                ):
                    lines.append(node.lineno)
        elif isinstance(node, ast.Call) and _call_arg_is_storage(node):
            if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                lines.append(node.lineno)
            if isinstance(node.func, ast.Attribute) and node.func.attr == "import_module":
                lines.append(node.lineno)
    return lines


def _call_arg_is_storage(node: ast.Call) -> bool:
    """Return True if *node* dynamically imports an owlbear_kanban.storage module."""
    return (
        node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
        and node.args[0].value.startswith("owlbear_kanban.storage")
    )


def _call_arg_is_task_io(node: ast.Call) -> bool:
    """Return True if *node* is a dynamic import call with a task_io argument."""
    return (
        node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
        and "task_io" in node.args[0].value
    )


def _find_task_io_references(py_file: Path) -> list[tuple[str, int]]:
    """Return (kind, lineno) tuples for every reference to ``task_io`` in
    *py_file*, covering:

    - ``from owlbear_kanban.task_io import X``
    - ``import owlbear_kanban.task_io``
    - ``__import__("owlbear_kanban.task_io", ...)``
    - ``importlib.import_module("owlbear_kanban.task_io")``
    """
    source = py_file.read_text(encoding="utf-8")
    if "task_io" not in source:
        return []
    tree = ast.parse(source, filename=str(py_file))
    hits: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and "task_io" in (node.module or ""):
            hits.append(("from-import", node.lineno))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if "task_io" in alias.name:
                    hits.append(("import", node.lineno))
        elif isinstance(node, ast.Call) and _call_arg_is_task_io(node):
            if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                hits.append(("__import__", node.lineno))
            elif isinstance(node.func, ast.Attribute) and node.func.attr == "import_module":
                hits.append(("import_module", node.lineno))
    return hits


# ---------------------------------------------------------------------------
# AC-C45 — intra-package storage boundary
# ---------------------------------------------------------------------------


class TestFromAC_KanbanInternalBoundary:
    """AC-C45: only ``engine.py`` may import from ``owlbear_kanban.storage``.

    The storage module is the single public surface the engine consumes.
    ``dispatch.py``, ``corruption.py``, and every other intra-package module
    must NOT import from it directly — they should use ``storage_io``,
    ``body_parser``, ``activity_store``, or ``corruption`` as appropriate.
    """

    def test_only_engine_may_import_owlbear_kanban_storage(self) -> None:
        """AC-C45: no owlbear_kanban source file except engine.py imports storage."""
        violations: list[str] = []
        for py_file in sorted(_KANBAN_SRC.glob("*.py")):
            if py_file.name in {"engine.py", "__init__.py"}:
                continue
            lines = _find_storage_imports(py_file)
            for lineno in lines:
                violations.append(f"  {py_file.name}:{lineno}")
        assert not violations, (
            "Only engine.py may import from owlbear_kanban.storage; "
            "violations found (update these files to import from storage_io, "
            "body_parser, activity_store, or corruption directly):\n"
            + "\n".join(violations)
        )

    def test_storage_io_dynamic_import_not_flagged_as_storage_violation(
        self, tmp_path: Path
    ) -> None:
        """AC-C45: _find_storage_imports must NOT flag owlbear_kanban.storage_io imports.

        storage_io is a different (private primitive) module.  The scanner's
        ``_call_arg_is_storage`` helper uses ``startswith("owlbear_kanban.storage")``
        which incorrectly matches ``"owlbear_kanban.storage_io"`` — a false positive
        that would block legal imports from non-engine source files.
        """
        synthetic = tmp_path / "synthetic_module.py"
        synthetic.write_text(
            'import importlib\nimportlib.import_module("owlbear_kanban.storage_io")\n',
            encoding="utf-8",
        )
        violations = _find_storage_imports(synthetic)
        assert violations == [], (
            "importlib.import_module('owlbear_kanban.storage_io') must not be flagged as "
            "an owlbear_kanban.storage boundary violation — storage_io is not the storage "
            "surface module.  Fix _call_arg_is_storage to use exact equality instead of "
            f"startswith().  Lines flagged: {violations}"
        )

    def test_scanner_detects_variable_held_storage_import(self, tmp_path: Path) -> None:
        """AC-C45: _find_storage_imports must detect variable-held importlib calls.

        A pattern like::

            module_name = "owlbear_kanban.storage"
            importlib.import_module(module_name)

        evades the current scanner because it only inspects literal-string
        ``ast.Constant`` arguments.  A non-engine module can bypass the boundary
        using a variable-held module name.
        """
        synthetic = tmp_path / "synthetic_variable.py"
        synthetic.write_text(
            'import importlib\n'
            'module_name = "owlbear_kanban.storage"\n'
            'importlib.import_module(module_name)\n',
            encoding="utf-8",
        )
        violations = _find_storage_imports(synthetic)
        assert violations, (
            "_find_storage_imports must detect importlib.import_module calls whose "
            "argument is a variable holding 'owlbear_kanban.storage'.  Currently only "
            "literal ast.Constant string arguments are detected, leaving a bypass path "
            "for variable-indirected dynamic imports."
        )


# ---------------------------------------------------------------------------
# 4th AC — no task_io import anywhere in the codebase
# ---------------------------------------------------------------------------


class TestFromAC_TaskIoGlobalRemoval:
    """4th AC: no import of removed ``task_io`` module anywhere in the codebase.

    This extends beyond the owlbear_kanban source package to include the test
    suite under ``serve/kanban/tests/`` and the workspace-level ``tests/``
    directory.
    """

    def test_no_task_io_reference_in_kanban_test_suite(self) -> None:
        """No file in serve/kanban/tests/ may import or __import__ task_io."""
        violations: list[str] = []
        for py_file in sorted(_KANBAN_TESTS.rglob("*.py")):
            hits = _find_task_io_references(py_file)
            for kind, lineno in hits:
                violations.append(f"  {py_file.name}:{lineno} ({kind})")
        assert not violations, (
            "serve/kanban/tests/ files must not reference the deleted task_io "
            "module; these references must be updated to use storage or "
            "storage_io:\n" + "\n".join(violations)
        )

    def test_no_task_io_reference_anywhere_in_codebase(
        self, project_root: Path
    ) -> None:
        """4th AC: no Python file in serve/ or tests/ imports task_io."""
        serve_root = project_root / "serve"
        tests_root = project_root / "tests"
        violations: list[str] = []
        for root in (serve_root, tests_root):
            for py_file in sorted(root.rglob("*.py")):
                hits = _find_task_io_references(py_file)
                for kind, lineno in hits:
                    rel = py_file.relative_to(project_root)
                    violations.append(f"  {rel}:{lineno} ({kind})")
        assert not violations, (
            "These files reference the deleted owlbear_kanban.task_io module "
            "and must be updated:\n" + "\n".join(violations)
        )


# ---------------------------------------------------------------------------
# AC-C46 — storage-test isolation file must exist
# ---------------------------------------------------------------------------


class TestFromAC_StorageTestIsolation:
    """AC-C46: ``tests/test_deny_code_writes.py`` must exist.

    This file provides enforcement that storage tests are prohibited from
    writing outside ``tmp_path``. Its absence means the convention is not
    programmatically enforced.
    """

    def test_deny_code_writes_test_file_exists(self, project_root: Path) -> None:
        """AC-C46: tests/test_deny_code_writes.py must exist."""
        deny_file = project_root / "tests" / "test_deny_code_writes.py"
        assert deny_file.exists(), (
            "tests/test_deny_code_writes.py does not exist; "
            "create it with enforcement tests that verify storage test files "
            "(serve/kanban/tests/test_storage*.py, test_activity_store*.py, "
            "test_corruption*.py) are isolated to tmp_path (AC-C46)"
        )


# ---------------------------------------------------------------------------
# 3rd AC — durable boundary coverage for the new storage-tier layout
# ---------------------------------------------------------------------------


class TestFromAC_NewModuleLayout:
    """3rd AC: boundary enforcement for the new layout is permanent, not just task-scoped.

    The 3rd AC states boundary tests pass with the new module layout
    (storage.py, storage_io.py, body_parser.py, activity_store.py, corruption.py,
    migrate.py, predicates.py).  For this to be a *permanent* guarantee the
    durable boundary suite (``tests/test_package_boundary.py``) must adopt the
    intra-kanban storage boundary check rather than leaving it only in the
    task-scoped file (which is cleaned up post-archive).
    """

    def test_durable_boundary_suite_includes_intra_kanban_storage_check(
        self, project_root: Path
    ) -> None:
        """tests/test_package_boundary.py must permanently enforce the storage boundary.

        The rule that only ``engine.py`` may import ``owlbear_kanban.storage``
        currently lives only in the task-scoped ``test_package_boundary_1064.py``.
        After this task is archived the task-scoped file will be removed, leaving
        no durable enforcement.  The durable suite must adopt this check.
        """
        boundary_file = project_root / "tests" / "test_package_boundary.py"
        content = boundary_file.read_text(encoding="utf-8")
        assert "engine.py" in content, (
            "tests/test_package_boundary.py must reference 'engine.py' as part of a "
            "permanent intra-kanban storage boundary test.  Currently this enforcement "
            "exists only in the task-scoped test_package_boundary_1064.py.  Add a "
            "TestFromAC_KanbanInternalBoundary (or equivalent) class to the durable suite "
            "so the AC-C45 constraint survives post-archive cleanup."
        )


