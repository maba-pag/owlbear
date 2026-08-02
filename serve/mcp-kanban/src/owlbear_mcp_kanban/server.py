"""Live OwlBear MCP server for target delivery."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from owlbear_kanban.attempts import AttemptStore
from owlbear_kanban.target_admission import TargetAuthorityRegistry
from owlbear_kanban.target_cutover import (
    TargetCutoverError,
    TargetCutoverRequest,
    authorize_target_mutation,
)
from owlbear_kanban.target_runtime import TargetRuntime
from owlbear_mcp_kanban.target_server import (
    TargetAppContext,
    TargetChangeBinding,
    TargetMCPAdapter,
    register_target_tools,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from owlbear_kanban.target_authority import TargetAuthority

_DEFAULT_WORKSPACE_ROOT = Path.cwd()
_DEFAULT_CUTOVER_REQUEST = Path(".owlbear/target-cutover-request.json")
_live_changes: dict[str, TargetChangeBinding] = {}
_live_runtime_roots: dict[str, Path] = {}


def _resolve_workspace_root() -> Path:
    configured = os.environ.get("OWLBEAR_WORKSPACE_ROOT", "").strip()
    return (Path(configured) if configured else _DEFAULT_WORKSPACE_ROOT).resolve()


def _resolve_request_path(workspace_root: Path) -> Path:
    configured = os.environ.get("OWLBEAR_TARGET_CUTOVER_REQUEST", "").strip()
    selected = Path(configured) if configured else _DEFAULT_CUTOVER_REQUEST
    return selected.resolve() if selected.is_absolute() else (workspace_root / selected).resolve()


def _process_is_alive(process_id: str) -> bool:
    try:
        process = int(process_id)
        if process <= 0:
            return False
        os.kill(process, 0)
    except ProcessLookupError, ValueError:
        return False
    except PermissionError:
        return True
    return True


def _work_item_activity(change_id: str, work_item_id: str) -> tuple[dict[str, object], ...]:
    root = _live_runtime_roots.get(change_id)
    if root is None:
        return ()
    return tuple(
        event.model_dump(mode="json")
        for event in AttemptStore(root).list()
        if event.change_id == change_id and event.target_node_id == work_item_id
    )


_live_context = TargetAppContext(
    changes=_live_changes,
    process_is_alive=_process_is_alive,
    work_item_activity=_work_item_activity,
)


def load_target_context(workspace_root: Path, request_path: Path) -> TargetAppContext:
    """Load and receipt-authorize all target changes for one workspace."""
    try:
        request = TargetCutoverRequest.model_validate_json(request_path.read_bytes())
        authorize_target_mutation(workspace_root, request)
    except (OSError, ValidationError, TargetCutoverError) as exc:
        message = "target delivery startup requires a valid cutover request and receipt"
        raise RuntimeError(message) from exc

    target_root = workspace_root / request.target_path
    registry = TargetAuthorityRegistry(target_root)
    changes: dict[str, TargetChangeBinding] = {}

    def bind_authority(authority: TargetAuthority) -> TargetChangeBinding:
        runtime_root = target_root / "changes" / authority.change_id
        runtime = TargetRuntime(authority, runtime_root)
        runtime.list_frontier()
        _live_runtime_roots[authority.change_id] = runtime_root
        return TargetChangeBinding(authority=authority, runtime=runtime)

    _live_runtime_roots.clear()
    for authority in registry.list_authorities():
        changes[authority.change_id] = bind_authority(authority)
    return TargetAppContext(
        changes=changes,
        process_is_alive=_process_is_alive,
        work_item_activity=_work_item_activity,
        authority_registry=registry,
        bind_authority=bind_authority,
    )


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncGenerator[TargetAppContext]:
    """Load the receipt-authorized target portfolio for one MCP process."""
    workspace_root = _resolve_workspace_root()
    loaded = load_target_context(workspace_root, _resolve_request_path(workspace_root))
    _live_changes.clear()
    _live_changes.update(loaded.changes)
    _live_context.authority_registry = loaded.authority_registry
    _live_context.bind_authority = loaded.bind_authority
    try:
        yield _live_context
    finally:
        _live_changes.clear()
        _live_runtime_roots.clear()
        _live_context.authority_registry = None
        _live_context.bind_authority = None


mcp = FastMCP("owlbear-kanban", lifespan=app_lifespan)
register_target_tools(mcp, TargetMCPAdapter(_live_context))

__all__ = [
    "TargetAppContext",
    "TargetChangeBinding",
    "TargetMCPAdapter",
    "app_lifespan",
    "load_target_context",
    "mcp",
]
