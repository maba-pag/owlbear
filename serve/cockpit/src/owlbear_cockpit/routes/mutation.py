"""Cockpit mutation API routes — move, edit, release."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from owlbear_cockpit import adapter
from owlbear_cockpit.deps import get_engine
from owlbear_cockpit.models import TaskDetailOut

if TYPE_CHECKING:
    from owlbear_kanban import KanbanEngine

router = APIRouter()

_Engine = Annotated["KanbanEngine", Depends(get_engine)]


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class MoveRequest(BaseModel):
    """Request body for POST /tasks/{id}/move."""

    model_config = ConfigDict(extra="forbid")

    status: str


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task_to_detail(task: Any) -> TaskDetailOut:  # noqa: ANN401
    return TaskDetailOut(
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
        claimed_by=task.claimed_by,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/tasks/{task_id}/move", response_model=TaskDetailOut)
def move_task(task_id: int, req: MoveRequest, engine: _Engine) -> TaskDetailOut:
    """Move task to a new status. Validates against valid_transitions."""
    try:
        task = engine.show_task(str(task_id))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found") from None

    transitions = adapter.valid_transitions(engine, task.status)
    if req.status not in transitions:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot move from '{task.status}' to '{req.status}'",
        )

    updated_task = engine.move_task(str(task_id), req.status)
    return _task_to_detail(updated_task)


def _build_edit_kwargs(req: EditRequest, task: Any) -> dict[str, Any]:  # noqa: ANN401
    """Translate EditRequest fields into engine.edit_task keyword arguments."""
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
        "add_tags",
        "remove_tags",
        task.tags or [],
        req.tags if "tags" in fields else None,
    )
    _apply_list_diff(
        kwargs,
        "depends_on",
        "add_deps",
        "remove_deps",
        task.depends_on or [],
        req.depends_on if "depends_on" in fields else None,
    )

    if "block_reason" in fields:
        _apply_block_kwargs(kwargs, req, task)

    return kwargs


def _apply_block_kwargs(kwargs: dict[str, Any], req: EditRequest, task: Any) -> None:  # noqa: ANN401
    """Apply block_reason and block:user tag changes to kwargs."""
    current_tags = set(task.tags or [])
    if req.block_reason is not None:
        kwargs["blocked"] = True
        kwargs["block_reason"] = req.block_reason
        if "block:user" not in current_tags:
            add_tags: list[str] = kwargs.get("add_tags") or []
            if "block:user" not in add_tags:
                kwargs["add_tags"] = [*add_tags, "block:user"]
    else:
        kwargs["blocked"] = False
        if "block:user" in current_tags:
            remove_tags: list[str] = kwargs.get("remove_tags") or []
            if "block:user" not in remove_tags:
                kwargs["remove_tags"] = [*remove_tags, "block:user"]


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


@router.post("/tasks/{task_id}/edit", response_model=TaskDetailOut)
def edit_task(task_id: int, req: EditRequest, engine: _Engine) -> TaskDetailOut:
    """Edit allowlisted task fields with D9 optimistic-lock check."""
    try:
        task = engine.show_task(str(task_id))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found") from None

    if req.updated != str(task.updated):
        raise HTTPException(
            status_code=409,
            detail="Task was modified since your last load (stale snapshot)",
        )

    kwargs = _build_edit_kwargs(req, task)
    if not kwargs:
        raise HTTPException(status_code=422, detail="No editable fields provided")
    try:
        updated_task = engine.edit_task(str(task_id), **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _task_to_detail(updated_task)


@router.post("/tasks/{task_id}/release", response_model=TaskDetailOut)
def release_task(task_id: int, engine: _Engine) -> TaskDetailOut:
    """Release claim on a task. 409 if task is not currently claimed."""
    try:
        task = engine.show_task(str(task_id))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found") from None

    if not task.claimed_by:
        raise HTTPException(status_code=409, detail=f"Task {task_id} is not currently claimed")

    updated_task = engine.release_task(str(task_id))
    return _task_to_detail(updated_task)
