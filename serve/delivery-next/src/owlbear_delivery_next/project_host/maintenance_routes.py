"""The Maintenance sessions: unknown work and its owner's explicit reboot recovery (OPS-03, OPS-06).

Beside them, the machine's Impeccable and PDS updates as the Updates pages show them, the same in every project
(``pack_overview``): the machine host serves them without a project, so the pages read them with none chosen.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from owlbear_delivery_next.project_host import decision_routes, pack_overview

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
    """Read the pinned pack and held sessions. Only the owner can recover a session."""
    routes = APIRouter()

    @routes.get("/maintenance/pack")
    def pack() -> dict[str, Any]:
        return pack_overview.pinned()

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
