"""Where this machine's shared data repository lives, and how it gets there (D-01M5ZET8ZH2TY1GNPDQJ6SKCPM).

A pointer file, ``data.json`` in OwlBear's folder, names the checkout; ``common.json``, its name before the
repository's rename, moves to it once. Without a pointer, ``~/.owlbear/data`` is used when it is a checkout. A clone
address is adopted from a checkout of it or cloned into ``~/.owlbear/data``; a folder the owner names overrides it.
A move of the checkout is recorded in the pointer before it starts, so an interrupted one is finished or undone, and no
reader uses either copy meanwhile. Updates and uninstalling never remove what the pointer names.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

from owlbear_delivery_next.local_system import git_run, local_home, publication_hold
from owlbear_delivery_next.local_system.data_repo import VIEW, DataRepo, DataRepoError, _git, _top, remote_identity
from owlbear_delivery_next.local_system.storage_io import atomic_write, fsync_dir, open_lock

if TYPE_CHECKING:
    from collections.abc import Iterator

POINTER, OLD_POINTER = local_home.POINTER, local_home.OLD_POINTER
CLONE_SECONDS, INVENTORY_SECONDS = 900, 20
HELD = "refs/owlbear/curation"  # a refused memory curation run's edits, never pushed (#746)
CLONING = ".data-clone-"  # a clone in progress beside its place; never published, so a leftover one goes
# A clone address rather than a folder: a scheme (https://, ssh://, file://) or scp's user@host:path
_URL = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://|^[^/\s@]+@[^/\s:]+:")
_log = logging.getLogger(__name__)


class BusyError(DataRepoError):
    """Another process holds the pointer lock: a clone, a move or another `owlbear data`."""


def pointer() -> Path:
    """Where the machine records the shared repository: ``data.json`` in OwlBear's folder.

    It holds ``repository`` (the checkout in use) and ``remote`` (where it is cloned from). A clone not done yet names
    only ``remote`` (and ``failed``, why the last try did not work); a move under way names ``moving_from`` and
    ``moving_to`` and no ``repository``, so no reader, old or new, writes either copy meanwhile; a finished move keeps
    ``moved_from``. Every write is atomic and holds `pointer_lock`; readers never lock.
    """
    return local_home.root() / POINTER


def default() -> Path:
    """The shared repository's own place, ``~/.owlbear/data``: used when no pointer names another."""
    return local_home.root() / local_home.DATA


def is_url(target: str) -> bool:
    """Whether *target* is a clone address rather than a folder."""
    return bool(_URL.match(target))


@contextlib.contextmanager
def pointer_lock() -> Iterator[None]:
    """Hold ``data.lock``, which every pointer write takes, for the whole clone or move; busy is refused at once."""
    home = local_home.root()
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    home_fd = os.open(home, os.O_RDONLY | os.O_DIRECTORY)
    try:
        try:
            lock = open_lock(home_fd, blocking=False, name=local_home.DATA_LOCK)
        except BlockingIOError:
            msg = "another `owlbear data`, move or clone of the shared repository is running; try again when it ends"
            raise BusyError(msg) from None
    finally:
        os.close(home_fd)
    try:
        yield
    finally:
        os.close(lock)


def _parse(path: Path) -> dict[str, str] | None:
    """A pointer file's record; None when there is none, an error when it holds no record."""
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        msg = f"{path} names no repository"
        raise DataRepoError(msg) from exc
    if not isinstance(data, dict) or not all(isinstance(v, str) for v in data.values()):
        msg = f"{path} names no repository"
        raise DataRepoError(msg)
    return data


def _write(record: dict[str, str]) -> None:
    """Replace the pointer with *record*, atomically; the caller holds `pointer_lock`."""
    try:
        atomic_write(pointer(), json.dumps(record) + "\n")
    except OSError as exc:
        msg = f"the pointer {pointer()} could not be written: {exc}"
        raise DataRepoError(msg) from exc


def stored() -> dict[str, str] | None:
    """The pointer as recorded, ``data.json`` else the old ``common.json``; None without either. Never writes."""
    path = pointer()
    found = _parse(path)
    return found if found is not None else _parse(path.with_name(OLD_POINTER))


def configured_root() -> Path | None:
    """The checkout the pointer names, else ``~/.owlbear/data`` when there is no pointer and it is a checkout.

    It never writes.

    For readers that only look, before or without `locate`'s one-time move of the old pointer.
    """
    record = stored()
    if record is None:
        place = default().resolve()
        return place if _top(place) == place else None
    return Path(record["repository"]).expanduser().resolve() if record.get("repository") else None


def protected() -> list[Path]:
    """Every folder that holds or may hold the shared data: the pointer's checkout and a move's ends, and the default.

    Read from the pointer files directly, the old one included, so a check before any migration still sees them; an
    unreadable pointer is an error, never an empty answer. A checkout's Git folder counts too, wherever it lies.
    """
    record = stored() or {}
    named = [record.get(key, "") for key in ("repository", "moving_from", "moving_to")]
    found = [default(), *(Path(p).expanduser() for p in named if p)]
    return found + [common for folder in found if (common := _common(folder))]


def _common(folder: Path) -> Path | None:
    """The Git folder holding the objects of the checkout at *folder*; None when it is no checkout's top folder."""
    root = folder.resolve()
    if _top(root) != root:
        return None
    said = _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if said.returncode != 0:
        msg = f"the Git folder of {root} cannot be found: {said.stderr.strip()}"
        raise DataRepoError(msg)
    return Path(said.stdout.strip())


def holds_data(folder: Path) -> Path | None:
    """The protected folder *folder* is, holds or lies inside; None when it touches none."""
    here = folder.expanduser().resolve()
    for kept in protected():
        there = kept.resolve()
        if here == there or here in there.parents or there in here.parents:
            return kept
    return None


def misplaced(root: Path) -> str:
    """Why *root* cannot hold the shared data: inside OwlBear's own folder, other than its place there; else ''."""
    home, root = local_home.root().resolve(), root.expanduser().resolve()
    if root == default().resolve():
        return ""
    if root == home or home in root.parents or root in home.parents:
        return f"{root} is in or around OwlBear's folder {home}, which updates and uninstalling clear; use {default()}"
    return ""


def _move_old(path: Path, *, held: bool = False) -> None:
    """Move the pointer's old ``common.json`` to *path* once: written atomically, then the old file removed.

    It takes `pointer_lock` unless the caller *held* it; while another writer holds it, it waits for a later read.
    """
    old = path.with_name(OLD_POINTER)
    if path.exists() or not old.is_file():
        return
    if not held:
        with contextlib.suppress(BusyError), pointer_lock():
            _move_old(path, held=True)
        return
    try:
        atomic_write(path, old.read_text())
        old.unlink(missing_ok=True)
    except OSError as exc:
        msg = f"the pointer {old} could not be moved to {path}: {exc}"
        raise DataRepoError(msg) from exc
    _log.warning("moved the shared repository's pointer %s to %s", old, path)


def locate() -> DataRepo | None:
    """The shared repository: the host's view when one is passed down, else the pointer's, else ``~/.owlbear/data``.

    None without any of them: settings then stay in each clone. A pointer that names no checkout yet (a clone or a
    move not finished) and a default place that is no checkout are errors, so nothing writes elsewhere meanwhile.
    """
    if (view := os.environ.get(VIEW)) is not None:
        return DataRepo(Path(view)) if view else None
    return _configured()


def _configured() -> DataRepo | None:
    """`locate` for this machine as configured, whatever view a process was given."""
    path = pointer()
    _move_old(path)
    record = stored()  # the old pointer still, while another writer holds the lock
    if record is None:
        place = default()
        if not place.exists():
            return None
        if _top(place.resolve()) != place.resolve():
            msg = f"{place}, OwlBear's place for the shared repository, is not a git repository's top folder"
            raise DataRepoError(msg)
        return DataRepo(place.resolve())
    if not record.get("repository"):
        raise DataRepoError(_unready(path, record))
    root = Path(record["repository"]).expanduser().resolve()
    if _top(root) != root:
        msg = f"{root}, named in {path}, is not a git repository's top folder"
        raise DataRepoError(msg)
    return DataRepo(root)


def _unready(path: Path, record: dict[str, str]) -> str:
    """Why a pointer without ``repository`` names no checkout yet."""
    if record.get("moving_to"):
        return (
            f"moving the shared repository from {record.get('moving_from')} to {record['moving_to']} is not finished; "
            "`owlbear data` finishes it"
        )
    if remote := record.get("remote"):
        failed = f": {record['failed']}" if record.get("failed") else ""
        return f"the shared repository {remote} is not cloned yet{failed}"
    return f"{path} names no repository"


def _origin(root: Path) -> str:
    return _git(root, "config", "--get", "remote.origin.url").stdout.strip()


def _same(url: str, other: str) -> bool:
    return bool(url and other) and remote_identity(url) == remote_identity(other)


def point(root: Path) -> DataRepo:
    """Record ``root`` as this machine's shared repository; it must be a git checkout's top folder.

    A folder in or around OwlBear's own is refused, except its place for the data, ``~/.owlbear/data``.
    """
    root = root.expanduser().resolve()
    if why := misplaced(root):
        raise DataRepoError(why)
    if _top(root) != root:
        msg = f"{root} is not a git repository's top folder"
        raise DataRepoError(msg)
    with pointer_lock():
        _move_old(pointer(), held=True)
        if (record := _parse(pointer())) and record.get("moving_to"):
            raise DataRepoError(_unready(pointer(), record))
        _write(_final(root))
    return DataRepo(root)


def _final(root: Path, **extra: str) -> dict[str, str]:
    """The pointer for a checkout in use: its path and where it is cloned from."""
    return {"repository": str(root), **({"remote": url} if (url := _origin(root)) else {}), **extra}


def provision(url: str | None = None, *, clone: bool = True, show: bool = False) -> tuple[DataRepo | None, str]:
    """Use the shared repository at *url*, else the pointer's remote: adopt a checkout of it, else clone it.

    First an unfinished move is finished or undone. A checkout already in use, or one at ``~/.owlbear/data``, is
    adopted when its origin is the same repository and refused otherwise, touching nothing. Without one, *url* is
    cloned beside ``~/.owlbear/data`` and renamed into place (when *clone*; *show* lets git print its progress). What
    it did is said; a failure raises with the reason, and a failed clone is kept in the pointer for the next try.
    """
    try:
        with pointer_lock():
            settle()
            record = _parse(pointer()) or {}
            if record.get("repository"):
                return _known(record, url)
            wanted = url or record.get("remote", "")
            place = default()
            if place.exists():
                return _adopt(place, wanted)
            if not wanted:
                return None, ""
            if not clone:
                return None, f"the shared repository {wanted} is not cloned yet"
            if record != {"remote": wanted}:
                _write({"remote": wanted})
            return _clone(wanted, place, show=show)
    except OSError as exc:  # a folder or file OwlBear could not use: said like any other failure, never a crash
        msg = f"the shared repository could not be set up: {exc}"
        raise DataRepoError(msg) from exc


def _known(record: dict[str, str], url: str | None) -> tuple[DataRepo, str]:
    root = Path(record["repository"]).expanduser().resolve()
    if _top(root) != root:
        msg = f"{root}, named in {pointer()}, is not a git repository's top folder"
        raise DataRepoError(msg)
    if url is None:
        return DataRepo(root), ""
    have = _origin(root)
    if not _same(url, have):
        msg = (
            f"this machine already uses {root}, a checkout of {remote_identity(have) if have else 'no remote'}, "
            f"not of {remote_identity(url)}; nothing was changed"
        )
        raise DataRepoError(msg)
    if record.get("remote") != have:
        _write({**record, "remote": have})
    return DataRepo(root), f"already uses {root}, a checkout of {remote_identity(url)}"


def _adopt(place: Path, wanted: str) -> tuple[DataRepo, str]:
    root = place.resolve()
    if _top(root) != root:
        msg = f"{place} is not a git repository's top folder; move it away, then try again"
        raise DataRepoError(msg)
    have = _origin(root)
    if wanted and not _same(wanted, have):
        msg = (
            f"{place} is a checkout of {remote_identity(have) if have else 'no remote'}, not of "
            f"{remote_identity(wanted)}; nothing was changed"
        )
        raise DataRepoError(msg)
    _write(_final(root))
    return DataRepo(root), f"adopted {root}" + (f", a checkout of {remote_identity(have)}" if have else "")


def _clone(url: str, place: Path, *, show: bool) -> tuple[DataRepo, str]:
    """Clone *url* beside *place* and rename it in.

    A failure is kept in the pointer; a rename done before a later error leaves *place* to be adopted at the next try.
    """
    home = local_home.root()
    try:
        temp = Path(tempfile.mkdtemp(prefix=CLONING, dir=home))
    except OSError as exc:
        _failed(url, f"no folder to clone into in {home}: {exc}")
    done = git_run.run(
        home, "clone", *([] if show else ["--quiet"]), "--", url, str(temp), until=None, cap=CLONE_SECONDS, show=show
    )
    why = "" if done.returncode == 0 else (done.stderr or "").strip()[-300:] or f"git exited {done.returncode}"
    if not why and (place.exists() or _parse(pointer()) != {"remote": url}):
        why = f"{place} or {pointer()} changed while cloning; this clone was discarded"
    if not why:
        try:
            temp.rename(place)
        except OSError as exc:
            why = f"the clone could not be renamed to {place}: {exc}"
    if why:
        shutil.rmtree(temp, ignore_errors=True)
        _failed(url, why)
    fsync_dir(home)
    _write(_final(place.resolve()))
    return DataRepo(place.resolve()), f"cloned {url} into {place}"


def _failed(url: str, why: str) -> NoReturn:
    """Keep *why* in the pointer while it still names only *url*, for the next try to show, then raise it."""
    if _parse(pointer()) == {"remote": url}:
        _write({"remote": url, "failed": why})
    msg = f"cloning {url} failed: {why}"
    raise DataRepoError(msg)


def settle() -> str:
    """Move the old pointer, drop a leftover clone, finish or undo a move; the caller holds `pointer_lock`."""
    _move_old(pointer(), held=True)
    for leftover in local_home.root().glob(f"{CLONING}*"):
        if not holds_data(leftover):  # an older `owlbear data` accepted any checkout, even one named like this
            shutil.rmtree(leftover, ignore_errors=True)
    return recover()


def recover() -> str:
    """Finish or undo a move the pointer says is under way; the caller holds `pointer_lock`. What it did, else ''.

    Only the source left: the move never happened, so the pointer names it again. Only the destination: its linked
    worktrees are repaired and checked, then the pointer names it. Both or neither: refused, for the owner to look.
    """
    record = _parse(pointer())
    if not record or not record.get("moving_to"):
        return ""
    source, target = Path(record.get("moving_from", "")), Path(record["moving_to"])
    kept = {"remote": record["remote"]} if record.get("remote") else {}
    there, here = source.exists() and bool(record.get("moving_from")), target.exists()
    if there and not here:
        _write({"repository": str(source), **kept})
        return f"the unfinished move to {target} was undone; {source} is used"
    if here and not there:
        if why := relink(target):
            msg = f"the shared repository was moved to {target}, but {why}; fix it, then run `owlbear data` again"
            raise DataRepoError(msg)
        _write({"repository": str(target), **kept, "moved_from": str(source)})
        return f"the move to {target} was finished"
    if here:
        msg = (
            f"an unfinished move left both {source} and {target}; check which holds your data, remove the other, "
            "then run `owlbear data`"
        )
    else:
        msg = f"an unfinished move left neither {source} nor {target}; restore the shared repository from a backup"
    raise DataRepoError(msg)


def relink(root: Path) -> str:
    """Point the linked worktrees of the checkout at *root* back to it after a move; what failed, else ''."""
    if (done := _git(root, "worktree", "repair")).returncode:
        return f"`git worktree repair` failed: {done.stderr.strip()[:200]}"
    common = _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip()
    for linked in worktrees(root):
        if not linked.exists():
            continue  # gone before the move: git lists it as prunable, and nothing here can work
        found = _git(linked, "rev-parse", "--path-format=absolute", "--git-common-dir")
        if found.returncode or Path(found.stdout.strip()).resolve() != Path(common).resolve():
            return f"its linked worktree {linked} does not reach it"
    return ""


def worktrees(root: Path) -> list[Path]:
    """The checkout's linked worktrees, not its main one."""
    listed = _git(root, "worktree", "list", "--porcelain").stdout.splitlines()
    return [Path(line.removeprefix("worktree ")) for line in listed if line.startswith("worktree ")][1:]


def inventory(shared: DataRepo) -> list[str]:
    """What only this checkout holds, as lines; none when everything in it is published.

    Uncommitted files, memory included; commits on any local branch no remote has; stashes; a held publication; the
    edits of refused memory curation runs; and its linked worktrees, which live elsewhere.
    """
    until, root = time.monotonic() + INVENTORY_SECONDS, shared.root
    status = _git(root, "status", "--porcelain=v1", "-uall", until=until)
    ahead = _git(root, "rev-list", "--count", "--branches", "--not", "--remotes", until=until)
    stashes = _git(root, "stash", "list", until=until)
    curated = _git(root, "for-each-ref", "--format=%(refname)", HELD, until=until)
    if failed := next((d for d in (status, ahead, stashes, curated) if d.returncode), None):
        return [f"{root} cannot be read: {failed.stderr.strip()[:200]}"]
    lines = []
    if files := status.stdout.splitlines():
        untracked = sum(f.startswith("??") for f in files)
        lines.append(f"{len(files)} file(s) not committed, {untracked} of them never added")
    if (count := ahead.stdout.strip()) not in {"", "0"}:
        lines.append(f"{count} commit(s) on local branches that no remote has")
    if stashed := stashes.stdout.splitlines():
        lines.append(f"{len(stashed)} stash(es)")
    if runs := curated.stdout.splitlines():
        lines.append(f"{len(runs)} refused memory curation run(s) held under {HELD}")
    if held := publication_hold.refusal(shared, until):
        lines.append(f"an automatic change is held: {held}")
    lines += [f"linked worktree: {p}" for p in worktrees(root)]
    return lines


@dataclass(frozen=True)
class Described:
    """Which shared repository this machine uses and how it was chosen, for status, doctor and `owlbear data`."""

    root: Path | None
    kind: str  # "default", "override", "none" or "problem"
    problem: str = ""
    warning: str = ""

    @property
    def line(self) -> str:
        """One line: ``shared data: PATH (default)`` and the like."""
        if self.kind == "problem":
            said = f"shared data: problem: {self.problem}"
        elif self.root is None:
            said = "shared data: none; settings stay in each clone (`owlbear data URL` sets one)"
        else:
            said = f"shared data: {self.root} ({self.kind})"
        return said + (f" · {self.warning}" if self.warning else "")


def describe() -> Described:
    """Which shared repository this machine uses, from the pointer and the disk alone: no network, no lock."""
    record: dict[str, str] = {}
    with contextlib.suppress(DataRepoError):
        record = stored() or {}
    moved = record.get("moved_from", "")
    warning = f"the old checkout {moved} is back; OwlBear doesn't use it" if moved and Path(moved).exists() else ""
    try:
        found = _configured()
    except DataRepoError as exc:
        return Described(None, "problem", str(exc), warning)
    if found is None:
        return Described(None, "none", warning=warning)
    return Described(found.root, "default" if found.root == default().resolve() else "override", warning=warning)
