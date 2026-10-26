"""The owner's routes for an interrupted decision batch: a diagnosis, then an explicit finish or abandon.

Each action names the generation the owner saw and must be confirmed. A corrupt journal shows its diagnosis and
refuses both actions; nothing here clears the journal on its own.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, StringConstraints

from owlbear_delivery_next.project_host import impact_routes
from owlbear_delivery_next.state_store import decision_batch, decision_recovery, decision_store

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.local_system.data_repo import DataRepo

type Shared = Callable[[], DataRepo | None]

NOT_CONFIRMED = "recovery needs the owner's explicit confirmation"


class RecoveryBody(BaseModel):
    """The generation the owner saw, and the owner's explicit confirmation of the finish or abandon."""

    generation: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{8,64}$")]
    confirmed: bool = False
    reason: Annotated[str, Field(max_length=300)] = ""


def diagnosis(shared: DataRepo) -> dict[str, Any]:
    """The interrupted batch the owner must decide on, or the journal's fault; never a success."""
    try:
        batch = decision_batch.pending(shared)
    except decision_batch.JournalError as exc:
        return {"interrupted": True, "corrupt": True, "diagnosis": str(exc)[:600], "generation": ""}
    if batch is None:
        return {"interrupted": False, "corrupt": False, "diagnosis": "", "generation": ""}
    return {
        "interrupted": True,
        "corrupt": False,
        "generation": batch.generation,
        "project": batch.project,
        "ids": list(batch.ids),
        "message": batch.message,
        "head": batch.head,
        "diagnosis": "a decision batch was interrupted; finish publishes it, abandon restores the files",
    }


def _run(action: Callable[[], Any], body: RecoveryBody) -> dict[str, Any]:
    if not body.confirmed:
        raise HTTPException(422, NOT_CONFIRMED)
    try:
        out = action()
    except decision_store.DecisionsUnavailable as exc:
        raise HTTPException(409, f"{exc} ({exc.action})") from exc
    return {"done": out.done, "notice": out.notice, "generation": out.generation}


def router(shared: Shared, owner: list[Any]) -> APIRouter:
    """Mounted by the decision routes; the owner-only dependency is the caller's.

    Its own route class keeps a 422 from echoing what was sent (TD-449): including a router keeps its routes' class.
    """
    routes = APIRouter(route_class=impact_routes.Quiet)

    @routes.get("/decisions/recovery", dependencies=owner)
    def status() -> dict[str, Any]:
        data = shared()
        if data is None:
            return {"interrupted": False, "corrupt": False, "diagnosis": "no shared repository", "generation": ""}
        return diagnosis(data)

    @routes.post("/decisions/recovery/finish", dependencies=owner)
    def finish(body: RecoveryBody) -> dict[str, Any]:
        data = shared()
        if data is None:
            raise HTTPException(409, "no shared repository")
        return _run(lambda: decision_recovery.finish(data, body.generation), body)

    @routes.post("/decisions/recovery/abandon", dependencies=owner)
    def abandon(body: RecoveryBody) -> dict[str, Any]:
        data = shared()
        if data is None:
            raise HTTPException(409, "no shared repository")
        return _run(lambda: decision_recovery.abandon(data, body.generation), body)

    return routes
