"""The machine's Impeccable update as Maintenance's OwlBear section shows it, the same in every project.

The pack is the machine's, so one update is open at a time across its projects (``pack_admission``); the run is kept in
the project that started it, whose labels, calibration and spend it uses. This view reads every registered project's
run record, and the serving project's own, without writing: never through a Job, which would settle a run its host
left running. A record that cannot be read is said per project, never taken for an idle one.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.impeccable import pack_files, pack_update
from owlbear_delivery_next.impeccable_runs import pack_progress
from owlbear_delivery_next.impeccable_runs.pack_state import running_for
from owlbear_delivery_next.state_store import pack_run_record, project_home, registry

if TYPE_CHECKING:
    from collections.abc import Callable

OPEN = frozenset({"running", "waiting"})
TRIES = 3  # reads of a record a writer replaced meanwhile, before it is said to be unreadable


def pinned() -> dict[str, Any]:
    """The pack this OwlBear version pins, whether it is in place here, and the last look at upstream's releases."""
    pins, notice = pack_files.manifest(), pack_update.notice(refresh=False)
    return {
        "pack": pins["pack"], "upstream": pins["upstream"]["tag"], "identity": pack_files.identity(),
        "status": pack_files.status(),
        "notice": {"said": pack_update.said(notice), "behind": notice["behind"], "checked_at": notice["checked_at"]},
    }  # fmt: skip


def runs(
    own: tuple[str, Path] | None = None,
    *,
    reader: Callable[[Path], dict[str, Any] | None] = pack_run_record.read_only,
    actions: dict[str, str] = pack_progress.ACTIONS,
) -> dict[str, Any]:
    """Every project's last Impeccable run, and the one to show: the open one, else the latest started.

    *reader* and *actions* are the kind's: a PDS update's record and its actions read the same way.

    *own* is the serving project's name and store root, its run marked ``own``; the machine host has none.
    ``holder`` names the project whose update holds the machine's lock now; a record that says running while none
    does was left by a host that stopped.
    """
    places, unread = _places(own)
    seen = [_seen(pid, name, root, reader) | {"own": here} for pid, name, root, here in places]
    started = [s for s in seen if s["record"] and s["record"].get("started_at")]
    open_ = [s for s in started if s["state"] in OPEN]
    focus = open_[0] if open_ else max(started, key=lambda s: str(s["record"]["started_at"]), default=None)
    holder = running_for()
    return {
        "holder": holder, "registry": unread,
        "runs": [{k: s[k] for k in ("pid", "name", "own", "state", "error")} | _times(s["record"]) for s in seen],
        "run": _shown(focus, holder, actions) if focus else None,
    }  # fmt: skip


def _places(own: tuple[str, Path] | None) -> tuple[list[tuple[str, str, Path, bool]], str]:
    """Each project as (id, name, store root): the serving one first, then the registry's; why that is unread."""
    try:
        listed = registry.load().projects
        unread = ""
    except registry.RegistryError as exc:
        listed, unread = [], f"the machine's registry cannot be read, so other projects' runs are not shown: {exc}"
    places: dict[str, list[Any]] = {}
    if own is not None:
        places[os.path.realpath(own[1])] = ["", own[0], own[1], True]
    for p in listed:
        root = project_home.home(p.id)
        if (key := os.path.realpath(root)) in places:
            places[key][0] = p.id  # the serving project, by its registry id
        else:
            places[key] = [p.id, Path(p.path).name, root, False]
    return [(pid, name, root, here) for pid, name, root, here in places.values()], unread


def _seen(pid: str, name: str, root: Path, reader: Callable[[Path], dict[str, Any] | None]) -> dict[str, Any]:
    error = ""
    for _ in range(TRIES):
        try:
            record = reader(root)
        except (OSError, ValueError) as exc:
            error = f"its run record cannot be read ({exc})"
            continue
        state = str(record.get("state") or "idle") if record else "idle"
        return {"pid": pid, "name": name, "state": state, "error": "", "record": record}
    return {"pid": pid, "name": name, "state": "unreadable", "error": error, "record": None}


def _times(record: dict[str, Any] | None) -> dict[str, Any]:
    return {k: (record or {}).get(k) for k in ("started_at", "ended_at", "reason")}


def _shown(s: dict[str, Any], holder: str | None, actions: dict[str, str]) -> dict[str, Any]:
    """The run as the section shows it: its record without the context, its progress, and where it was started."""
    record = s["record"]
    shown = {k: v for k, v in record.items() if k != "context"} | {"progress": pack_progress.progress(record, actions)}
    stopped = record["state"] == "running" and holder is None
    return shown | {k: s[k] for k in ("pid", "name", "own")} | {"interrupted": stopped}
