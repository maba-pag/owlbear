"""OwlBear MCP memory server for markdown-frontmatter memory operations."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from owlbear_memory import MemoryCategory, MemoryEngine, MemoryState
from pydantic import Field

from owlbear_mcp_memory.tools import (
    approve_memory as approve_memory_impl,
)
from owlbear_mcp_memory.tools import (
    assess_memories as assess_memories_impl,
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

__all__ = [
    "AppContext",
    "app_lifespan",
    "approve_memory",
    "assess_memories",
    "curate_memory",
    "delete_memory",
    "list_memories",
    "mcp",
    "read_memory",
    "recall_memory",
    "save_memory",
]

_DEFAULT_MEMORY_DIR = Path(".owlbear/memory")
_Title = Annotated[str, Field(min_length=1)]
_Content = Annotated[str, Field(max_length=1024)]
_Confidence = Annotated[float, Field(ge=0.7, le=1.0)]
_Agent = Annotated[str, Field(min_length=1)]
_Limit = Annotated[int, Field(ge=0)]
_Categories = Annotated[list[MemoryCategory], Field(min_length=1)]


@dataclass
class AppContext:
    """Runtime context passed through MCP lifespan to all tools."""

    engine: MemoryEngine


@asynccontextmanager
async def app_lifespan(
    _server: FastMCP,
) -> AsyncGenerator[AppContext]:  # pragma: no cover
    """Construct and expose memory runtime context for this MCP session."""
    memory_dir = Path(os.environ.get("OWLBEAR_MEMORY_DIR", str(_DEFAULT_MEMORY_DIR)))
    yield AppContext(engine=MemoryEngine(memory_dir=memory_dir))


mcp = FastMCP("owlbear-memory", lifespan=app_lifespan)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False, destructiveHint=False))
async def save_memory(  # noqa: PLR0913
    ctx: Context,
    *,
    title: _Title,
    content: _Content,
    categories: _Categories,
    confidence: _Confidence,
    source_agent: _Agent,
    scope_agents: list[str] | None = None,
) -> dict[str, Any]:  # pragma: no cover
    """Create a new pending memory entry with explicit source agent."""
    return await save_memory_impl(
        ctx,
        title=title,
        content=content,
        categories=categories,
        confidence=confidence,
        source_agent=source_agent,
        scope_agents=scope_agents,
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def list_memories(
    ctx: Context,
    *,
    states: list[MemoryState] | None = None,
    categories: Annotated[list[MemoryCategory] | None, Field(min_length=1)] = None,
    scope_agents: list[str] | None = None,
) -> list[dict[str, Any]]:  # pragma: no cover
    """List memory metadata sorted by curation priority."""
    return await list_memories_impl(
        ctx,
        states=states,
        categories=categories,
        scope_agents=scope_agents,
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def recall_memory(
    ctx: Context,
    *,
    agent: _Agent,
    categories: list[MemoryCategory] | None = None,
    limit: _Limit | None = None,
) -> str:  # pragma: no cover
    """Recall markdown body blocks for entries scoped to a specific agent."""
    return await recall_memory_impl(
        ctx,
        agent=agent,
        categories=categories,
        limit=limit,
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def read_memory(
    ctx: Context,
    *,
    entry_id: str,
) -> dict[str, Any]:  # pragma: no cover
    """Read a full memory entry by ID."""
    return await read_memory_impl(ctx, entry_id=entry_id)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False, destructiveHint=True))
async def curate_memory(  # noqa: PLR0913
    ctx: Context,
    *,
    entry_id: str,
    title: _Title | None = None,
    content: _Content | None = None,
    categories: list[MemoryCategory] | None = None,
    confidence: _Confidence | None = None,
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
        scope_agents=scope_agents,
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False, destructiveHint=True))
async def delete_memory(ctx: Context, *, entry_id: str) -> dict[str, Any]:  # pragma: no cover
    """Delete a memory entry with lifecycle-aware semantics."""
    return await delete_memory_impl(ctx, entry_id=entry_id)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False, destructiveHint=False))
async def approve_memory(ctx: Context, *, entry_id: str) -> dict[str, Any]:  # pragma: no cover
    """Approve a curated memory entry."""
    return await approve_memory_impl(ctx, entry_id=entry_id)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False, destructiveHint=False))
async def assess_memories(
    ctx: Context,
    *,
    assessments: Annotated[list[dict[str, str]], Field(min_length=1)],
    task_id: _Agent,
) -> dict[str, Any]:  # pragma: no cover
    """Assess memories in batch and return per-entry outcomes."""
    return await assess_memories_impl(ctx, assessments=assessments, task_id=task_id)
