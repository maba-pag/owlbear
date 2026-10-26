"""The Maintenance sessions: unknown work and its owner's explicit reboot recovery (OPS-03, OPS-06)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from owlbear_delivery_next.project_host import decision_routes

if TYPE_CHECKING:
    from owlbear_delivery_next.local_system import maintenance


class Holder(Protocol):
    """A project host or the machine: whichever owns the maintenance ledger it reads and recovers from."""

    maintenance: maintenance.Maintenance | None


class RecoverBody(BaseModel):
    """The owner's confirmation that the computer rebooted since the held session failed."""

    model_config = ConfigDict(extra="forbid")

    rebooted: bool


def router(host: Holder | None) -> APIRouter:
    """Held sessions and their recovery; a host without maintenance has none to show.

    Recovery is the owner's act on the page: a chat tool's call is refused, as the decisions' writes are.
    """
    routes = APIRouter()

    @routes.get("/maintenance/sessions")
    def sessions() -> dict[str, list[dict[str, Any]]]:
        return _bound(host).read()

    @routes.post("/maintenance/sessions/{ident}/recover", dependencies=[Depends(decision_routes.owner)])
    def recover(ident: str, body: RecoverBody) -> dict[str, list[dict[str, Any]]]:
        manager = _bound(host)
        if body.rebooted is not True:
            raise HTTPException(400, "confirm the computer rebooted since this session")
        try:
            return manager.recover(ident, rebooted=True)
        except (LookupError, ValueError) as exc:
            raise HTTPException(409, str(exc)) from exc

    return routes


def _bound(host: Holder | None) -> maintenance.Maintenance:
    manager = host.maintenance if host is not None else None
    if manager is None:
        raise HTTPException(503, "OwlBear is not running; start it to see maintenance sessions")
    return manager
