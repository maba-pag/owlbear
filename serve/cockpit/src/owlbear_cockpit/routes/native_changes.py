"""Native change authority and delivery graph HTTP resources."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from owlbear_cockpit.deps import NativeChangeContext, NativeContextCache, get_engine, get_native_context_cache
from owlbear_cockpit.native_models import (
    ChangeDetailResponse,
    ChangeGraphResponse,
    ChangeListEntryResponse,
    ChangeListResponse,
    NativeDiagnosticResponse,
)
from owlbear_kanban import ChangeDiagnostic, ChangeDiagnosticCode, ChangeRevision, KanbanEngine
from owlbear_kanban._duration import _parse_duration

router = APIRouter(prefix="/changes", tags=["native-changes"])
_Engine = Annotated[KanbanEngine, Depends(get_engine)]
_NativeCache = Annotated[NativeContextCache, Depends(get_native_context_cache)]


def _roots(engine: KanbanEngine) -> tuple[Path, Path, Path]:
    work_root = Path(engine.kanban_dir)
    return work_root.parent / "changes", work_root, work_root.parent.parent


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


def _context(change_id: str, engine: KanbanEngine, cache: NativeContextCache) -> NativeChangeContext:
    changes_dir, work_root, workspace_root = _roots(engine)
    revision = _load_revision(cache, changes_dir, change_id)
    try:
        return cache.get(
            changes_dir=changes_dir,
            work_root=work_root,
            workspace_root=workspace_root,
            revision=revision,
            claim_expiry=_parse_duration(engine.board_config().pipeline.claim_timeout),
        )
    except (OSError, RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "ERR_NATIVE_CONTEXT_UNAVAILABLE", "message": "native context assembly failed"},
        ) from exc


@router.get("", response_model=ChangeListResponse)
def list_changes(engine: _Engine, cache: _NativeCache) -> ChangeListResponse:
    """List loaded and malformed sibling native changes in identity order."""
    changes_dir, _, _ = _roots(engine)
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
    engine: _Engine,
    cache: _NativeCache,
) -> ChangeDetailResponse:
    """Return joined authority for one native change revision."""
    revision = _context(change_id, engine, cache).revision
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
    engine: _Engine,
    cache: _NativeCache,
) -> ChangeGraphResponse:
    """Return delivery graph authority and current isolated node plans."""
    revision = _context(change_id, engine, cache).revision
    plans = {node.id: plan for node in revision.graph.nodes if (plan := revision.read_node_plan(node.id)) is not None}
    return ChangeGraphResponse(
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        graph=revision.graph.model_dump(mode="json"),
        plans=plans,
    )


__all__ = ["router"]
