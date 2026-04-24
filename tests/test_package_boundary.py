"""Cross-package import boundary tests for serve/ packages (#1038).

Verifies that no owlbear_* package imports from another owlbear_*
package unless explicitly declared in ALLOWED_IMPORTS.

Policy: All imports are scanned, including those inside
``if TYPE_CHECKING:`` blocks. Runtime-vs-typecheck distinction is
irrelevant for boundary enforcement — a TYPE_CHECKING import still
creates a coupling contract.

Ground truth for ALLOWED_IMPORTS: ``serve/*/pyproject.toml`` workspace
dependencies and the co-packaging layout of ``serve/orchestrator/``
(``owlbear`` + ``owlbear_orchestrator`` ship in the same wheel).
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
    "owlbear_cockpit": {"owlbear_kanban"},
    "owlbear_kanban": set(),
    "owlbear_knowledge": set(),
    "owlbear_mcp_browser": {"owlbear_browser"},
    "owlbear_mcp_kanban": {"owlbear_kanban"},
    "owlbear_mcp_knowledge": {"owlbear_knowledge"},
    "owlbear_mcp_memory": set(),
    "owlbear": {"owlbear_orchestrator"},  # co-packaged in orchestrator wheel
    "owlbear_orchestrator": {"owlbear"},  # co-packaged in orchestrator wheel
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
            assert isinstance(allowed, set), (
                f"ALLOWED_IMPORTS[{ns!r}]: expected set, got {type(allowed).__name__}"
            )

    def test_allowed_imports_covers_all_discovered_namespaces(
        self, project_root: Path
    ) -> None:
        """AC#2, AC#4: every namespace under serve/*/src/ appears in ALLOWED_IMPORTS."""
        serve_root = project_root / "serve"
        discovered = _discover_namespaces(serve_root)
        missing = discovered - set(ALLOWED_IMPORTS)
        assert not missing, (
            f"Namespaces found in serve/ but missing from ALLOWED_IMPORTS: {sorted(missing)}"
        )

    def test_allowed_imports_has_no_unknown_keys(self, project_root: Path) -> None:
        """AC#4: ALLOWED_IMPORTS has no keys for namespaces that don't exist on disk."""
        serve_root = project_root / "serve"
        discovered = _discover_namespaces(serve_root)
        extra = set(ALLOWED_IMPORTS) - discovered
        assert not extra, (
            f"ALLOWED_IMPORTS has keys for non-existent namespaces: {sorted(extra)}"
        )


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
                f"  {ns}/{relfile}:{lineno} — imports {imported!r}"
                f" (not in ALLOWED_IMPORTS[{ns!r}])"
                for ns, relfile, imported, lineno in violations
            ]
            pytest.fail(
                "Undeclared cross-namespace imports found:\n" + "\n".join(lines)
            )

    def test_scan_detects_synthetic_from_import_violation(self, tmp_path: Path) -> None:
        """AC#3: scanner catches a synthetic 'from X import Y' boundary violation."""
        fake_src = tmp_path / "fake_pkg" / "src" / "owlbear_tools"
        fake_src.mkdir(parents=True)
        (fake_src / "bad.py").write_text(
            "from owlbear_kanban import KanbanEngine\n", encoding="utf-8"
        )
        violations = _collect_violations(tmp_path)
        assert len(violations) >= 1
        assert any(
            ns == "owlbear_tools" and imported == "owlbear_kanban"
            for ns, _relfile, imported, _lineno in violations
        )

    def test_scan_detects_synthetic_bare_import_violation(self, tmp_path: Path) -> None:
        """AC#3: scanner catches a synthetic bare 'import X' boundary violation."""
        fake_src = tmp_path / "fake_pkg" / "src" / "owlbear_tools"
        fake_src.mkdir(parents=True)
        (fake_src / "bad.py").write_text("import owlbear_kanban\n", encoding="utf-8")
        violations = _collect_violations(tmp_path)
        assert len(violations) >= 1
        assert any(
            ns == "owlbear_tools" and imported == "owlbear_kanban"
            for ns, _relfile, imported, _lineno in violations
        )

    def test_scan_ignores_intra_namespace_imports(self, tmp_path: Path) -> None:
        """AC#3: intra-package self-imports are not reported as violations."""
        fake_src = tmp_path / "fake_pkg" / "src" / "owlbear_kanban"
        fake_src.mkdir(parents=True)
        (fake_src / "internal.py").write_text(
            "from owlbear_kanban.engine import KanbanEngine\n", encoding="utf-8"
        )
        violations = _collect_violations(tmp_path)
        assert not violations

    def test_scan_allows_declared_cross_namespace_imports(self, tmp_path: Path) -> None:
        """AC#3: imports that appear in ALLOWED_IMPORTS are not violations."""
        fake_src = tmp_path / "fake_pkg" / "src" / "owlbear_cockpit"
        fake_src.mkdir(parents=True)
        (fake_src / "deps.py").write_text(
            "from owlbear_kanban import KanbanEngine\n", encoding="utf-8"
        )
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
            ns == "owlbear_tools" and imported == "owlbear_kanban"
            for ns, _relfile, imported, _lineno in violations
        )
