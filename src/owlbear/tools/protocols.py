"""Protocols and utilities for toolset capabilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic_ai.toolsets.wrapper import WrapperToolset

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from pydantic_ai.toolsets.abstract import AbstractToolset


@runtime_checkable
class WorkspaceAware(Protocol):
    """Toolset that can update its workspace root."""

    def update_workspace(self, workspace: Path) -> None:
        """Set the workspace root to *workspace*."""
        ...


def unwrap(toolset: AbstractToolset) -> AbstractToolset:
    """Peel all :class:`WrapperToolset` layers and return the innermost toolset."""
    inner = toolset
    while isinstance(inner, WrapperToolset):
        inner = inner.wrapped
    return inner


def find_toolset[T](toolsets: Iterable[AbstractToolset], cls: type[T]) -> T | None:
    """Return the first toolset matching *cls* after unwrapping, or ``None``."""
    for ts in toolsets:
        inner = unwrap(ts)
        if isinstance(inner, cls):
            return inner  # type: ignore[return-value]
    return None
