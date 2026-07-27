"""Bounded read-only inventory of the immutable legacy snapshot."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from owlbear_cockpit.deps import get_workspace
from owlbear_kanban import LegacySnapshotFile, LegacySnapshotManifest, NativeWorkspace

if TYPE_CHECKING:
    from pathlib import Path

router = APIRouter(tags=["legacy-inventory"])
_Workspace = Annotated[NativeWorkspace, Depends(get_workspace)]
_Limit = Annotated[int, Query(ge=1, le=100)]


class LegacyTaskEntry(BaseModel):
    """One legacy task summary with its source-store provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provenance: Literal["tasks", "archive"]
    task: dict[str, object]


class LegacyRequestEntry(BaseModel):
    """One legacy request with its source-store provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provenance: Literal["decisions/pending", "decisions/resolved"]
    request: dict[str, object]


class LegacyActivityEntry(BaseModel):
    """One legacy activity event with its source-store provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provenance: Literal["activity.jsonl"] = "activity.jsonl"
    event: dict[str, object]


class LegacyInventoryResponse(BaseModel):
    """Bounded inventory with explicit truncation state and no mutation links."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tasks: tuple[LegacyTaskEntry, ...] = ()
    requests: tuple[LegacyRequestEntry, ...] = ()
    activity: tuple[LegacyActivityEntry, ...] = ()
    truncated: dict[Literal["tasks", "requests", "activity"], bool] = Field(
        default_factory=lambda: {"tasks": False, "requests": False, "activity": False}
    )


@router.get("/legacy", response_model=LegacyInventoryResponse)
def legacy_inventory(workspace: _Workspace, limit: _Limit = 100) -> LegacyInventoryResponse:
    """Return capped file metadata from the immutable legacy manifest."""
    manifest = _load_manifest(workspace.legacy_snapshot_root)
    if manifest is None:
        return LegacyInventoryResponse()
    tasks = tuple(entry for item in manifest.files if (entry := _task_entry(item)) is not None)
    requests = tuple(entry for item in manifest.files if (entry := _request_entry(item)) is not None)
    activity = tuple(
        LegacyActivityEntry(event=_metadata(item)) for item in manifest.files if item.relative_path == "activity.jsonl"
    )
    return LegacyInventoryResponse(
        tasks=tasks[:limit],
        requests=requests[:limit],
        activity=activity[-limit:],
        truncated={
            "tasks": len(tasks) > limit,
            "requests": len(requests) > limit,
            "activity": len(activity) > limit,
        },
    )


def _load_manifest(root: Path) -> LegacySnapshotManifest | None:
    path = root / "manifest.json"
    if not path.is_file():
        return None
    return LegacySnapshotManifest.model_validate_json(path.read_bytes())


def _metadata(item: LegacySnapshotFile) -> dict[str, object]:
    return item.model_dump(mode="json")


def _task_entry(item: LegacySnapshotFile) -> LegacyTaskEntry | None:
    if item.relative_path.startswith("tasks/"):
        return LegacyTaskEntry(provenance="tasks", task=_metadata(item))
    if item.relative_path.startswith("archive/"):
        return LegacyTaskEntry(provenance="archive", task=_metadata(item))
    return None


def _request_entry(item: LegacySnapshotFile) -> LegacyRequestEntry | None:
    if item.relative_path.startswith("decisions/pending/"):
        return LegacyRequestEntry(provenance="decisions/pending", request=_metadata(item))
    if item.relative_path.startswith("decisions/resolved/"):
        return LegacyRequestEntry(provenance="decisions/resolved", request=_metadata(item))
    return None


__all__ = ["router"]
