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
    approve_memory as approve_memory_impl,
)
from owlbear_mcp_memory.tools import (
    curate_memory as curate_memory_impl,
)
from owlbear_mcp_memory.tools import (
    delete_memory as delete_memory_impl,
)
from owlbear_mcp_memory.tools import (
    list_memories as list_memories_impl,
)
from owlbear_mcp_memory.tools import (
    read_memory as read_memory_impl,
)
from owlbear_mcp_memory.tools import (
    recall_memory as recall_memory_impl,
)
from owlbear_mcp_memory.tools import (
    save_memory as save_memory_impl,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

_DEFAULT_MEMORY_DIR = Path(".owlbear/memory")


@dataclass
class AppContext:
    """Runtime context passed through MCP lifespan to all tools."""

    engine: MemoryEngine


@asynccontextmanager
async def app_lifespan(
    _server: FastMCP,
) -> AsyncGenerator[AppContext, None]:  # pragma: no cover
    """Construct and expose memory runtime context for this MCP session."""
    memory_dir = Path(os.environ.get("OWLBEAR_MEMORY_DIR", str(_DEFAULT_MEMORY_DIR)))
    yield AppContext(engine=MemoryEngine(memory_dir=memory_dir))


mcp = FastMCP("owlbear-memory", lifespan=app_lifespan)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False))
async def save_memory(  # noqa: PLR0913
    ctx: Context,
    *,
    title: str,
    content: str,
    categories: list[str],
    confidence: float,
    source_agent: str,
) -> dict[str, Any]:  # pragma: no cover
    """Create a new pending memory entry with explicit source agent."""
    return await save_memory_impl(
        ctx,
        title=title,
        content=content,
        categories=categories,
        confidence=confidence,
        source_agent=source_agent,
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def list_memories(
    ctx: Context,
    *,
    states: list[str] | None = None,
    categories: list[str] | None = None,
    scope_agents: list[str] | None = None,
) -> list[dict[str, Any]]:  # pragma: no cover
    """List memory metadata sorted by curation priority."""
    return await list_memories_impl(
        ctx,
        states=states,
        categories=categories,
        scope_agents=scope_agents,
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def recall_memory(
    ctx: Context,
    *,
    agent: str,
    categories: list[str] | None = None,
    limit: int | None = None,
) -> str:  # pragma: no cover
    """Recall markdown body blocks for entries scoped to a specific agent."""
    return await recall_memory_impl(
        ctx,
        agent=agent,
        categories=categories,
        limit=limit,
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False))
async def read_memory(
    ctx: Context,
    *,
    entry_id: str,
) -> dict[str, Any]:  # pragma: no cover
    """Read a full memory entry by ID."""
    return await read_memory_impl(ctx, entry_id=entry_id)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False))
async def curate_memory(  # noqa: PLR0913
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
    """Curate and mutate a memory entry."""
    return await curate_memory_impl(
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
async def delete_memory(
    ctx: Context, *, entry_id: str
) -> dict[str, Any]:  # pragma: no cover
    """Delete a memory entry with lifecycle-aware semantics."""
    return await delete_memory_impl(ctx, entry_id=entry_id)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False))
async def approve_memory(
    ctx: Context, *, entry_id: str
) -> dict[str, Any]:  # pragma: no cover
    """Approve a curated memory entry."""
    return await approve_memory_impl(ctx, entry_id=entry_id)
