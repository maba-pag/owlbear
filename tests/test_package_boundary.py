"""
AST-based package boundary enforcement test.

Scans all Python files under packages/*/src/ and fails if any package
imports a peer owlbear namespace it is not permitted to depend on.

Dependency rules
----------------
owlbear_knowledge     no owlbear-namespace deps (foundation layer)
owlbear_mcp_kanban    no owlbear-namespace deps (standalone MCP server)
owlbear_mcp_knowledge may import owlbear_knowledge only
owlbear               may import owlbear_orchestrator only (co-shipped wheel)
owlbear_orchestrator  may import owlbear only (co-shipped wheel)
owlbear_voice         no owlbear-namespace deps (standalone addon)

Self-import policy
------------------
A namespace importing from itself (e.g. owlbear_knowledge.models inside
owlbear_knowledge) is always allowed and excluded from boundary checks.

TYPE_CHECKING import policy
---------------------------
Imports inside ``if TYPE_CHECKING:`` blocks are parsed by ast.walk and are
subject to the same boundary rules as runtime imports. This is intentional:
TYPE_CHECKING imports create a real dependency chain reflected in wheels and
type checking tools even though they are not evaluated at runtime.
"""

from __future__ import annotations

import ast
from pathlib import Path

# serve/ directory relative to this test file (tests/test_package_boundary.py)
_PACKAGES_DIR = Path(__file__).parent.parent / "serve"

# Allowed cross-namespace imports per owlbear package namespace.
# Self-imports (a namespace importing from itself) are always allowed and are
# excluded from the check before consulting this map.
ALLOWED_IMPORTS = {
    "owlbear_knowledge": set(),
    "owlbear_mcp_kanban": set(),
    "owlbear_mcp_knowledge": {"owlbear_knowledge"},
    "owlbear_mcp_memory": set(),
    "owlbear": {"owlbear_orchestrator"},
    "owlbear_orchestrator": {"owlbear"},
    "owlbear_voice": set(),
    "owlbear_browser": set(),
    "owlbear_mcp_browser": {"owlbear_browser"},
}

# Derived set of all known owlbear namespaces (for import filtering).
_OWLBEAR_NAMESPACES: frozenset[str] = frozenset(ALLOWED_IMPORTS)


def _discover_namespaces() -> dict[str, Path]:
    """Return mapping of namespace name -> directory from packages/*/src/."""
    namespaces: dict[str, Path] = {}
    for src_dir in _PACKAGES_DIR.glob("*/src"):
        for ns_dir in src_dir.iterdir():
            if ns_dir.is_dir() and not ns_dir.name.startswith("_"):
                namespaces[ns_dir.name] = ns_dir
    return namespaces


def _owlbear_import_roots(py_file: Path) -> list[str]:
    """Return owlbear-namespace root modules imported in *py_file*.

    Uses ast.parse + ast.walk to collect all Import and ImportFrom nodes.
    Extracts the first dot-separated component of each import path and returns
    only those that are an exact match against an ALLOWED_IMPORTS key (i.e. a
    known owlbear peer namespace).  No prefix matching is performed.
    """
    source = py_file.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(py_file))
    roots: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _OWLBEAR_NAMESPACES:
                    roots.append(root)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            root = node.module.split(".")[0]
            if root in _OWLBEAR_NAMESPACES:
                roots.append(root)
    return roots


# ===========================================================================
# Manifest guard — ALLOWED_IMPORTS keys must exactly equal discovered namespaces
# ===========================================================================


class TestFromAC_ManifestGuard:
    """Bidirectional check: ALLOWED_IMPORTS must stay in sync with packages/*/src/."""

    def test_allowed_imports_keys_match_discovered_namespaces(self) -> None:
        """ALLOWED_IMPORTS keys exactly equal namespace dirs found under packages/*/src/.

        Fails when a package is added without updating ALLOWED_IMPORTS, or when
        a package is removed but its entry is left in ALLOWED_IMPORTS.
        """
        discovered = set(_discover_namespaces())
        defined = set(ALLOWED_IMPORTS)

        missing_from_map = discovered - defined
        extra_in_map = defined - discovered
        errors: list[str] = []
        if missing_from_map:
            errors.append(
                f"Namespaces discovered under packages/*/src/ but missing from "
                f"ALLOWED_IMPORTS: {sorted(missing_from_map)}"
            )
        if extra_in_map:
            errors.append(
                f"ALLOWED_IMPORTS contains unknown namespaces not found under packages/*/src/: {sorted(extra_in_map)}"
            )
        assert not errors, "\n".join(errors)


# ===========================================================================
# Boundary check — no illegal cross-package imports in the current codebase
# ===========================================================================


class TestFromAC_PackageBoundaries:
    """No source file under packages/*/src/ imports a disallowed peer namespace."""

    def test_no_illegal_cross_package_imports(self) -> None:
        """Every .py file under packages/*/src/ respects its allowed import set.

        A violation is reported as: '<file>: <namespace> imports disallowed
        namespace <peer>'.  Self-imports (namespace importing from itself) are
        excluded and never counted as violations.
        """
        namespaces = _discover_namespaces()
        violations: list[str] = []

        for ns_name, ns_dir in sorted(namespaces.items()):
            allowed = ALLOWED_IMPORTS.get(ns_name, set())
            for py_file in sorted(ns_dir.rglob("*.py")):
                for root in _owlbear_import_roots(py_file):
                    if root == ns_name:
                        continue  # self-import — always allowed
                    if root not in allowed:
                        rel = py_file.relative_to(_PACKAGES_DIR)
                        violations.append(f"{rel}: {ns_name!r} imports disallowed namespace {root!r}")

        assert not violations, f"Package boundary violations found ({len(violations)}):\n" + "\n".join(violations)
