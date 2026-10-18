"""The design pack's Settings section and the Maintenance overview (TD-101, TD-113): reads, and the one update start.

The overview only links each maintenance action to where it lives and shows its last run where Delivery keeps one;
beside it, each role's use of built-in subagents (TD-376).
"""

from __future__ import annotations

import contextlib
import os
import subprocess
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next.design_packs import design_pack, pack_update
from owlbear_delivery_next.pack_runs import pack_job
from owlbear_delivery_next.settings import roles

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager

    from owlbear_delivery_next.state_store.store import Store


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
        {"name": "Design pack update", "where": "Settings", "href": "/config#pack", "built": True,
         "recorded": True, "last": pack_job.last(store),
         "note": "Detector and design skills together: diff, golden pages, replay, challenger, then commit and push."},
        {"name": "Engine update", "where": "Settings", "href": None, "built": False, "recorded": False,
         "last": None, "note": "Not built yet."},
        {"name": "Review Tests", "where": "Project action", "href": None, "built": False, "recorded": False,
         "last": None, "note": "Not built yet (TD-112)."},
        {"name": "Backlog triage", "where": "Backlog", "href": "/backlog", "built": True, "recorded": False,
         "last": None, "note": "Triage items in the Backlog tab; Delivery keeps no run record for it."},
    ]  # fmt: skip


def subagent_use(store: Store) -> list[dict[str, Any]]:
    """Per role, its steps and the built-in subagents they started, from the step events each Change keeps (TD-376).

    A step logged twice (held, then decided) counts once, as its last event says.
    """
    steps: dict[tuple[str, str], dict[str, Any]] = {}
    for slug in store.slugs():
        for e in store.events(slug):
            if e.get("event") == "step":
                steps[slug, str(e.get("session") or id(e))] = e
    use: dict[str, dict[str, Any]] = {}
    for e in steps.values():
        kind = str(e.get("kind", ""))
        role = roles.SESSIONS.get(kind, kind)
        r = use.setdefault(role, {"role": role, "steps": 0, "with": 0, "runs": 0, "credits": 0.0, "unknown": 0,
                                  "agents": {}})  # fmt: skip
        ran = e.get("subagents") or []
        r["steps"], r["with"], r["runs"] = r["steps"] + 1, r["with"] + bool(ran), r["runs"] + len(ran)
        for s in ran:
            name = s.get("agent") or "unnamed"
            r["agents"][name] = r["agents"].get(name, 0) + 1
            if s.get("credits_known", True):
                r["credits"] += float(s.get("credits") or 0.0)
            else:
                r["unknown"] += 1
    return sorted(use.values(), key=lambda r: r["role"])


def router(
    store: Store, job: pack_job.Job, admitted: Callable[[], AbstractContextManager[None]] = contextlib.nullcontext
) -> APIRouter:
    """The design pack and maintenance routes; the caller adds the token check.

    An update and its answers run while Delivery is paused (TD-287); *admitted* refuses them once OwlBear stops or
    before a stop when idle, and holds the launch lock while one starts.
    """
    routes = APIRouter()

    @routes.get("/design-pack")
    def read() -> dict[str, Any]:
        return pack(job)

    @routes.get("/design-pack/update")
    def update_state() -> dict[str, Any]:
        return job.read()

    @routes.get("/design-pack/machine")
    def machine() -> dict[str, str | None]:
        return {"machine": pack_job.running_for()}  # TD-290: polled while the page is open

    @routes.post("/design-pack/update")
    def update() -> dict[str, Any]:
        try:
            with admitted():
                return job.start()
        except pack_job.Busy as exc:
            raise HTTPException(409, str(exc)) from exc

    _answers(routes, job, admitted)

    @routes.get("/maintenance")
    def maintenance() -> list[dict[str, Any]]:
        return overview(store)

    @routes.get("/maintenance/subagents")
    def subagents() -> list[dict[str, Any]]:
        return subagent_use(store)

    return routes


def _answers(routes: APIRouter, job: pack_job.Job, admitted: Callable[[], AbstractContextManager[None]]) -> None:
    """The owner's answers to a waiting update (TD-193, TD-256), and its discard."""

    @routes.post("/design-pack/update/answer")
    def answer(body: AnswerBody) -> dict[str, Any]:
        try:
            with admitted():  # an answer continues the update's sessions
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
