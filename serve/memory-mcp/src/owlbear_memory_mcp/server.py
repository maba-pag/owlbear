"""OwlBear MCP memory server for markdown-frontmatter memory operations."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context  # noqa: TC002 - MCPServer evaluates tool annotations at registration.
from mcp.types import ToolAnnotations
from owlbear_memory import MemoryCategory, MemoryEngine, MemoryState
from pydantic import Field

from owlbear_memory_mcp.agents import AgentCatalog
from owlbear_memory_mcp.tools import (
    approve_memory as approve_memory_impl,
)
from owlbear_memory_mcp.tools import (
    assess_memories as assess_memories_impl,
)
from owlbear_memory_mcp.tools import (
    curate_memory as curate_memory_impl,
)
from owlbear_memory_mcp.tools import (
    delete_agent_memories as delete_agent_memories_impl,
)
from owlbear_memory_mcp.tools import (
    delete_memory as delete_memory_impl,
)
from owlbear_memory_mcp.tools import (
    list_memories as list_memories_impl,
)
from owlbear_memory_mcp.tools import (
    read_memory as read_memory_impl,
)
from owlbear_memory_mcp.tools import (
    recall_memory as recall_memory_impl,
)
from owlbear_memory_mcp.tools import (
    rename_agent_memories as rename_agent_memories_impl,
)
from owlbear_memory_mcp.tools import (
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
    "delete_agent_memories",
    "delete_memory",
    "list_memories",
    "mcp",
    "read_memory",
    "recall_memory",
    "rename_agent_memories",
    "save_memory",
]

_DEFAULT_MEMORY_DIR = Path(".owlbear/memory")
_WORKSPACE_MARKER = Path(".owlbear")
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
    agents: AgentCatalog


@asynccontextmanager
async def app_lifespan(
    _server: MCPServer,
) -> AsyncGenerator[AppContext]:  # pragma: no cover
    """Construct and expose memory runtime context for this MCP session."""
    workspace_root = Path.cwd().resolve()
    if not (workspace_root / _WORKSPACE_MARKER).is_dir():
        message = f"OwlBear workspace marker not found: {_WORKSPACE_MARKER}"
        raise RuntimeError(message)
    yield AppContext(
        engine=MemoryEngine(memory_dir=workspace_root / _DEFAULT_MEMORY_DIR),
        agents=AgentCatalog(workspace_root),
    )


mcp = MCPServer("owlbear-memory", lifespan=app_lifespan)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False))
async def save_memory(  # noqa: PLR0913
    ctx: Context,
    *,
    title: _Title,
    content: _Content,
    categories: _Categories,
    confidence: _Confidence,
    source_agent: _Agent,
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


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True, destructive_hint=False))
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


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True, destructive_hint=False))
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


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True, destructive_hint=False))
async def read_memory(
    ctx: Context,
    *,
    entry_id: str,
) -> dict[str, Any]:  # pragma: no cover
    """Read a full memory entry by ID."""
    return await read_memory_impl(ctx, entry_id=entry_id)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=True))
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


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=True))
async def delete_memory(ctx: Context, *, entry_id: str) -> dict[str, Any]:  # pragma: no cover
    """Delete a memory entry with lifecycle-aware semantics."""
    return await delete_memory_impl(ctx, entry_id=entry_id)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=True))
async def rename_agent_memories(
    ctx: Context,
    *,
    old_name: _Agent,
    new_name: _Agent,
) -> dict[str, int]:  # pragma: no cover
    """Rewrite memory provenance and scopes after an agent rename."""
    return await rename_agent_memories_impl(ctx, old_name=old_name, new_name=new_name)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=True))
async def delete_agent_memories(ctx: Context, *, agent: _Agent) -> dict[str, int]:  # pragma: no cover
    """Delete memories and scope references for a removed agent."""
    return await delete_agent_memories_impl(ctx, agent=agent)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False))
async def approve_memory(ctx: Context, *, entry_id: str) -> dict[str, Any]:  # pragma: no cover
    """Approve a curated memory entry."""
    return await approve_memory_impl(ctx, entry_id=entry_id)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False))
async def assess_memories(
    ctx: Context,
    *,
    assessments: Annotated[list[dict[str, str]], Field(min_length=1)],
    task_id: _Agent,
) -> dict[str, Any]:  # pragma: no cover
    """Assess memories in batch and return per-entry outcomes."""
    return await assess_memories_impl(ctx, assessments=assessments, task_id=task_id)
