"""A lead chat's decision lookup (TD-456, TD-459): the picker over the folder's and Global decisions in force.

Contracts 1-5 ask and wait in one request. Contract 6 starts the lookup and reads it by its id, so no tool call
outlasts the Copilot client's cut (#972): the start answers at once and the lookup runs after the reply, inside the
same request, so the host counts and waits for it as for the blocking one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Path
from pydantic import BaseModel, ConfigDict, StringConstraints

from owlbear_delivery_next.project_host import impact_routes
from owlbear_delivery_next.workflow_steps import lookup

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.local_system.data_repo import DataRepo
    from owlbear_delivery_next.state_store.store import Store


class LookupBody(BaseModel):
    """A lead chat's question: which decisions govern it."""

    model_config = ConfigDict(extra="forbid")

    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


def router(shared: Callable[[], DataRepo | None], folder: Callable[[], str], store: Store | None) -> APIRouter:
    """The lookup routes over this host's lookups: one at a time (TD-336)."""
    routes = APIRouter(route_class=impact_routes.Quiet)  # a refused question is never echoed (TD-449)
    chats = lookup.Chats()
    settings = store.settings if store else None

    @routes.post("/decisions/lookup")
    def look_up(body: LookupBody) -> dict[str, Any]:
        return chats(shared(), folder(), body.question, settings)

    @routes.post("/decisions/lookups")
    def start(body: LookupBody, tasks: BackgroundTasks) -> dict[str, str]:
        where = shared(), folder()
        lookup_id = chats.start()
        if lookup_id is None:
            raise HTTPException(409, lookup.BUSY)
        tasks.add_task(chats.finish, lookup_id, *where, body.question, settings)
        return {"lookup_id": lookup_id}

    @routes.get("/decisions/lookups/{lookup_id}")
    def read(lookup_id: Annotated[str, Path(max_length=64)]) -> dict[str, Any]:
        said = chats.read(lookup_id)
        if said is None:
            raise HTTPException(404, lookup.GONE.format(lookup_id))
        return said

    return routes
