"""The design pack's Settings section and the Maintenance overview (TD-101, TD-113): reads, and the one update start.

The overview only links each maintenance action to where it lives and shows its last run where Delivery keeps one.
"""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next.design_packs import design_pack, pack_update
from owlbear_delivery_next.pack_runs import pack_job

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.state_store.store import Store

PAUSED = "Delivery is paused: press Resume on the Changes page, then continue the update"


class AnswerBody(BaseModel):
    """The owner's answer to one open question of a waiting pack update (TD-193, TD-256)."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(max_length=200)
    option: str = Field(max_length=40)
    note: str = Field(default="", max_length=2000)


def pack(job: pack_job.Job) -> dict[str, Any]:
    """The active pack, the last notice of upstream, and the update's current or last run; never online."""
    pins = design_pack.manifest()
    return {
        "pack": pins["pack"],
        "upstream": pins["upstream"]["tag"],
        "identity": design_pack.identity(),
        "status": design_pack.status(),
        "notice": pack_update.said(pack_update.notice(refresh=False)),
        "update": job.read(),
    }


def memory_last(store: Store) -> dict[str, Any] | None:
    """The owner's last memory action, from the shared repository's history; none without one."""
    if store.shared is None:
        return None
    marker = f"memory {store.name}: "  # the subject memory_routes commits each action with
    args = ["log", "-1", "--format=%cI%x00%s", "--fixed-strings", f"--grep={marker}", "--"]
    try:
        done = subprocess.run(  # noqa: S603
            ["git", *args, str(store.shared.memory_path(store.name))],  # noqa: S607
            cwd=store.shared.root, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"}, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=10, check=False,
        )  # fmt: skip
    except OSError, subprocess.TimeoutExpired:
        return None
    at, _, subject = done.stdout.strip().partition("\0")
    return {"state": subject.removeprefix(marker), "ended_at": at} if done.returncode == 0 and at else None


def overview(store: Store) -> list[dict[str, Any]]:
    """Each maintenance action: where it lives, whether it is built, and its last run where Delivery keeps one."""
    return [
        {"name": "Memory curation", "where": "Memory", "href": "/memory", "built": True, "recorded": True,
         "last": memory_last(store), "note": "Approve, edit, resolve or delete agent memory entries."},
        {"name": "Design pack update", "where": "Settings", "href": "/config#pack", "built": True,
         "recorded": True, "last": pack_job.last(store),
         "note": "Detector and design skills together: diff, golden pages, replay, challenger, then commit and push."},
        {"name": "Engine update", "where": "Settings", "href": None, "built": False, "recorded": False,
         "last": None, "note": "Not built yet."},
        {"name": "Review Tests", "where": "Project action", "href": None, "built": False, "recorded": False,
         "last": None, "note": "Not built yet (TD-112)."},
        {"name": "Backlog triage", "where": "Backlog", "href": "/backlog", "built": True, "recorded": False,
         "last": None, "note": "Triage items in the Backlog tab; Delivery keeps no run record for it."},
        {"name": "Explore experiment", "where": "Report", "href": None, "built": False, "recorded": False,
         "last": None, "note": "Pilot run 2026-10-16 under a proven credit limit: explore never started "
                                 "unprompted in three pairs, so it tested availability only. The setting stays off."},
    ]  # fmt: skip


def router(store: Store, job: pack_job.Job, paused: Callable[[], bool] = lambda: False) -> APIRouter:
    """The design pack and maintenance routes; the caller adds the token check. An update waits for Resume."""
    routes = APIRouter()

    def held() -> None:
        if paused():
            raise HTTPException(409, PAUSED)

    @routes.get("/design-pack")
    def read() -> dict[str, Any]:
        return pack(job)

    @routes.get("/design-pack/update")
    def update_state() -> dict[str, Any]:
        return job.read()

    @routes.post("/design-pack/update")
    def update() -> dict[str, Any]:
        held()
        try:
            return job.start()
        except pack_job.Busy as exc:
            raise HTTPException(409, str(exc)) from exc

    _answers(routes, job, held)

    @routes.get("/maintenance")
    def maintenance() -> list[dict[str, Any]]:
        return overview(store)

    return routes


def _answers(routes: APIRouter, job: pack_job.Job, held: Callable[[], None]) -> None:
    """The owner's answers to a waiting update (TD-193, TD-256), and its discard."""

    @routes.post("/design-pack/update/answer")
    def answer(body: AnswerBody) -> dict[str, Any]:
        held()  # an answer continues the update's sessions
        try:
            return job.answer(body.question, body.option, body.note)
        except (pack_job.Stale, pack_job.Busy) as exc:
            raise HTTPException(409, str(exc)) from exc
        except pack_job.Refused as exc:
            raise HTTPException(422, str(exc)) from exc

    @routes.post("/design-pack/update/discard")
    def discard() -> dict[str, Any]:
        try:
            return job.discard()
        except pack_job.Stale as exc:
            raise HTTPException(409, str(exc)) from exc
