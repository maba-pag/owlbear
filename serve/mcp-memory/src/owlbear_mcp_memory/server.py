"""OwlBear MCP memory server for markdown-frontmatter memory operations."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from owlbear_mcp_memory.engine import MemoryEngine
from owlbear_mcp_memory.tools import (
    approve_entry as approve_entry_impl,
)
from owlbear_mcp_memory.tools import (
    delete_entry as delete_entry_impl,
)
from owlbear_mcp_memory.tools import (
    query_memory as query_memory_impl,
)
from owlbear_mcp_memory.tools import (
    store_learning as store_learning_impl,
)
from owlbear_mcp_memory.tools import (
    update_entry as update_entry_impl,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

_DEFAULT_MEMORY_DIR = Path(".owlbear/memory")


@dataclass
class AppContext:
    """Runtime context passed through MCP lifespan to all tools."""

    engine: MemoryEngine
    caller: str


def _apply_tool_exclusions(server: FastMCP) -> set[str]:  # pragma: no cover
    """Remove tools listed in MEMORY_TOOLS_EXCLUDE, ignoring unknown names."""
    excluded: set[str] = set()
    env_val = os.environ.get("MEMORY_TOOLS_EXCLUDE", "")
    if not env_val:
        return excluded
    for raw in env_val.split(","):
        tool_name = raw.strip()
        if not tool_name:
            continue
        try:
            server.remove_tool(tool_name)
            excluded.add(tool_name)
        except Exception:  # noqa: BLE001,S110
            pass
    return excluded


@asynccontextmanager
async def app_lifespan(
    server: FastMCP,
) -> AsyncGenerator[AppContext, None]:  # pragma: no cover
    """Construct and expose memory runtime context for this MCP session."""
    memory_dir = Path(os.environ.get("OWLBEAR_MEMORY_DIR", str(_DEFAULT_MEMORY_DIR)))
    caller = os.environ.get("OWLBEAR_MEMORY_CALLER", "unknown")
    _apply_tool_exclusions(server)
    yield AppContext(engine=MemoryEngine(memory_dir=memory_dir), caller=caller)


mcp = FastMCP("owlbear-memory", lifespan=app_lifespan)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False))
async def store_learning(  # noqa: PLR0913
    ctx: Context,
    *,
    title: str,
    content: str,
    categories: list[str],
    confidence: float,
    scope_agents: list[str] | None = None,
) -> dict[str, Any]:  # pragma: no cover
    """Create a new pending memory entry."""
    return await store_learning_impl(
        ctx,
        title=title,
        content=content,
        categories=categories,
        confidence=confidence,
        scope_agents=scope_agents,
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def query_memory(  # noqa: PLR0913
    ctx: Context,
    *,
    states: list[str] | None = None,
    categories: list[str] | None = None,
    scope_agents: list[str] | None = None,
    min_confidence: float | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:  # pragma: no cover
    """Query memory entries by lifecycle state and priority ordering."""
    return await query_memory_impl(
        ctx,
        states=states,
        categories=categories,
        scope_agents=scope_agents,
        min_confidence=min_confidence,
        limit=limit,
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False))
async def update_entry(  # noqa: PLR0913
    ctx: Context,
    *,
    entry_id: str,
    title: str | None = None,
    content: str | None = None,
    categories: list[str] | None = None,
    confidence: float | None = None,
    state: str | None = None,
    scope_agents: list[str] | None = None,
) -> dict[str, Any]:  # pragma: no cover
    """Update mutable fields of an entry (curator-only)."""
    return await update_entry_impl(
        ctx,
        entry_id=entry_id,
        title=title,
        content=content,
        categories=categories,
        confidence=confidence,
        state=state,
        scope_agents=scope_agents,
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True))
async def delete_entry(
    ctx: Context, *, entry_id: str
) -> dict[str, Any]:  # pragma: no cover
    """Mark an entry as deleted (curator-only)."""
    return await delete_entry_impl(ctx, entry_id=entry_id)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False))
async def approve_entry(
    ctx: Context, *, entry_id: str
) -> dict[str, Any]:  # pragma: no cover
    """Promote a curated entry to approved (user-only)."""
    return await approve_entry_impl(ctx, entry_id=entry_id)
