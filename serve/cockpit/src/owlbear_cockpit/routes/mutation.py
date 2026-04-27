"""Cockpit mutation API routes — move, edit, release."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from owlbear_cockpit import adapter
from owlbear_cockpit.deps import get_view
from owlbear_kanban.engine import CockpitView
from owlbear_kanban.errors import ConcurrencyError, ConfigError, NotFoundError, ValidationError
from owlbear_kanban.models import SingleTaskResponse

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


class EditRequest(BaseModel):
    """Request body for POST /tasks/{id}/edit.

    Only allowlisted fields accepted. `extra="forbid"` rejects `status`,
    `blocked`, and any other non-allowlisted fields with 422.
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/tasks/{task_id}/move", response_model=SingleTaskResponse)
def move_task(task_id: int, req: MoveRequest, view: _View) -> SingleTaskResponse:
    """Move task to a new status. Validates OCC token then valid_transitions."""
    try:
        task = view.engine.show_task(str(task_id))
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Task {task_id} not found"
        ) from None

    if req.updated != str(task.updated):
        raise HTTPException(
            status_code=409,
            detail="Task was modified since your last load (stale snapshot)",
        )

    transitions = adapter.valid_transitions(view.engine, task.status)
    if req.status not in transitions:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot move from '{task.status}' to '{req.status}'",
        )

    try:
        updated_task = view.move_task(
            task_id,
            req.status,
            expected_updated=req.updated,
        )
    except NotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Task {task_id} not found"
        ) from None
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.user_message) from exc
    except ConcurrencyError:
        raise HTTPException(
            status_code=409,
            detail="Task was modified since your last load (stale snapshot)",
        ) from None
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


@router.post("/tasks/{task_id}/edit", response_model=SingleTaskResponse)
def edit_task(task_id: int, req: EditRequest, view: _View) -> SingleTaskResponse:
    """Edit allowlisted task fields with D9 optimistic-lock check."""
    task = None
    fields = req.model_fields_set
    if "tags" in fields or "depends_on" in fields:
        try:
            task = view.show_task(task_id)
        except NotFoundError:
            raise HTTPException(
                status_code=404, detail=f"Task {task_id} not found"
            ) from None

    kwargs = _build_edit_kwargs(req, task)
    if not kwargs:
        raise HTTPException(status_code=422, detail="No editable fields provided")
    try:
        updated_task = view.edit_task(
            task_id,
            expected_updated=req.updated,
            **kwargs,
        )
    except NotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Task {task_id} not found"
        ) from None
    except ConcurrencyError:
        raise HTTPException(
            status_code=409,
            detail="Task was modified since your last load (stale snapshot)",
        ) from None
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.user_message) from exc
    except ConfigError:
        raise HTTPException(status_code=500, detail="Invalid board configuration") from None
    return _task_to_single(updated_task)


@router.post("/tasks/{task_id}/release", response_model=SingleTaskResponse)
def release_task(task_id: int, req: ReleaseRequest, view: _View) -> SingleTaskResponse:
    """Release claim on a task. 409 if task is not currently claimed."""
    try:
        task = view.show_task(task_id)
    except (FileNotFoundError, NotFoundError):
        raise HTTPException(
            status_code=404, detail=f"Task {task_id} not found"
        ) from None

    if not task.claimed:
        raise HTTPException(
            status_code=409, detail=f"Task {task_id} is not currently claimed"
        )

    try:
        updated_task = view.release_task(task_id, expected_updated=req.updated)
    except NotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Task {task_id} not found"
        ) from None
    except ConcurrencyError:
        raise HTTPException(
            status_code=409,
            detail="Task was modified since your last load (stale snapshot)",
        ) from None

    return _task_to_single(updated_task)


@router.post("/tasks/sweep", response_model=list[int])
def sweep_tasks(view: _View) -> list[int]:
    """Release expired claims and return released task IDs."""
    return view.sweep()
