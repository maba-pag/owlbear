"""Whether a Retro unit may start now: the settings it would run under are all set and readable (#808).

A Change belongs to its registered project. A chat belongs to the registered project whose folder holds its
workspace, the innermost when registrations nest. A synthetic unit, and a chat outside every registered project,
run under this machine's settings over Global. A project registered but not loaded blocks its units with its state.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.improvement import chatlogs
from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.state_store import work_block
from owlbear_delivery_next.state_store.database import StoreError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from owlbear_delivery_next.machine_host.project import Project
    from owlbear_delivery_next.state_store.store import Store


def block(uid: str, projects: Mapping[str, Project]) -> str:
    """Why *uid* may not start now under a machine's registered *projects*; empty when it may."""
    registered = [(i, Path(p.entry.path), p.state, p.store) for i, p in list(projects.items())]
    if uid.startswith("chg:"):
        pid = uid.split(":", 2)[1]
        found = next((r for r in registered if r[0] == pid), None)
        return _project(found[2], found[3]) if found else "its project is not registered"
    if uid.startswith("chat:"):
        cwd = chatlogs.workspace(chatlogs.state() / uid.removeprefix("chat:"))
        if not cwd:
            return f"{work_block.UNREADABLE}its chat's workspace is unknown"
        if inside := [r for r in registered if chatlogs.enrolled(cwd, [str(r[1])])]:
            _, _, state, store = max(inside, key=lambda r: len(r[1].resolve().parts))  # enrolled resolved them
            return _project(state, store)
    return _outside()


def _project(state: str, store: Store | None) -> str:
    if state != "loaded" or store is None:
        return f"its project is {state}"
    return work_block.of_store(store).text()


def _outside() -> str:
    try:
        shared = data_repo.locate()
        return work_block.of_settings(work_block.outside(shared)).text() if shared else work_block.machine().text()
    except (data_repo.DataRepoError, StoreError) as exc:
        return f"{work_block.UNREADABLE}{exc}"


class Skips:
    """What the automatic runs say: once per unit and reason why it waits, and once when it may start again."""

    def __init__(self, say: Callable[[str], None]) -> None:
        self.say, self.waiting = say, dict[str, str]()

    def blocked(self, uid: str, why: str) -> bool:
        """Whether *uid* waits for *why*, said when it starts waiting or its reason changes."""
        if not why:
            if self.waiting.pop(uid, None) is not None:
                self.say(f"Retro may run {uid} again")
            return False
        if self.waiting.get(uid) != why:
            self.waiting[uid] = why
            self.say(f"Retro does not run {uid}: {why}")
        return True
