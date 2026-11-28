"""Machine update routes shared by PDS and Impeccable, and their companion actions."""

from __future__ import annotations

import logging
import subprocess
from contextlib import ExitStack, contextmanager
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.impeccable import pack_files, pack_update
from owlbear_delivery_next.impeccable.detector import DetectorError
from owlbear_delivery_next.impeccable_runs import pack_candidate, pack_job, pack_progress, pack_replay
from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.pds_runs import hand_audit
from owlbear_delivery_next.project_host import decision_routes, pack_overview
from owlbear_delivery_next.state_store import pds_run_record

if TYPE_CHECKING:
    from collections.abc import Iterator

    from owlbear_delivery_next.machine_host.update_jobs import Updates

_log = logging.getLogger(__name__)
OWNER = [Depends(decision_routes.owner)]
REPLAY_FAILURES = (
    pack_files.PackError,
    DetectorError,
    data_repo.DataRepoError,
    subprocess.CalledProcessError,
    OSError,
    ValueError,
)


class AnswerBody(BaseModel):
    """The owner's answer to one open question of a waiting update."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(max_length=200)
    option: str = Field(max_length=40)
    note: str = Field(default="", max_length=2000)


class DiscardBody(BaseModel):
    """The run shown in the owner's discard confirmation."""

    model_config = ConfigDict(extra="forbid")

    run: str = Field(max_length=200)


@contextmanager
def admitted(updates: Updates) -> Iterator[None]:
    """Return a refusal rather than starting work behind the machine's fence."""
    machine = updates.machine
    with machine.lock:
        if why := updates.refusal():
            stopping = machine.stopping.is_set() or machine.updating
            raise HTTPException(503 if stopping else 409, why)
        yield


def audit_routes(updates: Updates) -> APIRouter:
    """Read or start the hand audit of the installed pages."""
    routes = APIRouter()
    hand = updates.hand

    @routes.get("/pds/audit")
    def audit_state() -> dict[str, Any]:
        return hand.read()

    @routes.post("/pds/audit", dependencies=OWNER)
    def audit() -> dict[str, Any]:
        try:
            with admitted(updates):
                return hand.start()
        except hand_audit.Busy as exc:
            raise HTTPException(409, str(exc)) from exc

    return routes


def router(updates: Updates, job: pack_job.Job, prefix: str) -> APIRouter:
    """Read, start, answer or discard either kind of machine update."""
    routes = APIRouter()
    path = f"{prefix}/update"

    @routes.get(path)
    def update_state() -> dict[str, Any]:
        return job.read()

    @routes.post(path, dependencies=OWNER)
    def update() -> dict[str, Any]:
        try:
            with admitted(updates):
                return job.start()
        except pack_job.Busy as exc:
            raise HTTPException(409, str(exc)) from exc

    @routes.post(f"{path}/answer", dependencies=OWNER)
    def answer(body: AnswerBody) -> dict[str, Any]:
        try:
            with admitted(updates):
                return job.answer(body.question, body.option, body.note)
        except (pack_job.Stale, pack_job.Busy) as exc:
            raise HTTPException(409, str(exc)) from exc
        except pack_job.Refused as exc:
            raise HTTPException(422, str(exc)) from exc

    @routes.post(f"{path}/discard", dependencies=OWNER)
    def discard(body: DiscardBody) -> dict[str, Any]:
        try:
            return job.discard(body.run)
        except pack_job.Stale as exc:
            raise HTTPException(409, str(exc)) from exc

    return routes


def pack(updates: Updates) -> dict[str, Any]:
    """The active pack, its upstream notice and its update's last run."""
    pins = pack_files.manifest()
    return {
        "pack": pins["pack"], "upstream": pins["upstream"]["tag"], "identity": pack_files.identity(),
        "status": pack_files.status(), "notice": pack_update.said(pack_update.notice(refresh=False)),
        "update": updates.pack.read(), "machine": pack_job.running_for(),
    }  # fmt: skip


def replay_routes(updates: Updates) -> APIRouter:
    """Replay OwlBear's decided rounds on the installed pack."""
    routes = APIRouter()
    job = updates.pack

    @routes.post("/impeccable/replay", dependencies=OWNER)
    def replay() -> dict[str, Any]:
        try:
            with ExitStack() as held:
                with admitted(updates):
                    held.enter_context(job.exclusive())
                    job.count_replay(1)
                    held.callback(job.count_replay, -1)
                r = job.live.replay(job.store, None, keep=job.keeps)
        except pack_job.Busy as exc:
            raise HTTPException(409, str(exc)) from exc
        except pack_replay.ReplayError as exc:
            _log.warning("calibration replay refused: %s", exc)
            raise HTTPException(409, str(exc)) from exc
        except REPLAY_FAILURES as exc:
            _log.warning("calibration replay failed: %s", said := failure(exc), exc_info=True)
            raise HTTPException(422, said) from exc
        return {"ok": r.ok, "report": f"calibration replay: {pack_candidate.said_replay(r)}"}

    return routes


def read_routes() -> APIRouter:
    """Read the machine's last update of each kind."""
    routes = APIRouter()

    @routes.get("/maintenance/pack/runs")
    def pack_runs() -> dict[str, Any]:
        return pack_overview.runs()

    @routes.get("/maintenance/pds/runs")
    def pds_runs() -> dict[str, Any]:
        return pack_overview.runs(pds_run_record.read_only, pack_progress.PDS_ACTIONS)

    return routes
