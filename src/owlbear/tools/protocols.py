"""Protocols for toolset capabilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path


@runtime_checkable
class WorkspaceAware(Protocol):
    """Toolset that can update its workspace root."""

    def update_workspace(self, workspace: Path) -> None:
        """Set the workspace root to *workspace*."""
        ...
