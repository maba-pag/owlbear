"""Native change authority and delivery graph HTTP resources."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException

from owlbear_cockpit.deps import NativeChangeContext, NativeContextCache, get_native_context_cache, get_workspace
from owlbear_cockpit.native_models import (
    ChangeDetailResponse,
    ChangeGraphResponse,
    ChangeListEntryResponse,
    ChangeListResponse,
    NativeDiagnosticResponse,
)
from owlbear_kanban import ChangeDiagnostic, ChangeDiagnosticCode, ChangeRevision, NativeWorkspace

if TYPE_CHECKING:
    from pathlib import Path

router = APIRouter(prefix="/changes", tags=["native-changes"])
_Workspace = Annotated[NativeWorkspace, Depends(get_workspace)]
_NativeCache = Annotated[NativeContextCache, Depends(get_native_context_cache)]


def _diagnostics(items: tuple[ChangeDiagnostic, ...]) -> tuple[NativeDiagnosticResponse, ...]:
    return tuple(
        NativeDiagnosticResponse(code=item.code.value, detail=item.detail, target=item.target) for item in items
    )


def _load_revision(cache: NativeContextCache, changes_dir: Path, change_id: str) -> ChangeRevision:
    loaded = cache.load(changes_dir, change_id)
    if loaded.revision is not None:
        return loaded.revision
    diagnostics = _diagnostics(loaded.diagnostics)
    missing = (
        any(item.code is ChangeDiagnosticCode.FILE_MISSING for item in loaded.diagnostics)
        and not (changes_dir / change_id).is_dir()
    )
    raise HTTPException(
        status_code=404 if missing else 422,
        detail={
            "code": "ERR_CHANGE_NOT_FOUND" if missing else "ERR_CHANGE_INVALID",
            "message": "change not found" if missing else "change authority is invalid",
            "diagnostics": [item.model_dump(mode="json") for item in diagnostics],
        },
    )


def get_native_context(change_id: str, workspace: NativeWorkspace, cache: NativeContextCache) -> NativeChangeContext:
    """Load and assemble one native context or raise its stable HTTP error."""
    changes_dir = workspace.changes_dir
    revision = _load_revision(cache, changes_dir, change_id)
    try:
        return cache.get(
            workspace=workspace,
            revision=revision,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "ERR_NATIVE_CONTEXT_UNAVAILABLE", "message": "native context assembly failed"},
        ) from exc


@router.get("", response_model=ChangeListResponse)
def list_changes(workspace: _Workspace, cache: _NativeCache) -> ChangeListResponse:
    """List loaded and malformed sibling native changes in identity order."""
    changes_dir = workspace.changes_dir
    if not changes_dir.is_dir():
        return ChangeListResponse(changes=())
    entries: list[ChangeListEntryResponse] = []
    for child in sorted(changes_dir.iterdir(), key=lambda item: item.name):
        if not child.is_dir() or child.name.startswith("."):
            continue
        loaded = cache.load(changes_dir, child.name)
        if loaded.revision is not None:
            entries.append(
                ChangeListEntryResponse(
                    change_id=child.name,
                    state="loaded",
                    delivery_digest=loaded.revision.delivery_digest,
                )
            )
        else:
            entries.append(
                ChangeListEntryResponse(
                    change_id=child.name,
                    state="invalid",
                    diagnostics=_diagnostics(loaded.diagnostics),
                )
            )
    return ChangeListResponse(changes=tuple(entries))


@router.get("/{change_id}", response_model=ChangeDetailResponse)
def show_change(
    change_id: str,
    workspace: _Workspace,
    cache: _NativeCache,
) -> ChangeDetailResponse:
    """Return joined authority for one native change revision."""
    revision = get_native_context(change_id, workspace, cache).revision
    return ChangeDetailResponse(
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        intent=revision.intent,
        design=revision.design,
        decisions=revision.decisions.model_dump(mode="json"),
        graph=revision.graph.model_dump(mode="json"),
    )


@router.get("/{change_id}/graph", response_model=ChangeGraphResponse)
def show_change_graph(
    change_id: str,
    workspace: _Workspace,
    cache: _NativeCache,
) -> ChangeGraphResponse:
    """Return delivery graph authority and current isolated node plans."""
    revision = get_native_context(change_id, workspace, cache).revision
    plans = {node.id: plan for node in revision.graph.nodes if (plan := revision.read_node_plan(node.id)) is not None}
    return ChangeGraphResponse(
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        graph=revision.graph.model_dump(mode="json"),
        plans=plans,
    )


__all__ = ["get_native_context", "router"]
