"""The PDS routes (#777): the hand audit of the installed pages and the update, started and read on the Updates page."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException

from owlbear_delivery_next.impeccable_runs import pack_job
from owlbear_delivery_next.pds_runs import hand_audit
from owlbear_delivery_next.project_host.pack_routes import AnswerBody  # noqa: TC001 - FastAPI reads it at runtime

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager

    from owlbear_delivery_next.pds_runs.job import Job


def router(
    hand: hand_audit.Hand,
    job: Job | None = None,
    *,
    admitted: Callable[[], AbstractContextManager[None]] = contextlib.nullcontext,
) -> APIRouter:
    """The hand audit's routes, and the update's with its *job*; the caller adds the token check.

    *admitted* refuses a start or an answer once OwlBear stops.
    """
    routes = APIRouter()

    @routes.get("/pds/audit")
    def audit_state() -> dict[str, Any]:
        return hand.read()

    @routes.post("/pds/audit")
    def audit() -> dict[str, Any]:
        try:
            with admitted():
                return hand.start()
        except hand_audit.Busy as exc:
            raise HTTPException(409, str(exc)) from exc

    if job is not None:
        _update(routes, job, admitted)
    return routes


def _update(routes: APIRouter, job: Job, admitted: Callable[[], AbstractContextManager[None]]) -> None:
    """The update: its state, its start, the owner's answers and its discard."""

    @routes.get("/pds/update")
    def update_state() -> dict[str, Any]:
        return job.read()

    @routes.post("/pds/update")
    def update() -> dict[str, Any]:
        try:
            with admitted():
                return job.start()
        except pack_job.Busy as exc:
            raise HTTPException(409, str(exc)) from exc

    @routes.post("/pds/update/answer")
    def answer(body: AnswerBody) -> dict[str, Any]:
        try:
            with admitted():  # an answer continues the update's sessions
                return job.answer(body.question, body.option, body.note)
        except (pack_job.Stale, pack_job.Busy) as exc:
            raise HTTPException(409, str(exc)) from exc
        except pack_job.Refused as exc:
            raise HTTPException(422, str(exc)) from exc

    @routes.post("/pds/update/discard")
    def discard() -> dict[str, Any]:
        try:
            return job.discard()
        except pack_job.Stale as exc:
            raise HTTPException(409, str(exc)) from exc
