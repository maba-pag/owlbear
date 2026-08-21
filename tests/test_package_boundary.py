"""Enforce the permitted cross-package import direction for ``serve/``."""

from __future__ import annotations

import ast
from pathlib import Path

ALLOWED_IMPORTS: dict[str, frozenset[str]] = {
    "owlbear_browser": frozenset(),
    "owlbear_browser_mcp": frozenset({"owlbear_browser"}),
    "owlbear_cockpit": frozenset({"owlbear_delivery", "owlbear_delivery_github", "owlbear_memory"}),
    "owlbear_delivery": frozenset(),
    "owlbear_delivery_github": frozenset({"owlbear_delivery"}),
    "owlbear_delivery_mcp": frozenset({"owlbear_delivery", "owlbear_delivery_github"}),
    "owlbear_knowledge": frozenset(),
    "owlbear_knowledge_mcp": frozenset({"owlbear_knowledge"}),
    "owlbear_memory": frozenset(),
    "owlbear_memory_mcp": frozenset({"owlbear_memory"}),
    "owlbear_tools": frozenset({"owlbear_delivery"}),
    "owlbear_web_content": frozenset(),
}


def _package_sources(project_root: Path) -> dict[str, Path]:
    sources: dict[str, Path] = {}
    for src_root in sorted((project_root / "serve").glob("*/src")):
        for package_root in sorted(src_root.glob("owlbear_*")):
            if package_root.is_dir():
                sources[package_root.name] = package_root
    return sources


def _imported_namespaces(source_file: Path) -> tuple[str, ...]:
    tree = ast.parse(source_file.read_text(encoding="utf-8"))
    namespaces: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module is not None:
            modules = (node.module,)
        else:
            continue
        namespaces.update(module.split(".", 1)[0] for module in modules if module.startswith("owlbear_"))
    return tuple(sorted(namespaces))


def test_allowlist_covers_current_serve_packages(project_root: Path) -> None:
    """Every discovered package must have an explicit boundary entry, and vice versa."""
    assert set(_package_sources(project_root)) == set(ALLOWED_IMPORTS)


def test_serve_package_imports_follow_allowlist(project_root: Path) -> None:
    """Runtime and TYPE_CHECKING imports must follow the declared package direction."""
    violations: list[tuple[str, str, str]] = []
    for package_name, source_root in _package_sources(project_root).items():
        allowed = ALLOWED_IMPORTS[package_name]
        for source_file in sorted(source_root.rglob("*.py")):
            violations.extend(
                (
                    str(source_file.relative_to(project_root)),
                    package_name,
                    imported_namespace,
                )
                for imported_namespace in _imported_namespaces(source_file)
                if imported_namespace != package_name and imported_namespace not in allowed
            )
    assert violations == []
