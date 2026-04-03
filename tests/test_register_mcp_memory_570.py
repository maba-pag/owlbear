"""Tests for task #570: Register owlbear-memory server in .vscode/mcp.json.

AC coverage:
  - AC1: workspace .vscode/mcp.json includes owlbear-memory entry
         (stdio, command=uv, args=[run, python, -m, owlbear_mcp_memory], no --project flag)
  - AC4: owlbear-kanban key in workspace mcp.json matches owlbear-kanban/* tool pattern prefix
"""

from __future__ import annotations

import json
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_WORKSPACE_MCP_JSON = _REPO_ROOT / ".vscode" / "mcp.json"


def _load_workspace_mcp() -> dict:
    assert _WORKSPACE_MCP_JSON.is_file(), (
        f"Workspace .vscode/mcp.json not found at {_WORKSPACE_MCP_JSON}"
    )
    return json.loads(_WORKSPACE_MCP_JSON.read_text(encoding="utf-8"))


class TestFromAC_WorkspaceMcpMemoryEntry:
    """AC1: workspace .vscode/mcp.json must include owlbear-memory server entry."""

    def test_workspace_mcp_json_has_owlbear_memory_entry(self) -> None:
        """AC1: owlbear-memory must be a key in workspace mcp.json servers."""
        data = _load_workspace_mcp()
        assert "owlbear-memory" in data.get("servers", {}), (
            f"'owlbear-memory' entry missing from workspace .vscode/mcp.json. "
            f"Found servers: {list(data.get('servers', {}).keys())}"
        )

    def test_workspace_mcp_memory_entry_type_is_stdio(self) -> None:
        """AC1: owlbear-memory entry must have type: stdio."""
        data = _load_workspace_mcp()
        entry = data.get("servers", {}).get("owlbear-memory", {})
        assert entry.get("type") == "stdio", (
            f"owlbear-memory.type must be 'stdio', got: {entry.get('type')!r}"
        )

    def test_workspace_mcp_memory_entry_command_is_uv(self) -> None:
        """AC1: owlbear-memory entry must use command: uv."""
        data = _load_workspace_mcp()
        entry = data.get("servers", {}).get("owlbear-memory", {})
        assert entry.get("command") == "uv", (
            f"owlbear-memory.command must be 'uv', got: {entry.get('command')!r}"
        )

    def test_workspace_mcp_memory_entry_args_contain_module(self) -> None:
        """AC1: owlbear-memory args must contain 'run', 'python', '-m', 'owlbear_mcp_memory'."""
        data = _load_workspace_mcp()
        entry = data.get("servers", {}).get("owlbear-memory", {})
        args = entry.get("args", [])
        assert "run" in args, f"owlbear-memory args missing 'run': {args}"
        assert "python" in args, f"owlbear-memory args missing 'python': {args}"
        assert "-m" in args, f"owlbear-memory args missing '-m': {args}"
        assert "owlbear_mcp_memory" in args, f"owlbear-memory args missing 'owlbear_mcp_memory': {args}"

    def test_workspace_mcp_memory_entry_has_no_project_flag(self) -> None:
        """AC1: owlbear-memory must not use --project flag (matching existing workspace entries)."""
        data = _load_workspace_mcp()
        servers = data.get("servers", {})
        assert "owlbear-memory" in servers, (
            "owlbear-memory entry missing — cannot verify --project flag absence"
        )
        args = servers["owlbear-memory"].get("args", [])
        assert "--project" not in args, (
            f"owlbear-memory must not use --project flag in args, got: {args}"
        )


class TestFromAC_WorkspaceMcpToolPatterns:
    """AC4: workspace mcp.json key names must match agent tool pattern prefixes."""

    def test_workspace_mcp_memory_key_matches_memory_tool_pattern_prefix(self) -> None:
        """AC4: owlbear-memory key must exist so future owlbear-memory/* tool patterns resolve."""
        data = _load_workspace_mcp()
        servers = data.get("servers", {})
        assert "owlbear-memory" in servers, (
            f"'owlbear-memory' key missing from workspace mcp.json — "
            f"tool patterns 'owlbear-memory/*' require this exact kebab-case key. "
            f"Found: {list(servers.keys())}"
        )
