"""RED-phase tests for tools.py cleanup in mcp-knowledge (#223).

Tests the contract for:
- AC1: owlbear_mcp_knowledge/tools.py is deleted (module not importable)
- AC3: No imports of owlbear_mcp_knowledge.tools remain anywhere in the codebase

AC2 (test_search_knowledge.py deleted) and AC4 (tests pass) are already satisfied
in the current working tree — tests for them pass trivially and are omitted per
TDD RED-phase convention (no passing tests).

Inline imports use noqa: PLC0415 where needed so collection succeeds even if
the module under test no longer exists.
"""

from __future__ import annotations

import re
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).parent.parent
SKIP_DIRS = {".venv", "__pycache__", ".git", "node_modules", "docs/scratch"}


def _all_project_py_files() -> list[Path]:
    """Yield all .py files under WORKSPACE_ROOT excluding generated/scratch dirs."""
    result: list[Path] = []
    for py_file in WORKSPACE_ROOT.rglob("*.py"):
        parts = set(py_file.relative_to(WORKSPACE_ROOT).parts)
        if parts & SKIP_DIRS:
            continue
        result.append(py_file)
    return result


class TestFromAC_ToolsCleanup:
    """Cleanup of superseded tools.py and test_search_knowledge.py (#223)."""

    # ------------------------------------------------------------------
    # AC1 — owlbear_mcp_knowledge/tools.py deleted
    # ------------------------------------------------------------------

    def test_tools_py_source_file_absent(self) -> None:
        """AC1: The source file packages/mcp-knowledge/src/owlbear_mcp_knowledge/tools.py must not exist."""
        tools_path = (
            WORKSPACE_ROOT
            / "serve"
            / "mcp-knowledge"
            / "src"
            / "owlbear_mcp_knowledge"
            / "tools.py"
        )
        assert not tools_path.exists(), (
            f"AC1 FAIL — tools.py still exists at {tools_path}"
        )

    def test_tools_module_not_importable(self) -> None:
        """AC1: owlbear_mcp_knowledge.tools must raise ImportError when imported."""
        import importlib  # noqa: PLC0415
        import sys  # noqa: PLC0415

        # Remove cached entry if present so we get a fresh import attempt.
        sys.modules.pop("owlbear_mcp_knowledge.tools", None)
        try:
            importlib.import_module("owlbear_mcp_knowledge.tools")
        except ImportError:
            pass  # Expected — tools.py is deleted
        else:
            msg = (
                "AC1 FAIL — owlbear_mcp_knowledge.tools imported successfully; "
                "tools.py must be deleted"
            )
            raise AssertionError(msg)

    # ------------------------------------------------------------------
    # AC3 — No imports of owlbear_mcp_knowledge.tools remain in the codebase
    # ------------------------------------------------------------------

    def test_no_codebase_imports_of_tools_module(self) -> None:
        """AC3: No Python file in the project may import from owlbear_mcp_knowledge.tools."""
        # Match both:
        #   from owlbear_mcp_knowledge.tools import ...
        #   import owlbear_mcp_knowledge.tools
        #   from owlbear_mcp_knowledge import tools ...
        pattern = re.compile(
            r"(?:from\s+owlbear_mcp_knowledge\.tools\b"
            r"|import\s+owlbear_mcp_knowledge\.tools\b"
            r"|from\s+owlbear_mcp_knowledge\s+import\s+tools\b)"
        )

        this_file = Path(__file__)
        violations: list[str] = []
        for py_file in _all_project_py_files():
            if py_file == this_file:
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for lineno, line in enumerate(content.splitlines(), 1):
                if pattern.search(line):
                    rel = py_file.relative_to(WORKSPACE_ROOT)
                    violations.append(f"{rel}:{lineno}: {line.strip()}")

        assert not violations, (
            "AC3 FAIL — imports of owlbear_mcp_knowledge.tools found "
            f"({len(violations)} occurrence(s)):\n" + "\n".join(violations)
        )


