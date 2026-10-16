"""The design pack's Settings section and the Maintenance overview (TD-101, TD-113): reads, and the one update start.

The overview only links each maintenance action to where it lives and shows its last run where Delivery keeps one.
"""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException

from owlbear_delivery_next import design_pack, pack_job, pack_update

if TYPE_CHECKING:
    from owlbear_delivery_next.store import Store


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
         "last": None, "note": "Subagent monitoring is built; the paired pilot (TD-178) waits for a proven "
                                 "spending bound."},
    ]  # fmt: skip


def router(store: Store, job: pack_job.Job) -> APIRouter:
    """The design pack and maintenance routes; the caller adds the token check."""
    routes = APIRouter()

    @routes.get("/design-pack")
    def read() -> dict[str, Any]:
        return pack(job)

    @routes.get("/design-pack/update")
    def update_state() -> dict[str, Any]:
        return job.read()

    @routes.post("/design-pack/update")
    def update() -> dict[str, Any]:
        try:
            return job.start()
        except pack_job.Busy as exc:
            raise HTTPException(409, str(exc)) from exc

    @routes.get("/maintenance")
    def maintenance() -> list[dict[str, Any]]:
        return overview(store)

    return routes
