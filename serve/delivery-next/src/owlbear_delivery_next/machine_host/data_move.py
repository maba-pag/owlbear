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

from owlbear_delivery_next.local_system import data_place, data_repo, local_home, maintenance
from owlbear_delivery_next.local_system.data_place import _origin, _write
from owlbear_delivery_next.local_system.data_repo import _git, _top
from owlbear_delivery_next.local_system.storage_io import fsync_dir, open_lock
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
    dest = Path(rest[0]) if rest else data_place.default()
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
        with data_place.pointer_lock():
            return move(dest, say)
    except data_repo.DataRepoError as exc:
        say(f"not moved: {exc}")
        return 1
    finally:
        os.close(host)


def move(dest: Path, say: Callable[[str], None]) -> int:
    """Move the shared repository's checkout to *dest*, keeping all it holds; 0 when done, else 1 with the reason said.

    The caller holds `pointer_lock` and the host's lock. While the pointer names the move, no reader resolves either
    copy; `writers` then lists anything that still could write it, which refuses the move and puts the pointer back.
    A rename moves it, on the same disk only; its linked worktrees are repaired and checked before the pointer names
    it, and a failure there leaves the move for `owlbear data` to finish.
    """
    data_place.settle()
    record = data_place.stored()
    if record is None and (root := data_place.configured_root()):
        record = {"repository": str(root)}  # a checkout at the default place, which a start adopts
    record = record or {}
    if not record.get("repository"):
        say("not moved: no shared repository is set (`owlbear data` shows it)")
        return 1
    source = Path(record["repository"]).expanduser().resolve()
    dest = dest.expanduser().parent.resolve() / dest.name
    if why := _unmovable(source, dest):
        say(f"not moved: {why}")
        return 1
    shared = data_repo.DataRepo(source)
    with shared.locked(wait=0):
        before = data_place.inventory(shared)
        say(f"moving {source} to {dest}; only on this machine: " + ("; ".join(before) or "nothing"))
        kept = _kept(record)
        _write({**kept, "moving_from": str(source), "moving_to": str(dest)})
        try:
            live = writers()
            if not live:
                source.rename(dest)
        except BaseException:
            _write(record)
            raise
        if live:
            _write(record)
            say("not moved, something may still write it; end it, then try again:")
            for line in live:
                say(f"  {line}")
            return 1
        fsync_dir(source.parent)
        fsync_dir(dest.parent)
        if why := data_place.relink(dest):
            say(f"moved to {dest}, but {why}; fix it, then run `owlbear data` to finish")
            return 1
        _write({**kept, "repository": str(dest), "moved_from": str(source)})
        after = data_place.inventory(data_repo.DataRepo(dest))
    if after != before:
        say("moved, but what only this machine holds differs; check it: " + "; ".join(after))
        return 1
    say(f"moved: the shared repository is now {dest}; nothing is left at {source}")
    return 0


def _kept(record: dict[str, str]) -> dict[str, str]:
    return {"remote": url} if (url := record.get("remote") or _origin(Path(record["repository"]))) else {}


def _unmovable(source: Path, dest: Path) -> str:
    """Why the checkout at *source* cannot be renamed to *dest*; '' when it can. Checked in order, each lazily."""
    misplaced_why = data_place.misplaced(dest)
    checks: tuple[tuple[Callable[[], bool], str], ...] = (
        (lambda: source == dest, f"it is already at {dest}"),
        (lambda: bool(misplaced_why), misplaced_why),
        (lambda: os.path.lexists(dest), f"{dest} exists; choose a new folder"),
        (lambda: not dest.parent.is_dir(), f"{dest.parent} does not exist"),
        (lambda: source in dest.parents, f"{dest} is inside {source}"),
        (lambda: _top(source) != source, f"{source} is not a git repository's top folder"),
        (lambda: _linked(source), f"{source} is a linked worktree; move its main checkout"),
        (lambda: source.stat().st_dev != dest.parent.stat().st_dev, f"{dest} is on another disk; a move only renames"),
    )
    return next((said for bad, said in checks if bad()), "")


def _linked(root: Path) -> bool:
    git_dir = _git(root, "rev-parse", "--path-format=absolute", "--git-dir").stdout.strip()
    common = _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip()
    return not git_dir or Path(git_dir).resolve() != Path(common).resolve()


def writers() -> list[str]:
    """What could still write the shared repository: OwlBear's processes, runners and maintenance sessions.

    Runners count while a project still records them, maintenance sessions while active or not confirmed ended. A
    process, a store or a ledger that cannot be read counts, so the move is refused rather than risked.
    """
    return _processes() + _runners() + _maintenance()


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
    """Runner records in every store: each folder under the stores' home, and a registered clone's own store."""
    found = []
    try:
        stores = {folder.resolve(): str(folder) for folder in _children(local_home.root() / project_home.PROJECTS)}
        projects = registry.load().projects
    except (registry.RegistryError, OSError) as exc:
        return [f"the project stores cannot be listed: {exc}"]
    for project in projects:
        try:
            store = project_home.current(Path(project.path))
        except Exception as exc:  # noqa: BLE001 - any failure to read a store refuses the move
            found.append(f"{project.path}: its store cannot be read: {exc}")
            continue
        if store:
            stores.setdefault(store.resolve(), project.path)
    for store, name in sorted(stores.items()):
        try:
            records = _records(store / "changes")
        except OSError as exc:
            found.append(f"{name}: its store cannot be read: {exc}")
            continue
        found += [
            f"{path}: a runner's record; start OwlBear, let it settle the step, stop it, then try again"
            for path in records
        ]
    return found


def _children(home: Path) -> list[Path]:
    try:
        return sorted(folder for folder in home.iterdir() if folder.is_dir())
    except FileNotFoundError:
        return []


def _records(changes: Path) -> list[Path]:
    """The runner records under *changes*; a folder that cannot be listed or read raises, unlike a glob."""
    try:
        folders = sorted(changes.iterdir())
    except FileNotFoundError:
        return []
    found = []
    for folder in folders:
        try:
            (folder / "runner.json").stat()
        except FileNotFoundError, NotADirectoryError:
            continue
        found.append(folder / "runner.json")
    return found


def _maintenance() -> list[str]:
    try:
        with maintenance.Maintenance.locked() as ledger:
            held = [s for s in ledger.sessions if s.state in maintenance.HELD]
    except maintenance.MaintenanceError as exc:
        return [str(exc)]
    return [
        f"maintenance session {s.kind} in {s.project} is {s.state}; let it end, or recover it after a restart"
        for s in held
    ]
