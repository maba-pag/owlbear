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
    bound_strings = _collect_string_bindings(tree)
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
        elif isinstance(node, ast.Call) and _call_arg_is_storage(node, bound_strings):
            if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                lines.append(node.lineno)
            if isinstance(node.func, ast.Attribute) and node.func.attr == "import_module":
                lines.append(node.lineno)
    return lines


def _collect_string_bindings(tree: ast.AST) -> dict[str, str]:
    """Collect simple name-to-string bindings in module scope and function scope."""
    bound: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if (
                isinstance(target, ast.Name)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                bound[target.id] = node.value.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            bound[node.target.id] = node.value.value
    return bound


def _call_arg_is_storage(node: ast.Call, bound_strings: dict[str, str]) -> bool:
    """Return True if *node* dynamically imports an owlbear_kanban.storage module."""
    if not node.args:
        return False
    first_arg = node.args[0]
    module_name: str | None = None
    if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
        module_name = first_arg.value
    elif isinstance(first_arg, ast.Name):
        module_name = bound_strings.get(first_arg.id)
    return bool(
        module_name
        and (
            module_name == "owlbear_kanban.storage"
            or module_name.startswith("owlbear_kanban.storage.")
        )
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

    def test_durable_suite_detects_importlib_storage_import(self, tmp_path: Path) -> None:
        """AC-C45 (refined): the durable suite helper must detect
        importlib.import_module("owlbear_kanban.storage") in non-engine modules.

        ``_find_kanban_storage_import_violations`` in ``tests/test_package_boundary.py``
        only scans ``ast.ImportFrom`` and ``ast.Import`` nodes.  A non-engine module
        using ``importlib.import_module("owlbear_kanban.storage")`` bypasses the
        static-import guard entirely.  The refined AC-C45 requires this dynamic
        form to also be detected by the durable boundary helper.
        """
        from tests.test_package_boundary import _find_kanban_storage_import_violations

        kanban_src = tmp_path / "serve" / "kanban" / "src" / "owlbear_kanban"
        kanban_src.mkdir(parents=True)
        (kanban_src / "dispatch.py").write_text(
            "import importlib\n"
            'importlib.import_module("owlbear_kanban.storage")\n',
            encoding="utf-8",
        )
        violations = _find_kanban_storage_import_violations(tmp_path)
        assert violations, (
            "_find_kanban_storage_import_violations (tests/test_package_boundary.py) must "
            "detect importlib.import_module('owlbear_kanban.storage') in non-engine source "
            "files.  The durable helper currently only checks ast.ImportFrom and ast.Import "
            "nodes, leaving dynamic imports undetected.  Refined AC-C45 requires both "
            "static and dynamic import forms to be covered by the durable boundary suite."
        )

    def test_durable_suite_detects_dunder_import_storage_call(self, tmp_path: Path) -> None:
        """AC-C45 (refined): the durable suite helper must detect
        __import__("owlbear_kanban.storage") in non-engine modules.

        ``__import__`` is a second dynamic-import bypass form that the current
        durable helper does not scan.  Refined AC-C45 requires both
        ``importlib.import_module`` and ``__import__`` to be detected by
        ``_find_kanban_storage_import_violations`` in ``tests/test_package_boundary.py``.
        """
        from tests.test_package_boundary import _find_kanban_storage_import_violations

        kanban_src = tmp_path / "serve" / "kanban" / "src" / "owlbear_kanban"
        kanban_src.mkdir(parents=True)
        (kanban_src / "corruption.py").write_text(
            '__import__("owlbear_kanban.storage")\n',
            encoding="utf-8",
        )
        violations = _find_kanban_storage_import_violations(tmp_path)
        assert violations, (
            "_find_kanban_storage_import_violations must detect "
            "__import__('owlbear_kanban.storage') calls in non-engine source files.  "
            "The current durable helper only scans ast.ImportFrom / ast.Import nodes and "
            "misses the __import__() dynamic form.  Refined AC-C45 requires coverage of "
            "this bypass path in the durable boundary suite."
        )

    def test_durable_suite_detects_from_owlbear_kanban_import_storage(
        self, tmp_path: Path
    ) -> None:
        """AC-C45a (v3): durable helper must catch ``from owlbear_kanban import storage``.

        The alias import form ``from owlbear_kanban import storage`` is a valid
        Python spelling that violates the AC-C45a boundary for non-engine source
        files.  The task-scoped helper ``_find_storage_imports`` already detects
        it (``tests/test_package_boundary_1064.py:67``), but the durable helper
        ``_find_kanban_storage_import_violations`` in ``tests/test_package_boundary.py``
        only checks ``module == "owlbear_kanban.storage"`` in the ``ast.ImportFrom``
        branch (line ~136-138), missing this alias form.
        """
        from tests.test_package_boundary import _find_kanban_storage_import_violations

        kanban_src = tmp_path / "serve" / "kanban" / "src" / "owlbear_kanban"
        kanban_src.mkdir(parents=True)
        (kanban_src / "engine.py").write_text("", encoding="utf-8")
        (kanban_src / "__init__.py").write_text("", encoding="utf-8")
        (kanban_src / "bad.py").write_text(
            "from owlbear_kanban import storage\n", encoding="utf-8"
        )
        violations = _find_kanban_storage_import_violations(tmp_path)
        assert violations, (
            "Durable helper _find_kanban_storage_import_violations must detect "
            "'from owlbear_kanban import storage' (alias import form) in non-engine "
            "source files.  Fix: add "
            "`or (module == 'owlbear_kanban' and any(a.name == 'storage' for a in node.names))` "
            "to the ast.ImportFrom branch at tests/test_package_boundary.py:~136-138."
        )
        assert any("bad.py" in v for v in violations), (
            "The violation entry must identify bad.py as the offending file."
        )

    def test_durable_suite_alias_form_in_init_not_flagged(self, tmp_path: Path) -> None:
        """AC-C45a (v4): ``from owlbear_kanban import storage`` in ``__init__.py``
        must NOT produce a violation.

        Arch v4 explicitly exempts ``__init__.py`` alongside ``engine.py`` from
        the storage-import boundary.  ``__init__.py`` is a package API re-export
        surface, not a feature module, so a storage re-export there is a
        deliberate API expansion rather than an accidental boundary leak.

        This is the negative counterpart to
        ``test_durable_suite_detects_from_owlbear_kanban_import_storage``:
        alias-form in ``__init__.py`` is *exempt*; alias-form in feature modules
        is *detected*.  If the durable helper ever drops ``__init__.py`` from its
        skip-list, this test will fail.
        """
        from tests.test_package_boundary import _find_kanban_storage_import_violations

        kanban_src = tmp_path / "serve" / "kanban" / "src" / "owlbear_kanban"
        kanban_src.mkdir(parents=True)
        (kanban_src / "__init__.py").write_text(
            "from owlbear_kanban import storage\n", encoding="utf-8"
        )
        violations = _find_kanban_storage_import_violations(tmp_path)
        assert not violations, (
            "AC-C45a (v4) explicitly exempts __init__.py from the storage-import "
            "boundary.  `from owlbear_kanban import storage` in __init__.py must NOT "
            "be flagged as a violation.  The durable helper's skip-list must include "
            "both 'engine.py' and '__init__.py'; removing __init__.py from the skip-list "
            "violates the arch v4 decision.\n"
            f"Current violations returned: {violations}"
        )

    def test_durable_suite_detects_direct_static_storage_import(
        self, tmp_path: Path
    ) -> None:
        """AC-C45a regression guard: durable helper detects direct
        ``from owlbear_kanban.storage import X`` in non-engine source files.

        The durable helper at ``tests/test_package_boundary.py:136-148`` implements
        the direct static branches (``ast.ImportFrom`` with ``module ==
        'owlbear_kanban.storage'`` and ``ast.Import``).  This regression guard
        proves those branches remain active: removing them would cause this test
        to fail.
        """
        from tests.test_package_boundary import _find_kanban_storage_import_violations

        kanban_src = tmp_path / "serve" / "kanban" / "src" / "owlbear_kanban"
        kanban_src.mkdir(parents=True)
        (kanban_src / "engine.py").write_text("", encoding="utf-8")
        (kanban_src / "bad.py").write_text(
            "from owlbear_kanban.storage import read_task\n", encoding="utf-8"
        )
        violations = _find_kanban_storage_import_violations(tmp_path)
        assert violations, (
            "Durable helper must detect direct 'from owlbear_kanban.storage import X' "
            "in non-engine source files"
        )
        assert any("bad.py" in v for v in violations)


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


# ---------------------------------------------------------------------------
# AC-C45b — durable suite must enforce task_io removal from kanban sources
# ---------------------------------------------------------------------------


class TestFromAC_KanbanTaskIoRemoval:
    """AC-C45b: ``tests/test_package_boundary.py`` must enforce that no
    ``owlbear_kanban`` source file imports the deleted ``task_io`` module.

    The refined AC-C45b requires a new ``_find_task_io_import_violations``
    helper and a ``TestFromAC_KanbanTaskIoRemoval`` class in the durable suite
    (``tests/test_package_boundary.py``).  The task-scoped file already has
    ``_find_task_io_references`` (lines 136-175) which can serve as a reference.

    This test proves the durable enforcement does not yet exist by attempting
    to import the helper and verifying it detects violations in a synthetic
    non-engine file.
    """

    def test_durable_suite_task_io_helper_detects_static_import(
        self, tmp_path: Path
    ) -> None:
        """AC-C45b: ``_find_task_io_import_violations`` must exist in the durable suite
        and detect ``from owlbear_kanban.task_io import write_task`` in source files.

        The import will raise ``ImportError`` until the helper is added to
        ``tests/test_package_boundary.py``.  Once it exists, the synthetic
        project must yield at least one violation entry so the builder confirms
        the helper actually scans for ``task_io`` imports.
        """
        from tests.test_package_boundary import _find_task_io_import_violations

        kanban_src = tmp_path / "serve" / "kanban" / "src" / "owlbear_kanban"
        kanban_src.mkdir(parents=True)
        (kanban_src / "dispatch.py").write_text(
            "from owlbear_kanban.task_io import write_task\n",
            encoding="utf-8",
        )
        violations = _find_task_io_import_violations(tmp_path)
        assert violations, (
            "_find_task_io_import_violations (tests/test_package_boundary.py) must "
            "detect 'from owlbear_kanban.task_io import write_task' in non-engine "
            "source files.  Add this helper to the durable suite per refined AC-C45b."
        )

    def test_durable_suite_task_io_init_py_exemption_in_place(self, tmp_path: Path) -> None:
        """AC-C45b (v5): ``from owlbear_kanban.task_io import X`` in ``__init__.py``
        must NOT produce a task_io violation.

        Arch v5 explicitly exempts ``__init__.py`` from C45b for the same reason
        as C45a (v4): ``__init__.py`` is a package API re-export surface, not a
        feature module.  A deleted-module import in ``__init__.py`` would fail at
        import time with ``ModuleNotFoundError``, making the structural scanner
        redundant there.

        This is the negative counterpart to
        ``test_durable_suite_task_io_helper_detects_static_import``:
        task_io import in ``__init__.py`` is *exempt*; task_io import in feature
        modules is *detected*.  If the durable helper ever drops ``__init__.py``
        from its skip-list, this test will fail.
        """
        from tests.test_package_boundary import _find_task_io_import_violations

        kanban_src = tmp_path / "serve" / "kanban" / "src" / "owlbear_kanban"
        kanban_src.mkdir(parents=True)
        (kanban_src / "__init__.py").write_text(
            "from owlbear_kanban.task_io import write_task\n", encoding="utf-8"
        )
        violations = _find_task_io_import_violations(tmp_path)
        assert not violations, (
            "AC-C45b (v5) explicitly exempts __init__.py from the task_io-import "
            "boundary scanner.  `from owlbear_kanban.task_io import write_task` in "
            "__init__.py must NOT be flagged as a violation — a deleted-module import "
            "there would fail at import time with ModuleNotFoundError, making the "
            "structural guard redundant.  The durable helper's skip-list must include "
            "'__init__.py'; removing it violates the arch v5 decision.\n"
            f"Current violations returned: {violations}"
        )

    def test_durable_suite_detects_dynamic_task_io_import(self, tmp_path: Path) -> None:
        """AC-C45b regression guard: durable helper detects
        ``importlib.import_module("owlbear_kanban.task_io")`` in source files.

        The durable helper at ``tests/test_package_boundary.py:203-212`` implements
        the dynamic task_io detection branch.  This regression guard proves that
        branch is active: removing it would cause this test to fail.
        """
        from tests.test_package_boundary import _find_task_io_import_violations

        kanban_src = tmp_path / "serve" / "kanban" / "src" / "owlbear_kanban"
        kanban_src.mkdir(parents=True)
        (kanban_src / "dispatch.py").write_text(
            'import importlib\nimportlib.import_module("owlbear_kanban.task_io")\n',
            encoding="utf-8",
        )
        violations = _find_task_io_import_violations(tmp_path)
        assert violations, (
            "Durable helper must detect importlib.import_module('owlbear_kanban.task_io') "
            "in source files"
        )
        assert any("dispatch.py" in v for v in violations)


