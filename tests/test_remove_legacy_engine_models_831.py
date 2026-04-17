"""RED tests — Remove legacy engine_models.py from mcp-kanban (task #831).

AC coverage:
  AC1 - engine_models.py must NOT exist at serve/mcp-kanban/src/owlbear_mcp_kanban/engine_models.py
  AC2 - No Python file in the workspace imports from owlbear_mcp_kanban.engine_models

All tests FAIL in RED phase: file still exists and 3 test files still import from it.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_MCP_KANBAN_SRC = _REPO_ROOT / "serve" / "mcp-kanban" / "src" / "owlbear_mcp_kanban"
_THIS_FILE = Path(__file__).resolve()

_LEGACY_MODULE = "owlbear_mcp_kanban.engine_models"

# Directories excluded from the import scan (virtual envs, caches, build artifacts)
_SCAN_EXCLUDE_DIRS = frozenset(
    {
        ".venv",
        "venv",
        "__pycache__",
        ".git",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
        "dist",
        "build",
        "site-packages",
    }
)


def _workspace_py_files() -> list[Path]:
    """Return .py files under repo root, skipping excluded directories."""
    results: list[Path] = []

    def _walk(directory: Path) -> None:
        try:
            entries = list(directory.iterdir())
        except PermissionError:
            return
        for entry in entries:
            if entry.is_dir() and not entry.is_symlink():
                if entry.name not in _SCAN_EXCLUDE_DIRS:
                    _walk(entry)
            elif entry.suffix == ".py":
                results.append(entry)

    _walk(_REPO_ROOT)
    return sorted(results)


class TestFromAC_RemoveLegacyEngineModels:
    """AC1 + AC2: engine_models.py deleted and all workspace imports cleaned up."""

    def test_engine_models_py_does_not_exist(self) -> None:
        """engine_models.py must NOT exist at serve/mcp-kanban/src/owlbear_mcp_kanban/engine_models.py."""
        legacy = _MCP_KANBAN_SRC / "engine_models.py"
        assert not legacy.exists(), (
            f"engine_models.py still present at {legacy} — "
            "must be deleted (canonical models are in owlbear_kanban.models)"
        )

    def test_no_workspace_imports_from_engine_models(self) -> None:
        """No .py file in the workspace may import from owlbear_mcp_kanban.engine_models."""
        offenders: list[str] = []

        for py_file in _workspace_py_files():
            # Exclude this test file — it references the module name as a string literal, not an import
            if py_file.resolve() == _THIS_FILE:
                continue

            try:
                source = py_file.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source, filename=str(py_file))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if module == _LEGACY_MODULE or module.startswith(_LEGACY_MODULE + "."):
                        rel = py_file.relative_to(_REPO_ROOT)
                        offenders.append(f"{rel}:{node.lineno}")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == _LEGACY_MODULE or alias.name.startswith(_LEGACY_MODULE + "."):
                            rel = py_file.relative_to(_REPO_ROOT)
                            offenders.append(f"{rel}:{node.lineno}")

        assert not offenders, f"These files still import from '{_LEGACY_MODULE}' and must be updated:\n" + "\n".join(
            f"  {o}" for o in offenders
        )
