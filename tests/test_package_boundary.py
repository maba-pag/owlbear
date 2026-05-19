"""Cross-package import boundary tests for serve/ packages (#1038).

Verifies that no owlbear_* package imports from another owlbear_*
package unless explicitly declared in ALLOWED_IMPORTS.

Policy: All imports are scanned, including those inside
``if TYPE_CHECKING:`` blocks. Runtime-vs-typecheck distinction is
irrelevant for boundary enforcement — a TYPE_CHECKING import still
creates a coupling contract.

Ground truth for ALLOWED_IMPORTS: ``serve/*/pyproject.toml`` workspace
dependencies.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# ALLOWED_IMPORTS — the boundary contract
# ---------------------------------------------------------------------------

ALLOWED_IMPORTS: dict[str, set[str]] = {
    "owlbear_browser": set(),
    "owlbear_cockpit": {"owlbear_kanban", "owlbear_memory"},
    "owlbear_kanban": set(),
    "owlbear_knowledge": set(),
    "owlbear_memory": set(),
    "owlbear_mcp_browser": {"owlbear_browser"},
    "owlbear_mcp_kanban": {"owlbear_kanban"},
    "owlbear_mcp_knowledge": {"owlbear_knowledge"},
    "owlbear_mcp_memory": {"owlbear_memory"},
    "owlbear_tools": set(),
}

_ALL_NAMESPACES: frozenset[str] = frozenset(ALLOWED_IMPORTS)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _discover_namespaces(serve_root: Path) -> set[str]:
    """Return all owlbear namespace package dirs under ``serve/*/src/``."""
    found: set[str] = set()
    for src_dir in serve_root.glob("*/src"):
        for entry in src_dir.iterdir():
            if entry.is_dir() and entry.name.startswith("owlbear"):
                found.add(entry.name)
    return found


def _owlbear_root(name: str | None) -> str | None:
    """Return the owlbear namespace root of a dotted module/import path, or None."""
    if not name:
        return None
    root = name.split(".")[0]
    return root if root in _ALL_NAMESPACES else None


def _scan_file(
    py_file: Path,
    src_dir: Path,
    namespace: str,
    allowed: set[str],
) -> list[tuple[str, str, str, int]]:
    """Return boundary violations found in a single Python file."""
    violations: list[tuple[str, str, str, int]] = []
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported = _owlbear_root(node.module)
            if imported and imported != namespace and imported not in allowed:
                violations.append(
                    (
                        namespace,
                        str(py_file.relative_to(src_dir)),
                        imported,
                        node.lineno,
                    )
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported = _owlbear_root(alias.name)
                if imported and imported != namespace and imported not in allowed:
                    violations.append(
                        (
                            namespace,
                            str(py_file.relative_to(src_dir)),
                            imported,
                            node.lineno,
                        )
                    )
    return violations


def _collect_violations(serve_root: Path) -> list[tuple[str, str, str, int]]:
    """AST-scan all ``serve/*/src/`` Python files for undeclared cross-namespace imports.

    Scans both ``from X import Y`` and bare ``import X`` forms.
    Includes imports inside ``if TYPE_CHECKING:`` blocks.

    Returns a list of ``(namespace, relative_file, imported_namespace, lineno)``.
    """
    violations: list[tuple[str, str, str, int]] = []
    for src_dir in sorted(serve_root.glob("*/src")):
        for ns_dir in sorted(src_dir.iterdir()):
            if not (ns_dir.is_dir() and ns_dir.name.startswith("owlbear")):
                continue
            namespace = ns_dir.name
            allowed = ALLOWED_IMPORTS.get(namespace, set())
            for py_file in sorted(ns_dir.rglob("*.py")):
                violations.extend(_scan_file(py_file, src_dir, namespace, allowed))
    return violations


def _find_kanban_storage_import_violations(  # noqa: C901, PLR0912
    project_root: Path,
) -> list[str]:
    """Return source-file locations that import owlbear_kanban.storage outside engine.py."""
    kanban_src = project_root / "serve" / "kanban" / "src" / "owlbear_kanban"
    violations: list[str] = []
    for py_file in sorted(kanban_src.glob("*.py")):
        if py_file.name in {"engine.py", "__init__.py"}:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if (
                    module == "owlbear_kanban.storage"
                    or module.startswith("owlbear_kanban.storage.")
                    or (module == "owlbear_kanban" and any(alias.name == "storage" for alias in node.names))
                ):
                    violations.append(f"{py_file.name}:{node.lineno}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "owlbear_kanban.storage" or alias.name.startswith("owlbear_kanban.storage."):
                        violations.append(f"{py_file.name}:{node.lineno}")
            elif isinstance(node, ast.Call) and node.args:
                target_module: str | None = None
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                    target_module = first_arg.value
                is_storage_target = bool(
                    target_module
                    and (
                        target_module == "owlbear_kanban.storage" or target_module.startswith("owlbear_kanban.storage.")
                    )
                )
                if not is_storage_target:
                    continue
                if (isinstance(node.func, ast.Name) and node.func.id == "__import__") or (
                    isinstance(node.func, ast.Attribute) and node.func.attr == "import_module"
                ):
                    violations.append(f"{py_file.name}:{node.lineno}")
    return violations


def _find_task_io_import_violations(project_root: Path) -> list[str]:  # noqa: C901, PLR0912
    """Return source-file locations that import deleted owlbear_kanban.task_io."""
    kanban_src = project_root / "serve" / "kanban" / "src" / "owlbear_kanban"
    violations: list[str] = []
    for py_file in sorted(kanban_src.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if (
                    module == "owlbear_kanban.task_io"
                    or module.startswith("owlbear_kanban.task_io.")
                    or (module == "owlbear_kanban" and any(a.name == "task_io" for a in node.names))
                ):
                    violations.append(f"{py_file.name}:{node.lineno}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "owlbear_kanban.task_io" or alias.name.startswith("owlbear_kanban.task_io."):
                        violations.append(f"{py_file.name}:{node.lineno}")
            elif isinstance(node, ast.Call) and node.args:
                first_arg = node.args[0]
                if not (isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str)):
                    continue
                target_module = first_arg.value
                is_task_io_target = target_module == "owlbear_kanban.task_io" or target_module.startswith(
                    "owlbear_kanban.task_io."
                )
                if not is_task_io_target:
                    continue
                if (isinstance(node.func, ast.Name) and node.func.id == "__import__") or (
                    isinstance(node.func, ast.Attribute) and node.func.attr == "import_module"
                ):
                    violations.append(f"{py_file.name}:{node.lineno}")
    return violations


# ---------------------------------------------------------------------------
# AC#1, AC#4: ALLOWED_IMPORTS structure and namespace key coverage
# ---------------------------------------------------------------------------


class TestFromAC_AllowedImportsSchema:
    """ALLOWED_IMPORTS is a correctly-typed dict covering all serve/ namespaces.

    AC#1: ``ALLOWED_IMPORTS: dict[str, set[str]]`` exists
    AC#2: all serve/*/src/ namespaces have an entry
    AC#4: keys are validated against discovered namespaces
    """

    def test_allowed_imports_is_dict(self) -> None:
        """AC#1: ALLOWED_IMPORTS is a dict."""
        assert isinstance(ALLOWED_IMPORTS, dict)

    def test_allowed_imports_values_are_sets(self) -> None:
        """AC#1: every value is a set (not a list, tuple, or None)."""
        for ns, allowed in ALLOWED_IMPORTS.items():
            assert isinstance(allowed, set), f"ALLOWED_IMPORTS[{ns!r}]: expected set, got {type(allowed).__name__}"

    def test_allowed_imports_covers_all_discovered_namespaces(self, project_root: Path) -> None:
        """AC#2, AC#4: every namespace under serve/*/src/ appears in ALLOWED_IMPORTS."""
        serve_root = project_root / "serve"
        discovered = _discover_namespaces(serve_root)
        missing = discovered - set(ALLOWED_IMPORTS)
        assert not missing, f"Namespaces found in serve/ but missing from ALLOWED_IMPORTS: {sorted(missing)}"

    def test_allowed_imports_has_no_unknown_keys(self, project_root: Path) -> None:
        """AC#4: ALLOWED_IMPORTS has no keys for namespaces that don't exist on disk."""
        serve_root = project_root / "serve"
        discovered = _discover_namespaces(serve_root)
        extra = set(ALLOWED_IMPORTS) - discovered
        assert not extra, f"ALLOWED_IMPORTS has keys for non-existent namespaces: {sorted(extra)}"


# ---------------------------------------------------------------------------
# AC#3, AC#5: AST boundary scan — current codebase must be clean
# ---------------------------------------------------------------------------


class TestFromAC_CrossImportEnforcement:
    """AST scan enforces namespace-level import boundaries across serve/ packages.

    AC#3: undeclared cross-namespace imports are detected
    AC#5: no false positives against the current codebase
    """

    def test_no_undeclared_cross_namespace_imports(self, project_root: Path) -> None:
        """AC#3, AC#5: current codebase has zero boundary violations."""
        serve_root = project_root / "serve"
        violations = _collect_violations(serve_root)
        if violations:
            lines = [
                f"  {ns}/{relfile}:{lineno} — imports {imported!r} (not in ALLOWED_IMPORTS[{ns!r}])"
                for ns, relfile, imported, lineno in violations
            ]
            pytest.fail("Undeclared cross-namespace imports found:\n" + "\n".join(lines))

    def test_scan_detects_synthetic_from_import_violation(self, tmp_path: Path) -> None:
        """AC#3: scanner catches a synthetic 'from X import Y' boundary violation."""
        fake_src = tmp_path / "fake_pkg" / "src" / "owlbear_tools"
        fake_src.mkdir(parents=True)
        (fake_src / "bad.py").write_text("from owlbear_kanban import KanbanEngine\n", encoding="utf-8")
        violations = _collect_violations(tmp_path)
        assert len(violations) >= 1
        assert any(
            ns == "owlbear_tools" and imported == "owlbear_kanban" for ns, _relfile, imported, _lineno in violations
        )

    def test_scan_detects_synthetic_bare_import_violation(self, tmp_path: Path) -> None:
        """AC#3: scanner catches a synthetic bare 'import X' boundary violation."""
        fake_src = tmp_path / "fake_pkg" / "src" / "owlbear_tools"
        fake_src.mkdir(parents=True)
        (fake_src / "bad.py").write_text("import owlbear_kanban\n", encoding="utf-8")
        violations = _collect_violations(tmp_path)
        assert len(violations) >= 1
        assert any(
            ns == "owlbear_tools" and imported == "owlbear_kanban" for ns, _relfile, imported, _lineno in violations
        )

    def test_scan_ignores_intra_namespace_imports(self, tmp_path: Path) -> None:
        """AC#3: intra-package self-imports are not reported as violations."""
        fake_src = tmp_path / "fake_pkg" / "src" / "owlbear_kanban"
        fake_src.mkdir(parents=True)
        (fake_src / "internal.py").write_text("from owlbear_kanban.engine import KanbanEngine\n", encoding="utf-8")
        violations = _collect_violations(tmp_path)
        assert not violations

    def test_scan_allows_declared_cross_namespace_imports(self, tmp_path: Path) -> None:
        """AC#3: imports that appear in ALLOWED_IMPORTS are not violations."""
        fake_src = tmp_path / "fake_pkg" / "src" / "owlbear_cockpit"
        fake_src.mkdir(parents=True)
        (fake_src / "deps.py").write_text("from owlbear_kanban import KanbanEngine\n", encoding="utf-8")
        violations = _collect_violations(tmp_path)
        assert not violations

    def test_scan_catches_type_checking_import_violation(self, tmp_path: Path) -> None:
        """AC#3: imports inside TYPE_CHECKING blocks are also scanned."""
        fake_src = tmp_path / "fake_pkg" / "src" / "owlbear_tools"
        fake_src.mkdir(parents=True)
        (fake_src / "typed.py").write_text(
            "from __future__ import annotations\n"
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    from owlbear_kanban import KanbanEngine\n",
            encoding="utf-8",
        )
        violations = _collect_violations(tmp_path)
        assert len(violations) >= 1
        assert any(
            ns == "owlbear_tools" and imported == "owlbear_kanban" for ns, _relfile, imported, _lineno in violations
        )


class TestFromAC_KanbanInternalBoundary:
    """Durable AC-C45 guard: only engine.py may import owlbear_kanban.storage."""

    def test_only_engine_may_import_owlbear_kanban_storage(self, project_root: Path) -> None:
        violations = _find_kanban_storage_import_violations(project_root)
        assert not violations, "Only engine.py may import owlbear_kanban.storage; found violations:\n" + "\n".join(
            f"  {entry}" for entry in violations
        )


class TestFromAC_KanbanTaskIoRemoval:
    """Durable AC-C45b guard: no source file may import deleted task_io."""

    def test_no_source_file_imports_task_io(self, project_root: Path) -> None:
        violations = _find_task_io_import_violations(project_root)
        assert not violations, (
            "owlbear_kanban source files must not import deleted owlbear_kanban.task_io; "
            "found violations:\n" + "\n".join(f"  {entry}" for entry in violations)
        )


# Promoted from archived task #1064.

_REPO_ROOT = Path(__file__).parent.parent
_KANBAN_SRC = _REPO_ROOT / "serve" / "kanban" / "src" / "owlbear_kanban"
_KANBAN_TESTS = _REPO_ROOT / "serve" / "kanban" / "tests"


def _find_storage_imports(py_file: Path) -> list[int]:  # noqa: C901
    """Return line numbers where ``owlbear_kanban.storage`` is imported in *py_file*."""
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
                if alias.name == "owlbear_kanban.storage" or alias.name.startswith("owlbear_kanban.storage."):
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
        module_name and (module_name == "owlbear_kanban.storage" or module_name.startswith("owlbear_kanban.storage."))
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
    """Return (kind, lineno) tuples for every reference to ``task_io`` in *py_file*."""
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


class TestFromAC_KanbanInternalBoundary1064:
    """AC-C45 refinements promoted from task #1064."""

    def test_only_engine_may_import_owlbear_kanban_storage(self) -> None:
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
            "body_parser, activity_store, or corruption directly):\n" + "\n".join(violations)
        )

    def test_storage_io_dynamic_import_not_flagged_as_storage_violation(self, tmp_path: Path) -> None:
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
        synthetic = tmp_path / "synthetic_variable.py"
        synthetic.write_text(
            'import importlib\nmodule_name = "owlbear_kanban.storage"\nimportlib.import_module(module_name)\n',
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
        from tests.test_package_boundary import _find_kanban_storage_import_violations

        kanban_src = tmp_path / "serve" / "kanban" / "src" / "owlbear_kanban"
        kanban_src.mkdir(parents=True)
        (kanban_src / "dispatch.py").write_text(
            'import importlib\nimportlib.import_module("owlbear_kanban.storage")\n',
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

    def test_durable_suite_detects_from_owlbear_kanban_import_storage(self, tmp_path: Path) -> None:
        from tests.test_package_boundary import _find_kanban_storage_import_violations

        kanban_src = tmp_path / "serve" / "kanban" / "src" / "owlbear_kanban"
        kanban_src.mkdir(parents=True)
        (kanban_src / "engine.py").write_text("", encoding="utf-8")
        (kanban_src / "__init__.py").write_text("", encoding="utf-8")
        (kanban_src / "bad.py").write_text("from owlbear_kanban import storage\n", encoding="utf-8")
        violations = _find_kanban_storage_import_violations(tmp_path)
        assert violations, (
            "Durable helper _find_kanban_storage_import_violations must detect "
            "'from owlbear_kanban import storage' (alias import form) in non-engine "
            "source files.  Fix: add "
            "`or (module == 'owlbear_kanban' and any(a.name == 'storage' for a in node.names))` "
            "to the ast.ImportFrom branch at tests/test_package_boundary.py:~136-138."
        )
        assert any("bad.py" in violation for violation in violations), (
            "The violation entry must identify bad.py as the offending file."
        )

    def test_durable_suite_alias_form_in_init_not_flagged(self, tmp_path: Path) -> None:
        from tests.test_package_boundary import _find_kanban_storage_import_violations

        kanban_src = tmp_path / "serve" / "kanban" / "src" / "owlbear_kanban"
        kanban_src.mkdir(parents=True)
        (kanban_src / "__init__.py").write_text("from owlbear_kanban import storage\n", encoding="utf-8")
        violations = _find_kanban_storage_import_violations(tmp_path)
        assert not violations, (
            "AC-C45a (v4) explicitly exempts __init__.py from the storage-import "
            "boundary.  `from owlbear_kanban import storage` in __init__.py must NOT "
            "be flagged as a violation.  The durable helper's skip-list must include "
            "both 'engine.py' and '__init__.py'; removing __init__.py from the skip-list "
            "violates the arch v4 decision.\n"
            f"Current violations returned: {violations}"
        )

    def test_durable_suite_detects_direct_static_storage_import(self, tmp_path: Path) -> None:
        from tests.test_package_boundary import _find_kanban_storage_import_violations

        kanban_src = tmp_path / "serve" / "kanban" / "src" / "owlbear_kanban"
        kanban_src.mkdir(parents=True)
        (kanban_src / "engine.py").write_text("", encoding="utf-8")
        (kanban_src / "bad.py").write_text("from owlbear_kanban.storage import read_task\n", encoding="utf-8")
        violations = _find_kanban_storage_import_violations(tmp_path)
        assert violations, (
            "Durable helper must detect direct 'from owlbear_kanban.storage import X' in non-engine source files"
        )
        assert any("bad.py" in violation for violation in violations)

    def test_durable_suite_detects_bare_import_storage(self, tmp_path: Path) -> None:
        from tests.test_package_boundary import _find_kanban_storage_import_violations

        kanban_src = tmp_path / "serve" / "kanban" / "src" / "owlbear_kanban"
        kanban_src.mkdir(parents=True)
        (kanban_src / "engine.py").write_text("", encoding="utf-8")
        (kanban_src / "bad.py").write_text("import owlbear_kanban.storage\n", encoding="utf-8")
        violations = _find_kanban_storage_import_violations(tmp_path)
        assert violations, "Durable helper must detect bare 'import owlbear_kanban.storage'"
        assert any("bad.py" in violation for violation in violations)


class TestFromAC_TaskIoGlobalRemoval:
    """4th AC: no import of removed ``task_io`` module anywhere in the codebase."""

    def test_no_task_io_reference_in_kanban_test_suite(self) -> None:
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

    def test_no_task_io_reference_anywhere_in_codebase(self, project_root: Path) -> None:
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


class TestFromAC_StorageTestIsolation:
    """AC-C46: ``tests/test_deny_code_writes.py`` must exist."""

    def test_deny_code_writes_test_file_exists(self, project_root: Path) -> None:
        deny_file = project_root / "tests" / "test_deny_code_writes.py"
        assert deny_file.exists(), (
            "tests/test_deny_code_writes.py does not exist; "
            "create it with enforcement tests that verify storage test files "
            "(serve/kanban/tests/test_storage*.py, test_activity_store*.py, "
            "test_corruption*.py) are isolated to tmp_path (AC-C46)"
        )


class TestFromAC_NewModuleLayout:
    """3rd AC: boundary enforcement for the new layout is permanent, not just task-scoped."""

    def test_durable_boundary_suite_includes_intra_kanban_storage_check(self, project_root: Path) -> None:
        boundary_file = project_root / "tests" / "test_package_boundary.py"
        content = boundary_file.read_text(encoding="utf-8")
        assert "engine.py" in content, (
            "tests/test_package_boundary.py must reference 'engine.py' as part of a "
            "permanent intra-kanban storage boundary test.  Currently this enforcement "
            "exists only in the task-scoped test_package_boundary_1064.py.  Add a "
            "TestFromAC_KanbanInternalBoundary (or equivalent) class to the durable suite "
            "so the AC-C45 constraint survives post-archive cleanup."
        )


class TestFromAC_KanbanTaskIoRemoval1064:
    """AC-C45b refinements promoted from task #1064."""

    def test_durable_suite_task_io_helper_detects_static_import(self, tmp_path: Path) -> None:
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
        from tests.test_package_boundary import _find_task_io_import_violations

        kanban_src = tmp_path / "serve" / "kanban" / "src" / "owlbear_kanban"
        kanban_src.mkdir(parents=True)
        (kanban_src / "__init__.py").write_text("from owlbear_kanban.task_io import write_task\n", encoding="utf-8")
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
        from tests.test_package_boundary import _find_task_io_import_violations

        kanban_src = tmp_path / "serve" / "kanban" / "src" / "owlbear_kanban"
        kanban_src.mkdir(parents=True)
        (kanban_src / "dispatch.py").write_text(
            'import importlib\nimportlib.import_module("owlbear_kanban.task_io")\n',
            encoding="utf-8",
        )
        violations = _find_task_io_import_violations(tmp_path)
        assert violations, (
            "Durable helper must detect importlib.import_module('owlbear_kanban.task_io') in source files"
        )
        assert any("dispatch.py" in violation for violation in violations)

    def test_durable_suite_detects_bare_import_task_io(self, tmp_path: Path) -> None:
        from tests.test_package_boundary import _find_task_io_import_violations

        kanban_src = tmp_path / "serve" / "kanban" / "src" / "owlbear_kanban"
        kanban_src.mkdir(parents=True)
        (kanban_src / "bad.py").write_text("import owlbear_kanban.task_io\n", encoding="utf-8")
        violations = _find_task_io_import_violations(tmp_path)
        assert violations, "Durable helper must detect bare 'import owlbear_kanban.task_io'"
        assert any("bad.py" in violation for violation in violations)

    def test_durable_suite_detects_dunder_import_task_io(self, tmp_path: Path) -> None:
        from tests.test_package_boundary import _find_task_io_import_violations

        kanban_src = tmp_path / "serve" / "kanban" / "src" / "owlbear_kanban"
        kanban_src.mkdir(parents=True)
        (kanban_src / "bad.py").write_text('__import__("owlbear_kanban.task_io")\n', encoding="utf-8")
        violations = _find_task_io_import_violations(tmp_path)
        assert violations, "Durable helper must detect __import__('owlbear_kanban.task_io') in source files"
        assert any("bad.py" in violation for violation in violations)

    def test_durable_suite_detects_alias_form_task_io_import(self, tmp_path: Path) -> None:
        from tests.test_package_boundary import _find_task_io_import_violations

        kanban_src = tmp_path / "serve" / "kanban" / "src" / "owlbear_kanban"
        kanban_src.mkdir(parents=True)
        (kanban_src / "bad.py").write_text("from owlbear_kanban import task_io\n", encoding="utf-8")
        violations = _find_task_io_import_violations(tmp_path)
        assert violations, "Durable helper must detect 'from owlbear_kanban import task_io'"
        assert any("bad.py" in violation for violation in violations)
