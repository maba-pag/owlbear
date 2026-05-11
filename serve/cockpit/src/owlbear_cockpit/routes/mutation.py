"""Cockpit mutation API routes — move, edit, release, sweep, scan, repair, compact-activity."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from owlbear_cockpit.deps import get_view
from owlbear_cockpit.view import CockpitView
from owlbear_kanban.errors import (
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from owlbear_kanban.models import (
    ActivityCompactionResult,
    CleanupResult,
    RepairOutcome,
    SingleTaskResponse,
)

router = APIRouter()

_View = Annotated[CockpitView, Depends(get_view)]


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class MoveRequest(BaseModel):
    """Request body for POST /tasks/{id}/move."""

    model_config = ConfigDict(extra="forbid")

    status: str
    updated: str
    archival_reason: str | None = None
    archival_refs: list[int] | None = None


class EditRequest(BaseModel):
    """Request body for POST /tasks/{id}/edit.

    Only allowlisted fields accepted. ``extra="forbid"`` rejects ``status``,
    ``blocked``, and any other non-allowlisted fields with 422.

    Tri-state field semantics (``model_fields_set`` distinguishes omit from null):

    - ``body: ""`` clears task body; ``body: null`` or omitted = no change.
    - ``parent: null`` clears parent; negative value → 422; omitted = no change.
    - ``block_reason: ""`` or ``null`` unblocks; non-empty string sets block reason.
    """

    model_config = ConfigDict(extra="forbid")

    updated: str
    title: str | None = None
    tags: list[str] | None = None
    priority: str | None = None
    depends_on: list[int] | None = None
    parent: int | None = None
    block_reason: str | None = None
    body: str | None = None


class ReleaseRequest(BaseModel):
    """Request body for POST /tasks/{id}/release."""

    model_config = ConfigDict(extra="forbid")

    updated: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task_to_single(task: Any) -> SingleTaskResponse:  # noqa: ANN401
    if hasattr(task, "model_dump"):
        payload = task.model_dump()
        if payload.get("body") is None:
            payload["body"] = ""
        payload["guidance"] = payload.get("guidance") or []
        return SingleTaskResponse.model_validate(payload)

    return SingleTaskResponse(
        id=task.id,
        title=task.title,
        status=task.status,
        priority=task.priority,
        body=task.body,
        updated=task.updated,
        created=task.created,
        tags=task.tags or [],
        blocked=task.blocked,
        block_reason=task.block_reason,
        parent=task.parent,
        depends_on=task.depends_on or [],
        claimed_at=getattr(task, "claimed_at", None),
        claimed_by=getattr(task, "claimed_by", None),
        guidance=[],
    )


def _serialize_scan_item(item: Any) -> dict[str, Any]:  # noqa: ANN401
    """Normalize corruption scan items into JSON-serializable dictionaries."""
    if isinstance(item, dict):
        return {
            "code": item.get("code"),
            "detail": item.get("detail"),
            "file_path": item.get("file_path"),
        }

    file_path = getattr(item, "file_path", None)
    if file_path is None:
        path = getattr(item, "path", None)
        file_path = str(path) if path is not None else None

    detail = (
        getattr(item, "detail", None)
        or getattr(item, "user_message", None)
        or str(item)
    )

    return {
        "code": getattr(item, "code", None),
        "detail": detail,
        "file_path": file_path,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/tasks/{task_id}/move", response_model=SingleTaskResponse)
def move_task(task_id: int, req: MoveRequest, view: _View) -> SingleTaskResponse:
    """Move task to a new status. Validates OCC token then valid_transitions; archived skips transition check."""
    try:
        task = view.engine.show_task(str(task_id))
    except FileNotFoundError:
        raise NotFoundError(
            code="ERR_NOT_FOUND",
            user_message=f"Task {task_id} not found",
        ) from None

    if req.updated != str(task.updated):
        raise ConcurrencyError(
            code="ERR_STALE",
            user_message="Task was modified since your last load (stale snapshot)",
        )

    transitions = view.engine.valid_transitions(task.status)
    if req.status != "archived" and req.status not in transitions:
        raise ValidationError(
            code="ERR_INVALID_STATUS",
            user_message=f"Cannot move from '{task.status}' to '{req.status}'",
        )

    updated_task = view.move_task(
        task_id,
        req.status,
        expected_updated=req.updated,
        archival_reason=req.archival_reason,
        archival_refs=req.archival_refs,
    )
    return _task_to_single(updated_task)


def _build_edit_kwargs(req: EditRequest, task: Any | None = None) -> dict[str, Any]:  # noqa: ANN401
    """Translate EditRequest fields into CockpitView.edit_task keyword arguments."""
    fields = req.model_fields_set - {"updated"}
    kwargs: dict[str, Any] = {}

    if "title" in fields and req.title is not None:
        kwargs["title"] = req.title
    if "priority" in fields and req.priority is not None:
        kwargs["priority"] = req.priority
    if "parent" in fields:
        kwargs["parent"] = req.parent
    if "body" in fields and req.body is not None:
        kwargs["body"] = req.body

    _apply_list_diff(
        kwargs,
        "tags",
        "add_tag",
        "remove_tag",
        (task.tags if task is not None else []) or [],
        req.tags if "tags" in fields else None,
    )
    _apply_list_diff(
        kwargs,
        "depends_on",
        "add_dep",
        "remove_dep",
        (task.depends_on if task is not None else []) or [],
        req.depends_on if "depends_on" in fields else None,
    )

    if "block_reason" in fields:
        kwargs["block_reason"] = req.block_reason
        _apply_block_kwargs(
            kwargs,
            (task.tags if task is not None else []) or [],
            req.block_reason,
        )

    return kwargs


def _apply_list_diff(
    kwargs: dict[str, Any],
    _field: str,
    add_key: str,
    remove_key: str,
    current: list[Any],
    desired: list[Any] | None,
) -> None:
    """Apply full-replacement list diff into kwargs if desired is not None."""
    if desired is None:
        return
    current_set = set(current)
    desired_set = set(desired)
    add = list(desired_set - current_set)
    remove = list(current_set - desired_set)
    if add:
        kwargs[add_key] = add
    if remove:
        kwargs[remove_key] = remove


def _apply_block_kwargs(
    kwargs: dict[str, Any],
    current_tags: list[str],
    block_reason: str | None,
) -> None:
    """Enforce D21 block:user lifecycle and resolve tag-diff conflicts."""
    if not block_reason:
        _remove_tag_op(kwargs, "add_tag", "block:user")
        if "block:user" in current_tags:
            _add_tag_op(kwargs, "remove_tag", "block:user")
        return

    _remove_tag_op(kwargs, "remove_tag", "block:user")
    if "block:user" not in current_tags:
        _add_tag_op(kwargs, "add_tag", "block:user")


def _add_tag_op(kwargs: dict[str, Any], key: str, tag: str) -> None:
    """Add a tag operation without duplicating entries."""
    values = [value for value in kwargs.get(key, []) if value != tag]
    values.append(tag)
    kwargs[key] = values


def _remove_tag_op(kwargs: dict[str, Any], key: str, tag: str) -> None:
    """Remove a tag operation and clear empty operation lists."""
    values = [value for value in kwargs.get(key, []) if value != tag]
    if values:
        kwargs[key] = values
    else:
        kwargs.pop(key, None)


@router.post("/tasks/{task_id}/edit", response_model=SingleTaskResponse)
def edit_task(task_id: int, req: EditRequest, view: _View) -> SingleTaskResponse:
    """Edit allowlisted task fields with D9 optimistic-lock check."""
    task = None
    fields = req.model_fields_set
    if "tags" in fields or "depends_on" in fields or "block_reason" in fields:
        try:
            task = view.show_task(task_id)
        except NotFoundError:
            raise NotFoundError(
                code="ERR_NOT_FOUND",
                user_message=f"Task {task_id} not found",
            ) from None

    kwargs = _build_edit_kwargs(req, task)
    if not kwargs:
        raise ValidationError(
            code="ERR_NO_OP",
            user_message="No editable fields provided",
        )
    updated_task = view.edit_task(
        task_id,
        expected_updated=req.updated,
        **kwargs,
    )
    return _task_to_single(updated_task)


@router.post("/tasks/{task_id}/release", response_model=SingleTaskResponse)
def release_task(task_id: int, req: ReleaseRequest, view: _View) -> SingleTaskResponse:
    """Release claim on a task. 409 if task is not currently claimed."""
    try:
        task = view.show_task(task_id)
    except (FileNotFoundError, NotFoundError):
        raise NotFoundError(
            code="ERR_NOT_FOUND",
            user_message=f"Task {task_id} not found",
        ) from None

    if not task.claimed:
        raise ConcurrencyError(
            code="ERR_NOT_CLAIMED",
            user_message=f"Task {task_id} is not currently claimed",
        )

    updated_task = view.release_task(task_id, expected_updated=req.updated)

    return _task_to_single(updated_task)


@router.post("/tasks/sweep", response_model=list[int])
def sweep_tasks(view: _View) -> list[int]:
    """Release expired claims and return released task IDs."""
    return view.sweep()


@router.post("/tasks/cleanup", response_model=CleanupResult)
def cleanup_tasks(view: _View) -> CleanupResult:
    """Run maintenance cleanup and return released, archived, and skipped items."""
    return view.cleanup()


@router.post("/tasks/scan", response_model=list[dict[str, Any]])
def scan_corruption(view: _View) -> list[dict[str, Any]]:
    """Run read-only corruption scan for tasks and archive directories."""
    return [_serialize_scan_item(item) for item in view.scan_corruption()]


@router.post("/tasks/repair", response_model=list[RepairOutcome])
def repair_storage(view: _View) -> list[RepairOutcome]:
    """Run storage repair and return one outcome per affected file."""
    return view.repair_storage()


@router.post("/tasks/compact-activity", response_model=ActivityCompactionResult)
def compact_activity(view: _View) -> ActivityCompactionResult:
    """Compact activity log and return byte and record deltas."""
    return view.compact_activity()
