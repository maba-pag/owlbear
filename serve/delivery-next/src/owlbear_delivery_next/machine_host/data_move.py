"""``owlbear data --move [DEST]``: move the shared data repository's checkout, by default into ``~/.owlbear/data``.

Only while OwlBear is stopped and nothing else of it runs: the host's lock is held throughout, and every process that
could write the shared repository, and every runner a project still records, refuses the move (`writers`).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

import psutil

from owlbear_delivery_next.local_system import data_repo, local_home
from owlbear_delivery_next.local_system.storage_io import open_lock
from owlbear_delivery_next.state_store import project_home, registry

if TYPE_CHECKING:
    from collections.abc import Callable

# A process of OwlBear's: one of its packages run as a module or script, or one of its commands (the program or the
# script its interpreter runs)
_OWLBEAR = re.compile(r"owlbear_(?:delivery_next|memory_mcp|knowledge_mcp|browser_mcp)\b")
_COMMANDS = {"owlbear", "owlbear-next"}
USAGE = "usage: owlbear data --move [DEST]  (DEST defaults to ~/.owlbear/data)"


def main(args: list[str], say: Callable[[str], None]) -> int:
    """Move the checkout to DEST; 0 when moved, 1 when refused or unfinished, 2 for a wrong command."""
    rest = [a for a in args if a != "--move"]
    if len(rest) > 1 or any(a.startswith("-") for a in rest):
        say(USAGE)
        return 2
    dest = Path(rest[0]) if rest else data_repo.default()
    home = local_home.root()
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    home_fd = os.open(home, os.O_RDONLY | os.O_DIRECTORY)
    try:
        host = open_lock(home_fd, blocking=False, name="host.lock")
    except BlockingIOError:
        say("not moved: OwlBear is running; `owlbear stop` first, then try again")
        return 1
    finally:
        os.close(home_fd)
    try:
        with data_repo.pointer_lock():
            return data_repo.move(dest, writers, say)
    except data_repo.DataRepoError as exc:
        say(f"not moved: {exc}")
        return 1
    finally:
        os.close(host)


def writers() -> list[str]:
    """What could still write the shared repository: OwlBear's processes, and runners a project still records.

    A process or a store that cannot be read counts, so the move is refused rather than risked.
    """
    return _processes() + _runners()


def _processes() -> list[str]:
    me = psutil.Process()
    mine = {me.pid, *(p.pid for p in me.parents())}
    user, found = os.getuid(), []
    for proc in psutil.process_iter():
        if proc.pid in mine:
            continue
        try:
            if proc.uids().real != user:
                continue
            words = proc.cmdline()
        except psutil.NoSuchProcess, psutil.ZombieProcess:
            continue
        except (psutil.Error, OSError) as exc:
            found.append(f"process {proc.pid} cannot be read: {exc}")
            continue
        if any(_OWLBEAR.search(w) for w in words) or any(Path(w).name in _COMMANDS for w in words[:2]):
            found.append(f"process {proc.pid}: {' '.join(words)[:200]}")
    return found


def _runners() -> list[str]:
    try:
        projects = registry.load().projects
    except registry.RegistryError as exc:
        return [str(exc)]
    found = []
    for project in projects:
        try:
            store = project_home.current(Path(project.path))
            records = sorted((store / "changes").glob("*/runner.json")) if store else []
        except Exception as exc:  # noqa: BLE001 - any failure to read a store refuses the move
            found.append(f"{project.path}: its store cannot be read: {exc}")
            continue
        found += [
            f"{path}: a runner's record; start OwlBear, let it settle the step, stop it, then try again"
            for path in records
        ]
    return found
