"""The Impeccable update's routes and the Maintenance overview (TD-101, TD-113): reads, and the one update start.

The overview only links each maintenance action to where it lives and shows its last run where Delivery keeps one;
beside it, each role's use of built-in subagents (TD-376).
"""

from __future__ import annotations

import contextlib
import os
import subprocess
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next.impeccable import pack_files, pack_update
from owlbear_delivery_next.impeccable.detector import DetectorError
from owlbear_delivery_next.impeccable_runs import pack_candidate, pack_job, pack_replay
from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.project_host import curation_routes, maintenance_routes
from owlbear_delivery_next.settings import roles

OLD = "/design-pack"  # the routes' prefix before the Impeccable rename
REPLAY_FAILURES = (
    pack_files.PackError,
    DetectorError,
    data_repo.DataRepoError,
    subprocess.CalledProcessError,
    OSError,
    ValueError,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager

    from owlbear_delivery_next.project_host.host import Host
    from owlbear_delivery_next.state_store.store import Store


class AnswerBody(BaseModel):
    """The owner's answer to one open question of a waiting pack update (TD-193, TD-256)."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(max_length=200)
    option: str = Field(max_length=40)
    note: str = Field(default="", max_length=2000)


def pack(job: pack_job.Job) -> dict[str, Any]:
    """The active pack, the last notice of upstream, and the update's current or last run; never online."""
    pins = pack_files.manifest()
    return {
        "pack": pins["pack"],
        "upstream": pins["upstream"]["tag"],
        "identity": pack_files.identity(),
        "status": pack_files.status(),
        "notice": pack_update.said(pack_update.notice(refresh=False)),
        "update": job.read(),
        "machine": pack_job.running_for(),  # TD-290: an update any project runs on this machine
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
        {"name": "Impeccable update", "where": "Maintenance", "href": "#owlbear", "built": True,
         "recorded": True, "last": pack_job.last(store),
         "note": "Detector and design skills together: diff, golden pages, replay, challenger, then commit and push. "
                 "One runs at a time on this machine; the OwlBear section shows it in every project."},
        {"name": "Engine update", "where": "Maintenance", "href": "#owlbear", "built": True,
         "recorded": False, "last": None,
         "note": "OwlBear updates itself when idle, announced on open pages; Update now in the OwlBear section "
                 "updates at once. When it updates is set in Settings, This machine."},
        {"name": "Review Tests", "where": "Maintenance", "href": "#tests", "built": True, "recorded": False,
         "last": None, "note": "Reviewers judge shares of the tests; a curator applies what holds in a Change."},
        {"name": "Backlog triage", "where": "Backlog", "href": "/backlog", "built": True, "recorded": False,
         "last": None, "note": "Triage items in the Backlog tab; Delivery keeps no run record for it."},
    ]  # fmt: skip


def _ran(event: dict[str, Any]) -> list[dict[str, Any]]:
    """A step event's subagent records; anything stored that is not one is left out."""
    ran = event.get("subagents")
    return [s for s in ran if isinstance(s, dict)] if isinstance(ran, list) else []


def subagent_use(store: Store) -> list[dict[str, Any]]:
    """Per role, its steps and the built-in subagents they started, from the step events each Change keeps (TD-376).

    A step logged twice (held, then decided) counts once: as the last agent's kind or label logged for it, with its
    subagents from the last event that recorded any, since a decided held result is logged again without them. Only
    an agent's steps count; a merge or cleanup runs none, and kinds since renamed are left out.
    """
    steps: dict[tuple[str, str], tuple[str, list[dict[str, Any]]]] = {}
    for slug in store.slugs():
        for e in (e for e in store.events(slug) if e.get("event") == "step"):
            key, kind = (slug, str(e.get("session") or id(e))), str(e.get("label") or e.get("kind", ""))
            before = steps.get(key, ("", []))
            steps[key] = kind if kind in roles.SESSIONS else before[0], _ran(e) or before[1]
    use: dict[str, dict[str, Any]] = {}
    for kind, ran in steps.values():
        if kind not in roles.SESSIONS:
            continue
        role = roles.SESSIONS[kind]
        r = use.setdefault(role, {"role": role, "steps": 0, "with": 0, "runs": 0, "credits": 0.0, "unknown": 0,
                                  "agents": {}})  # fmt: skip
        r["steps"], r["with"], r["runs"] = r["steps"] + 1, r["with"] + bool(ran), r["runs"] + len(ran)
        for s in ran:
            name = str(s.get("agent") or "unnamed")
            r["agents"][name] = r["agents"].get(name, 0) + 1
            spent = s.get("credits")
            if s.get("credits_known", True) is True and type(spent) in {int, float}:
                r["credits"] += spent
            else:
                r["unknown"] += 1
    return sorted(use.values(), key=lambda r: r["role"])


def moved(routes: APIRouter, *paths: str) -> None:
    """Redirect each read under the old ``/design-pack`` to ``/impeccable``, for pages and links from before the rename.

    The redirect is temporary (307), so a browser that remembers it still reaches a version rolled back to the old
    routes (D-01M63CAZTX2N496K1GFQY6N87Y); the old changing routes run the same handlers instead.
    """
    for path in paths:
        routes.add_api_route(OLD + path, _moved, methods=["GET"], include_in_schema=False)


def _moved(request: Request) -> RedirectResponse:
    head, _, tail = request.url.path.rpartition(OLD)
    return RedirectResponse(str(request.url.replace(path=f"{head}/impeccable{tail}")), 307)


def router(
    store: Store,
    job: pack_job.Job,
    admitted: Callable[[], AbstractContextManager[None]] = contextlib.nullcontext,
    host: Host | None = None,
) -> APIRouter:
    """Impeccable and maintenance routes, with the host's test review; the caller adds the token check.

    An update and its answers run while Delivery is paused (TD-287); *admitted* refuses them once OwlBear stops or
    before a stop when idle, and holds the launch lock while one starts.
    """
    routes = APIRouter()

    @routes.get("/impeccable")
    def read() -> dict[str, Any]:
        return pack(job)

    @routes.get("/impeccable/update")
    def update_state() -> dict[str, Any]:
        return job.read()

    @routes.get("/impeccable/machine")
    def machine() -> dict[str, str | None]:
        return {"machine": pack_job.running_for()}  # TD-290: polled while the page is open

    moved(routes, "", "/update", "/machine")

    @routes.post("/impeccable/update")
    @routes.post(f"{OLD}/update", include_in_schema=False)
    def update() -> dict[str, Any]:
        try:
            with admitted():
                return job.start()
        except pack_job.Busy as exc:
            raise HTTPException(409, str(exc)) from exc

    _answers(routes, job, admitted)
    _replay(routes, store, job, admitted)

    @routes.get("/maintenance")
    def maintenance() -> list[dict[str, Any]]:
        return overview(store)

    @routes.get("/maintenance/subagents")
    def subagents() -> list[dict[str, Any]]:
        return subagent_use(store)

    routes.include_router(maintenance_routes.router(host, (store.name or store.root.name, store.root)))
    if host is not None:
        routes.include_router(curation_routes.router(store, host))
    return routes


def _replay(
    routes: APIRouter, store: Store, job: pack_job.Job, admitted: Callable[[], AbstractContextManager[None]]
) -> None:
    """The installed pack's calibration replay, run by this host's managed job; never a second one at once (TD-177)."""

    @routes.post("/impeccable/replay")
    @routes.post(f"{OLD}/replay", include_in_schema=False)
    def replay() -> dict[str, Any]:
        try:
            with job.exclusive():
                with admitted():  # a barrier only: the launch lock is not held while the replay waits for a slot
                    job.count_replay(1)
                try:
                    r = job.live.replay(store, None, keep=job.keeps)
                finally:
                    job.count_replay(-1)
        except pack_job.Busy as exc:
            raise HTTPException(409, str(exc)) from exc
        except pack_replay.ReplayError as exc:
            raise HTTPException(409, str(exc)) from exc
        except REPLAY_FAILURES as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"ok": r.ok, "report": f"calibration replay: {pack_candidate.said_replay(r)}"}


def _answers(routes: APIRouter, job: pack_job.Job, admitted: Callable[[], AbstractContextManager[None]]) -> None:
    """The owner's answers to a waiting update (TD-193, TD-256), and its discard."""

    @routes.post("/impeccable/update/answer")
    @routes.post(f"{OLD}/update/answer", include_in_schema=False)
    def answer(body: AnswerBody) -> dict[str, Any]:
        try:
            with admitted():  # an answer continues the update's sessions
                return job.answer(body.question, body.option, body.note)
        except (pack_job.Stale, pack_job.Busy) as exc:
            raise HTTPException(409, str(exc)) from exc
        except pack_job.Refused as exc:
            raise HTTPException(422, str(exc)) from exc

    @routes.post("/impeccable/update/discard")
    @routes.post(f"{OLD}/update/discard", include_in_schema=False)
    def discard() -> dict[str, Any]:
        try:
            return job.discard()
        except pack_job.Stale as exc:
            raise HTTPException(409, str(exc)) from exc
