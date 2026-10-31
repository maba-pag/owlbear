"""The test review's Maintenance routes (TD-370, TD-371): what its dialog offers, and the owner's Start."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next.state_store import work_block
from owlbear_delivery_next.workflow_steps import curation

if TYPE_CHECKING:
    from owlbear_delivery_next.project_host.host import Host
    from owlbear_delivery_next.state_store.store import Store


class StartBody(BaseModel):
    """The packages whose tests the owner chose."""

    model_config = ConfigDict(extra="forbid")

    packages: list[str] = Field(max_length=200)


def router(store: Store, host: Host) -> APIRouter:
    """The dialog's offer and the start; a start while OwlBear stops is refused."""
    routes = APIRouter()

    @routes.get("/maintenance/test-review")
    def offer() -> dict[str, Any]:
        return curation.offer(store, host.repo)

    @routes.post("/maintenance/test-review")
    def start(body: StartBody) -> dict[str, str]:
        if host.draining():
            raise HTTPException(409, "OwlBear stops once the running steps end; press Resume to cancel")
        if why := work_block.of_store(store).text():  # its start is the owner's work for this project (#808)
            raise HTTPException(409, why)
        try:
            c = curation.start(store, host.repo, body.packages, datetime.now(UTC))
        except curation.StartError as exc:
            raise HTTPException(exc.status, str(exc)) from exc
        host.wake.set()
        return {"slug": c.slug, "handle": c.handle}

    return routes
