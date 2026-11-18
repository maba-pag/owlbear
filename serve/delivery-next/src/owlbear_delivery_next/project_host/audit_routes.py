"""Project audits: shared page/chat admission, their last report and publication recovery."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next.audit_runs import job as audit_job
from owlbear_delivery_next.audit_runs import suppression_verdicts
from owlbear_delivery_next.project_host import decision_routes, pack_routes, pds_routes, session_slots
from owlbear_delivery_next.project_host.admission import admitted

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.impeccable_runs.pack_job import Job
    from owlbear_delivery_next.project_host.host import Host, HostRecord
    from owlbear_delivery_next.state_store.store import Store


class NoteBody(BaseModel):
    """Chat supplies a note, never consent to discard an unpublished report."""

    model_config = ConfigDict(extra="forbid")

    note: str = Field(default="", max_length=2000)


class StartBody(NoteBody):
    """The page's note and explicit consent to replace one exact unfinished report."""

    discard_report: str = Field(default="", max_length=32)


class VerdictBody(BaseModel):
    """An owner confirmation of one exact displayed verdict group."""

    model_config = ConfigDict(extra="forbid")

    id: str
    action: Literal["again", "accept"]


def maintenance_page(rec: HostRecord) -> str | None:
    """The Maintenance address for this host's project, or its machine overview."""
    if not rec.token:
        return None
    return f"{rec.url}maintenance{f'?project={rec.project}' if rec.project else ''}#token={rec.token}"


def start_audit(audits: audit_job.Audits, host: Host, audit: str, body: StartBody) -> dict[str, Any]:
    """Both triggers use the same host's admission and its already-bound Audits object."""
    try:
        with admitted(host):
            return audits.start(audit, body.note, discard_report=body.discard_report)
    except (audit_job.AuditBusyError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


def router(audits: audit_job.Audits, host: Host) -> APIRouter:
    """Offer the project's audits; only the page discards a report or continues publication."""
    routes = APIRouter()

    @routes.get("/maintenance/audits")
    def read() -> dict[str, Any]:
        return audits.offer()

    @routes.get("/maintenance/audits/suppressions/verdicts")
    def verdicts() -> dict[str, Any]:
        return {"verdicts": suppression_verdicts.read(audits)}

    @routes.post("/maintenance/audits/suppressions/verdicts", dependencies=[Depends(decision_routes.owner)])
    def verdict(body: VerdictBody) -> dict[str, Any]:
        try:
            with admitted(host):
                return {"verdicts": suppression_verdicts.change(audits, body.id, body.action)}
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @routes.post("/maintenance/audits/{audit}", dependencies=[Depends(decision_routes.owner)])
    def start(audit: str, body: StartBody) -> dict[str, Any]:
        return start_audit(audits, host, audit, body)

    @routes.post("/chat/audits/code")
    def chat_start(body: NoteBody) -> JSONResponse:
        page = maintenance_page(host.record)
        try:
            state = start_audit(audits, host, "code", StartBody(note=body.note))
        except HTTPException as exc:
            return JSONResponse(
                {"started": False, "error": exc.detail, "maintenance_page": page}, status_code=exc.status_code
            )
        return JSONResponse(
            {
                "started": True,
                "id": state["id"],
                "state": state["state"],
                "initial_commit": state["commit"],
                "maintenance_page": page,
            }
        )

    @routes.post("/maintenance/audits/{audit}/publish", dependencies=[Depends(decision_routes.owner)])
    def publish(audit: str) -> dict[str, Any]:
        try:
            with admitted(host):
                return audits.publish(audit)
        except audit_job.AuditBusyError as exc:
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
