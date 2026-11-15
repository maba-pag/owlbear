"""Project doc and agent audits: owner-started maintenance, their last report and publication recovery."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next.audit_runs import job as audit_job
from owlbear_delivery_next.project_host import decision_routes, pack_routes, pds_routes, session_slots
from owlbear_delivery_next.project_host.admission import admitted

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.impeccable_runs.pack_job import Job
    from owlbear_delivery_next.project_host.host import Host
    from owlbear_delivery_next.state_store.store import Store


class StartBody(BaseModel):
    """The note as typed and explicit consent to replace an unfinished report."""

    model_config = ConfigDict(extra="forbid")

    note: str = Field(default="", max_length=2000)
    drop_unpublished: bool = False


def router(audits: audit_job.Audits, host: Host) -> APIRouter:
    """Offer the project's audits; only the owner on the page starts or continues publication."""
    routes = APIRouter()

    @routes.get("/maintenance/audits")
    def read() -> dict[str, Any]:
        return audits.offer()

    @routes.post("/maintenance/audits/{audit}", dependencies=[Depends(decision_routes.owner)])
    def start(audit: str, body: StartBody) -> dict[str, Any]:
        try:
            with admitted(host):
                return audits.start(audit, body.note, drop_unpublished=body.drop_unpublished)
        except audit_job.Busy as exc:
            raise HTTPException(409, str(exc)) from exc

    @routes.post("/maintenance/audits/{audit}/publish", dependencies=[Depends(decision_routes.owner)])
    def publish(audit: str) -> dict[str, Any]:
        try:
            with admitted(host):
                return audits.publish(audit)
        except audit_job.Busy as exc:
            raise HTTPException(409, str(exc)) from exc

    return routes


def bind(routes: APIRouter, store: Store, host: Host, job: Job, opening: Callable[[], bool]) -> Callable[[], list[str]]:
    """Compose the project's maintenance actions and the work its stop waits for."""
    routes.include_router(pack_routes.router(store, job, lambda: admitted(host), host))
    pds = session_slots.pds(host, store)
    routes.include_router(pds_routes.router(*pds, admitted=lambda: admitted(host)))
    audits = session_slots.audits(host, store)
    routes.include_router(router(audits, host))

    def busy() -> list[str]:
        return [
            *(["a shaping chat opening"] if opening() else []),
            *session_slots.busy(job, *pds),
            *(["a project audit"] if audits.busy() else []),
        ]

    return busy
