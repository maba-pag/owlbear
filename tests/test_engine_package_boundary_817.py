"""RED tests — Engine package boundary + public API (task #817).

Verifies the target state of Phase 2 extraction:
- owlbear_kanban is importable with KanbanEngine, Task, TaskSummary
- Engine package does NOT import mcp or transport packages
- Engine public API surface is complete (14 methods/properties + 3 model exports)
- MCP adapter (server.py) imports owlbear_kanban

All tests FAIL in the RED phase before serve/kanban/ is extracted.
"""

from __future__ import annotations

import ast
from pathlib import Path

_SERVE_DIR = Path(__file__).parent.parent / "serve"
_KANBAN_ENGINE_DIR = _SERVE_DIR / "kanban"
_MCP_KANBAN_SERVER = _SERVE_DIR / "mcp-kanban" / "src" / "owlbear_mcp_kanban" / "server.py"

_TRANSPORT_BLOCKLIST: frozenset[str] = frozenset({"mcp", "fastmcp"})

_ENGINE_PUBLIC_API: frozenset[str] = frozenset(
    {
        "list_tasks",
        "show_task",
        "create_task",
        "edit_task",
        "move_task",
        "claim_task",
        "release_task",
        "start_work",
        "end_work",
        "agent_name",
        "board_config",
        "refresh_config",
        "valid_transitions",
        "revision",
    }
)


class TestFromAC_EngineImportable:
    """AC1: from owlbear_kanban import KanbanEngine, Task, TaskSummary works."""

    def test_import_core_exports(self) -> None:
        """KanbanEngine, Task, TaskSummary are importable from owlbear_kanban."""
        from owlbear_kanban import KanbanEngine, Task, TaskSummary  # noqa: F401


class TestFromAC_EngineBoundary:
    """AC2: Engine package does NOT import mcp or any transport package."""

    def test_engine_dir_exists(self) -> None:
        """serve/kanban/ directory exists — engine package has been extracted."""
        assert _KANBAN_ENGINE_DIR.exists(), (
            f"serve/kanban/ not found at {_KANBAN_ENGINE_DIR} — package not yet extracted"
        )

    def test_no_mcp_transport_imports(self) -> None:
        """No file under serve/kanban/src/ imports mcp or fastmcp."""
        assert _KANBAN_ENGINE_DIR.exists(), (
            f"serve/kanban/ not found at {_KANBAN_ENGINE_DIR} — package not yet extracted"
        )
        src_dir = _KANBAN_ENGINE_DIR / "src"
        assert src_dir.exists(), f"serve/kanban/src/ not found at {src_dir}"

        violations: list[str] = []
        for py_file in src_dir.rglob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root = alias.name.split(".")[0]
                        if root in _TRANSPORT_BLOCKLIST:
                            violations.append(f"{py_file.name}: imports {root!r}")
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    root = node.module.split(".")[0]
                    if root in _TRANSPORT_BLOCKLIST:
                        violations.append(f"{py_file.name}: imports from {root!r}")

        assert not violations, "Engine package must not import transport packages:\n" + "\n".join(violations)


class TestFromAC_EnginePublicAPI:
    """AC3: Engine public API — KanbanEngine methods, Task, TaskSummary, BoardConfig exports."""

    def test_engine_methods(self) -> None:
        """KanbanEngine exposes all 14 required public methods and properties."""
        from owlbear_kanban import KanbanEngine

        missing = [m for m in _ENGINE_PUBLIC_API if not hasattr(KanbanEngine, m)]
        assert not missing, f"KanbanEngine missing API members: {sorted(missing)}"

    def test_task_exported(self) -> None:
        """Task model is exported from owlbear_kanban."""
        from owlbear_kanban import Task  # noqa: F401

    def test_tasksummary_exported(self) -> None:
        """TaskSummary model is exported from owlbear_kanban."""
        from owlbear_kanban import TaskSummary  # noqa: F401

    def test_boardconfig_exported(self) -> None:
        """BoardConfig model is exported from owlbear_kanban."""
        from owlbear_kanban import BoardConfig  # noqa: F401


class TestFromAC_AdapterImportsEngine:
    """AC4: MCP adapter (owlbear_mcp_kanban) is allowed to import owlbear_kanban."""

    def test_adapter_imports_engine(self) -> None:
        """server.py imports from owlbear_kanban — adapter wraps extracted engine."""
        assert _MCP_KANBAN_SERVER.exists(), f"server.py not found at {_MCP_KANBAN_SERVER}"
        source = _MCP_KANBAN_SERVER.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(_MCP_KANBAN_SERVER))

        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] == "owlbear_kanban":
                        found = True
                        break
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.level == 0
                and node.module.split(".")[0] == "owlbear_kanban"
            ):
                found = True
                break
            if found:
                break

        assert found, (
            "server.py does not import from owlbear_kanban — MCP adapter must depend on engine package after extraction"
        )
