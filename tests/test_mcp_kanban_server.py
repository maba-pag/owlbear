"""Infrastructure tests for mcp-kanban server (task #14).

AC items:
  - pyproject.toml declares mcp[cli]>=1.26 dependency
  - __main__.py entry point exists (python -m owlbear_mcp_kanban)
  - server module exposes a named FastMCP instance (confirming stdio transport)
"""

from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path

try:
    from owlbear_mcp_kanban import server as _server_module  # type: ignore[import]
except ImportError:
    _server_module = None  # type: ignore[assignment]


_MCP_KANBAN_PYPROJECT = Path(__file__).parent.parent / "packages" / "mcp-kanban" / "pyproject.toml"


class TestFromAC_McpKanbanServer:
    """Infrastructure contract tests for task #14 AC items."""

    # AC: MCP server in packages/mcp-kanban/ using Python MCP SDK
    # — pyproject.toml must declare mcp[cli]>=1.26
    def test_pyproject_declares_mcp_dependency(self) -> None:
        """packages/mcp-kanban/pyproject.toml must list mcp[cli]>=1.26 in [project.dependencies]."""
        with _MCP_KANBAN_PYPROJECT.open("rb") as f:
            data = tomllib.load(f)
        deps: list[str] = data.get("project", {}).get("dependencies", [])
        assert any("mcp" in dep for dep in deps), (
            "packages/mcp-kanban/pyproject.toml is missing the mcp[cli]>=1.26 dependency; "
            "add it under [project.dependencies]"
        )

    # AC: python -m owlbear_mcp_kanban entry point
    # — __main__.py must exist in the package
    def test_main_module_exists(self) -> None:
        """owlbear_mcp_kanban.__main__ must exist for `python -m owlbear_mcp_kanban`."""
        spec = importlib.util.find_spec("owlbear_mcp_kanban.__main__")
        assert spec is not None, (
            "owlbear_mcp_kanban.__main__ not found; "
            "create packages/mcp-kanban/src/owlbear_mcp_kanban/__main__.py "
            "that calls mcp.run()"
        )

    # AC: Server communicates via stdio transport
    # — FastMCP instance named 'mcp' must be present at module level;
    #   FastMCP.run() defaults to stdio transport when no transport is specified.
    def test_server_exposes_mcp_instance(self) -> None:
        """server module must expose a module-level FastMCP instance named 'mcp'."""
        assert _server_module is not None, (
            "owlbear_mcp_kanban.server is not importable; builder must create server.py"
        )
        assert hasattr(_server_module, "mcp"), (
            "server module must expose a module-level attribute 'mcp' (FastMCP instance); "
            "this is required for stdio transport via __main__.py"
        )
