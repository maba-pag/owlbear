"""Tool abstractions and registry."""

from __future__ import annotations

from owlbear.tools.ask_user import AskUserToolset
from owlbear.tools.filesystem import FileToolset
from owlbear.tools.git_local import GitLocalToolset
from owlbear.tools.github_api import GitHubToolset
from owlbear.tools.hooked import HookedToolset
from owlbear.tools.kanban import KanbanToolset
from owlbear.tools.mcp_registry import MCPServerRegistry
from owlbear.tools.protocols import find_toolset, unwrap
from owlbear.tools.terminal import TerminalToolset

__all__ = (
    "AskUserToolset",
    "FileToolset",
    "GitHubToolset",
    "GitLocalToolset",
    "HookedToolset",
    "KanbanToolset",
    "MCPServerRegistry",
    "TerminalToolset",
    "find_toolset",
    "unwrap",
)
