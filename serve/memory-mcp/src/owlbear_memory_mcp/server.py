"""OwlBear MCP memory server for markdown-frontmatter memory operations."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver import Context  # noqa: TC002 - MCPServer evaluates tool annotations at registration.
from mcp.types import ToolAnnotations
from owlbear_memory import MemoryCategory, MemoryEngine, MemoryState, Where
from pydantic import Field, StrictStr

from owlbear_memory_mcp.store import shared_stores
from owlbear_memory_mcp.tools import (
    AssessmentItem,
    AssessmentTaskId,
)
from owlbear_memory_mcp.tools import (
    approve_memory as approve_memory_impl,
)
from owlbear_memory_mcp.tools import (
    assess_memories as assess_memories_impl,
)
from owlbear_memory_mcp.tools import (
    commit_memory_batch as commit_memory_batch_impl,
)
from owlbear_memory_mcp.tools import (
    curate_memory as curate_memory_impl,
)
from owlbear_memory_mcp.tools import (
    curation_threshold as curation_threshold_impl,
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
    make_global as make_global_impl,
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
    "commit_memory_batch",
    "curate_memory",
    "curation_threshold",
    "delete_agent_memories",
    "delete_memory",
    "list_memories",
    "make_global",
    "mcp",
    "memory_dir",
    "read_memory",
    "recall_memory",
    "rename_agent_memories",
    "save_memory",
]

_DEFAULT_MEMORY_DIR = Path(".owlbear/memory")
_WORKSPACE_MARKER = Path(".owlbear")
MEMORY_DIR_ENV = "OWLBEAR_MEMORY_DIR"  # an explicit store, such as a project's folder in the shared repository
MEMORY_GLOBAL_ENV = "OWLBEAR_MEMORY_GLOBAL_DIR"  # the shared repository's Global memory, read only (TD-241)
_Title = Annotated[str, Field(min_length=1)]
_Content = Annotated[str, Field(max_length=1024)]
_Confidence = Annotated[float, Field(ge=0.7, le=1.0)]
_Agent = Annotated[str, Field(min_length=1)]
_Revision = Annotated[str, Field(pattern=r"^[0-9a-f]{16}$")]
_RecallAgent = Annotated[StrictStr | Literal[0] | None, Field(default=None)]
_Limit = Annotated[int, Field(ge=0)]
_Categories = Annotated[list[MemoryCategory], Field(min_length=1)]
_BatchSession = Literal["curation", "review"]
_Folder = Annotated[
    str | None,
    Field(
        description="For the memory curator: another project folder of the shared repository to work on, by its "
        "name; omit for this server's own folder. Global memory is never named here: it changes only by make_global."
    ),
]
_Where = Annotated[
    Where,
    Field(
        description="Your recommended scope (TD-293): project for a lesson specific to this project, global for "
        "one that holds in any project. It only recommends: the entry stays pending in this project until curated."
    ),
]


@dataclass
class AppContext:
    """Runtime context passed through MCP lifespan to all tools."""

    engine: MemoryEngine
    memory_dir: Path
    global_dir: Path | None = None  # the shared repository's Global memory, read beside the store and never written
    global_engine: MemoryEngine | None = None  # opened once ``global_dir`` exists; Make global may create it later


def memory_dir() -> Path:
    """The store: ``OWLBEAR_MEMORY_DIR``, else the workspace's shared folder (TD-72), else ``.owlbear/memory``."""
    if explicit := os.environ.get(MEMORY_DIR_ENV):
        return Path(explicit).expanduser().resolve()
    workspace_root = Path.cwd().resolve()
    if shared := shared_stores(workspace_root):
        return shared[0]
    if not (workspace_root / _WORKSPACE_MARKER).is_dir():
        message = f"OwlBear workspace marker not found: {_WORKSPACE_MARKER}"
        raise RuntimeError(message)
    return workspace_root / _DEFAULT_MEMORY_DIR


def global_dir() -> Path | None:
    """Global memory, read and never written: ``OWLBEAR_MEMORY_GLOBAL_DIR``, else the shared store's (TD-241)."""
    if explicit := os.environ.get(MEMORY_GLOBAL_ENV):
        return Path(explicit).expanduser().resolve()
    if os.environ.get(MEMORY_DIR_ENV):
        return None
    shared = shared_stores(Path.cwd().resolve())
    return shared[1] if shared else None


@asynccontextmanager
async def app_lifespan(
    _server: MCPServer,
) -> AsyncGenerator[AppContext]:  # pragma: no cover
    """Construct and expose memory runtime context for this MCP session."""
    store, shared = memory_dir(), global_dir()
    common = shared if shared != store else None
    yield AppContext(engine=MemoryEngine(memory_dir=store), memory_dir=store, global_dir=common)


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
    where: _Where,
) -> dict[str, Any]:  # pragma: no cover
    """Create a new pending memory entry with explicit source agent and its recommended scope."""
    return await save_memory_impl(
        ctx,
        title=title,
        content=content,
        categories=categories,
        confidence=confidence,
        source_agent=source_agent,
        where=where,
    )


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True, destructive_hint=False))
async def list_memories(
    ctx: Context,
    *,
    states: list[MemoryState] | None = None,
    categories: Annotated[list[MemoryCategory] | None, Field(min_length=1)] = None,
    scope_agents: list[str] | None = None,
    folder: _Folder = None,
) -> list[dict[str, Any]]:  # pragma: no cover
    """List memory metadata sorted by curation priority."""
    return await list_memories_impl(
        ctx,
        states=states,
        categories=categories,
        scope_agents=scope_agents,
        folder=folder,
    )


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True, destructive_hint=False))
async def recall_memory(
    ctx: Context,
    *,
    agent: _RecallAgent = None,
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
    folder: _Folder = None,
) -> dict[str, Any]:  # pragma: no cover
    """Read a full memory entry by ID."""
    return await read_memory_impl(ctx, entry_id=entry_id, folder=folder)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=True))
async def curate_memory(  # noqa: PLR0913
    ctx: Context,
    *,
    entry_id: str,
    revision: _Revision,
    title: _Title | None = None,
    content: _Content | None = None,
    categories: list[MemoryCategory] | None = None,
    confidence: _Confidence | None = None,
    scope_agents: list[str] | None = None,
    folder: _Folder = None,
) -> dict[str, Any]:  # pragma: no cover
    """Curate and mutate a memory entry."""
    return await curate_memory_impl(
        ctx,
        entry_id=entry_id,
        revision=revision,
        title=title,
        content=content,
        categories=categories,
        confidence=confidence,
        scope_agents=scope_agents,
        folder=folder,
    )


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False))
async def commit_memory_batch(
    ctx: Context, *, session_type: _BatchSession, folder: _Folder = None
) -> dict[str, Any]:  # pragma: no cover
    """Commit reviewed non-pending memory entries for one curation or review session."""
    return await commit_memory_batch_impl(ctx, session_type=session_type, folder=folder)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=True))
async def delete_memory(
    ctx: Context, *, entry_id: str, revision: _Revision, folder: _Folder = None
) -> dict[str, Any]:  # pragma: no cover
    """Delete a memory entry with lifecycle-aware semantics."""
    return await delete_memory_impl(ctx, entry_id=entry_id, revision=revision, folder=folder)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False))
async def make_global(
    ctx: Context, *, entry_id: str, revision: _Revision, folder: _Folder = None
) -> dict[str, Any]:  # pragma: no cover
    """Move a curated or approved entry into Global memory, recording its project, and commit (TD-292)."""
    return await make_global_impl(ctx, entry_id=entry_id, revision=revision, folder=folder)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True, destructive_hint=False))
async def curation_threshold(ctx: Context) -> dict[str, Any]:  # pragma: no cover
    """The curator's confidence threshold in percent: at or above it the curator acts alone (TD-400)."""
    return await curation_threshold_impl(ctx)


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
    """Remove a retired agent from scopes while preserving provenance."""
    return await delete_agent_memories_impl(ctx, agent=agent)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False))
async def approve_memory(ctx: Context, *, entry_id: str, revision: _Revision) -> dict[str, Any]:  # pragma: no cover
    """Approve a curated memory entry."""
    return await approve_memory_impl(ctx, entry_id=entry_id, revision=revision)


@mcp.tool(annotations=ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False))
async def assess_memories(
    ctx: Context,
    *,
    assessments: Annotated[list[AssessmentItem], Field(min_length=1)],
    task_id: AssessmentTaskId,
) -> dict[str, Any]:  # pragma: no cover
    """Assess memories in batch and return per-entry outcomes."""
    return await assess_memories_impl(ctx, assessments=assessments, task_id=task_id)
