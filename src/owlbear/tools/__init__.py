"""Tool abstractions and registry.

All imports are lazy to avoid eager loading of heavy submodules (e.g.
owlbear.tools.github_api pulls owlbear.core.retry) on bare package import.
"""

from __future__ import annotations

import importlib

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

# Lazy import map: attribute name → (relative submodule, attribute name).
# Covers only the 10 public symbols declared in __all__.
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "AskUserToolset": (".ask_user", "AskUserToolset"),
    "FileToolset": (".filesystem", "FileToolset"),
    "GitHubToolset": (".github_api", "GitHubToolset"),
    "GitLocalToolset": (".git_local", "GitLocalToolset"),
    "HookedToolset": (".hooked", "HookedToolset"),
    "KanbanToolset": (".kanban", "KanbanToolset"),
    "MCPServerRegistry": (".mcp_registry", "MCPServerRegistry"),
    "TerminalToolset": (".terminal", "TerminalToolset"),
    "find_toolset": (".protocols", "find_toolset"),
    "unwrap": (".protocols", "unwrap"),
}


def __getattr__(name: str) -> object:
    if name in _LAZY_IMPORTS:
        submodule, attr = _LAZY_IMPORTS[name]
        mod = importlib.import_module(submodule, __name__)
        val = getattr(mod, attr)
        globals()[name] = val  # cache for subsequent access
        return val
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
