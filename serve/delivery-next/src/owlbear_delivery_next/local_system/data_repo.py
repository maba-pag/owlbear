"""Delivery's settings in the shared data repository (TD-57, TD-59, TD-64, TD-98, TD-128).

A pointer file names the repository; ``common.json``, its name before the repository's rename, moves to ``data.json``
once. The global layer lives at its root, each project's layer in a folder named
after the project's repository unless the owner chose another name; the folder is claimed by that repository's
identity, and that claim keeps the chosen name for every clone and machine. Every save is committed and pushed
under one repository-wide lock; a failed commit or push is reported, never hidden. A running host passes its view to
its runners through ``OWLBEAR_DATA``; each runner finds the project's folder by its claim.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system import batch_journal, git_run, local_home, publication_hold
from owlbear_delivery_next.local_system.storage_io import atomic_write, fsync_dir, open_lock

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence
    from typing import Self

CONFIG, CLAIM, MEMORY = "config.json", "repository", "memory"
POINTER, OLD_POINTER = local_home.POINTER, local_home.OLD_POINTER
VIEW = "OWLBEAR_DATA"  # the host's view for its runners: the repository's path, or empty for none
# Delivery's locks, temporary files, calibration screenshots and the backlog migration's journal
EXCLUDE = (".*.lock", ".tmp-*", "*/visual/*/*.png", ".backlog-migration.json")
# Git never combines two versions of one decision file, in any rebase of the checkout: such a rebase stops (TD-424)
ATTRIBUTES = ("**/decisions/*.md -merge",)
GIT_SECONDS, LOCK_SECONDS, SAVE_SECONDS, PENDING_SECONDS = 10, 20, 45, 4  # a save answers within the page's 60 s
CLONE_SECONDS, INVENTORY_SECONDS = 900, 20
CLONING = ".data-clone-"  # a clone in progress beside its place; never published, so a leftover one goes
# A clone address rather than a folder: a scheme (https://, ssh://, file://) or scp's user@host:path
_URL = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://|^[^/\s@]+@[^/\s:]+:")
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_log = logging.getLogger(__name__)


class DataRepoError(ValueError):
    """The pointer names no usable repository, or a project folder belongs to another repository."""


class BusyError(DataRepoError):
    """Another process holds the pointer lock: a clone, a move or another `owlbear data`."""


class Committed(str):
    """What `DataRepo.commit` says: why it failed, else nothing, as before; and the commit it made, "" when none.

    It is the notice string every caller already reads, so they need nothing new; a publication also reads `commit`
    to tell its own commit from one the owner made meanwhile, never by a moved HEAD alone. `unnamed` says Git made a
    commit whose id its own answer did not name: then no commit is known to be this call's.
    """

    __slots__ = ("commit", "unnamed")

    def __new__(cls, notice: str, commit: str = "", *, unnamed: bool = False) -> Self:  # noqa: D102 - the class says it
        made = super().__new__(cls, notice)
        made.commit, made.unnamed = commit, unnamed
        return made


# The first line `git commit` prints names the commit it made, in full with `core.abbrev=no`: "[branch id] subject",
# "[branch (root-commit) id] ..." or "[detached HEAD id] ...". A branch name holds no space, so the first " id]" is it.
_MADE = re.compile(r"\[[^\n]*? ([0-9a-f]{40}|[0-9a-f]{64})\](?: |$)")


def _held(path: Path) -> str:
    """The identity a claim file holds; nothing when there is none."""
    try:
        return path.read_text().strip()
    except OSError, ValueError:
        return ""


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
    unreadable pointer is an error, never an empty answer.
    """
    record = stored() or {}
    named = [record.get(key, "") for key in ("repository", "moving_from", "moving_to")]
    return [default(), *(Path(p).expanduser() for p in named if p)]


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


def _git(cwd: Path, *args: str, until: float | None = None) -> subprocess.CompletedProcess[str]:
    """One git command, ended by ``until`` (monotonic) at the latest; never started once it passed (`git_run.run`)."""
    return git_run.run(cwd, *args, until=until, cap=GIT_SECONDS)


def _top(root: Path) -> Path | None:
    out = _git(root, "rev-parse", "--show-toplevel") if root.is_dir() else None
    return Path(out.stdout.strip()).resolve() if out and out.returncode == 0 else None


@dataclass(frozen=True)
class DataRepo:
    """The shared repository's checkout on this machine."""

    root: Path

    @property
    def global_path(self) -> Path:
        """The global layer, at the repository's root."""
        return self.root / CONFIG

    def project_path(self, name: str) -> Path:
        """A project's layer, in the folder named after its repository."""
        return self.root / name / CONFIG

    def memory_path(self, name: str) -> Path:
        """A project's agent memory, beside its layer (TD-72); memory curation commits it."""
        return self.root / name / MEMORY

    def git(
        self, *args: str, until: float | None = None, guard: Callable[[], str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        """One git command in the checkout; a timeout or a missing folder is a failed command.

        A push runs only as one checked, non-forced refspec. Plain and held pushes must land on the checked upstream;
        with nothing held, an explicit push may name its caller's captured destination. An unproved destination or
        a held change that no longer meets the fetched remote sends nothing (`publication_hold.pushing`). A push's
        *guard*, an owned caller's final check, runs after those probes and immediately before Git starts the push:
        what it refuses, nothing is sent.
        """
        pushing = args[:1] == ("push",)
        run = args
        if pushing:
            held, run = publication_hold.pushing(self, args, until)
            if not held and guard is not None:
                held = guard()
            if held:
                return subprocess.CompletedProcess(["git", *args], 1, "", held)
        done = _git(self.root, *run, until=until)
        if pushing and done.returncode == 0:
            publication_hold.settled(self, until)
        return done

    @contextlib.contextmanager
    def locked(self, wait: float | None = None) -> Iterator[None]:
        """Hold the repository-wide lock that serializes every write, commit, push and rebase; wait a bounded time."""
        wait = LOCK_SECONDS if wait is None else wait
        found = _git(self.root, "rev-parse", "--absolute-git-dir")
        admin = Path(found.stdout.strip())
        if found.returncode or not admin.is_dir():
            msg = f"the git folder of {self.root} cannot be found: {found.stderr.strip()[:200]}"
            raise DataRepoError(msg)
        fd = os.open(admin / "owlbear-delivery.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            end = time.monotonic() + wait
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() > end:
                        msg = "another settings save is still running; try again"
                        raise DataRepoError(msg) from None
                    time.sleep(0.1)
            self._exclude(admin)
            yield
        finally:
            os.close(fd)

    def _exclude(self, admin: Path) -> None:
        for name, lines in (("exclude", EXCLUDE), ("attributes", ATTRIBUTES)):
            path = admin / "info" / name
            text = path.read_text() if path.exists() else ""
            if missing := [p for p in lines if p not in text.splitlines()]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text + ("" if not text or text.endswith("\n") else "\n") + "\n".join(missing) + "\n")

    def claim(self, name: str, identity: str) -> bool:
        """Bind the project folder to one repository; True when this call wrote the claim.

        Another repository of the same name is refused.
        """
        path = self.root / name / CLAIM
        held = path.read_text().strip() if path.exists() else ""
        if held and held != identity:
            msg = f"the shared settings folder {name} belongs to {held}, not {identity}; run setup with --folder NAME"
            raise DataRepoError(msg)
        if held:
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(identity + "\n")
        return True

    def claimed(self, identity: str) -> str | None:
        """The folder ``identity`` claims, under the name kept for the repository (TD-98); None before any claim."""
        found = sorted(p.parent.name for p in self.root.glob(f"*/{CLAIM}") if _held(p) == identity)
        if len(found) > 1:
            msg = f"the shared settings folders {', '.join(found)} all belong to {identity}; remove all but one"
            raise DataRepoError(msg)
        return found[0] if found else None

    def refusal(self, name: str, identity: str) -> str:
        """Why ``name`` cannot be the folder of ``identity``; nothing when it can."""
        if not _NAME.fullmatch(name) or name == CONFIG:
            return f"{name!r} is no folder name: up to 64 letters, digits, '.', '_' or '-', first a letter or digit"
        if (self.root / name).exists() and not (self.root / name).is_dir():
            return f"{name} is a file in {self.root}"
        held = _held(self.root / name / CLAIM)
        return f"the shared settings folder {name} belongs to {held}" if held and held != identity else ""

    def rename(self, old: str, new: str, until: float | None = None) -> str:
        """Move a project's folder with all it holds to ``new``, commit and push the move; the caller holds ``locked``.

        Files never committed move along uncommitted. What the owner should know about the publication, else nothing.
        """
        until = time.monotonic() + SAVE_SECONDS if until is None else until
        why = self.refusal(new, _held(self.root / old / CLAIM))
        if why or (self.root / new).exists():
            raise DataRepoError(why or f"{new} already exists in {self.root}")
        if _git(self.root, "diff", "--cached", "--quiet", until=until).returncode:
            msg = f"{self.root} has staged changes; commit or unstage them, then rename again"
            raise DataRepoError(msg)
        _git(self.root, "mv", "-k", "--", old, new, until=until)
        if (self.root / old).exists():  # nothing in it was ever committed, so git moved nothing
            (self.root / old).rename(self.root / new)
        if _git(self.root, "diff", "--cached", "--quiet", until=until).returncode:
            made = _git(self.root, "commit", "-q", "-m", f"settings: the folder {old} is now {new}", until=until)
            if made.returncode:
                return f"renamed, but not committed: {made.stderr.strip()[:200]}"
        return self._push(until)

    def publish(self, paths: Path | Sequence[Path], message: str, until: float | None = None) -> str:
        """Commit ``paths`` alone if they changed and push; what the owner should know when that fails, else nothing.

        The caller holds ``locked``. Unpushed earlier commits are pushed too, so an unchanged save retries them.
        """
        until = time.monotonic() + SAVE_SECONDS if until is None else until
        return self.commit(paths, message, until) or self._push(until)

    def hold(self, watch: Path, requires: publication_hold.Requires, until: float | None = None) -> None:
        """Bind the automatic change about to be written to *watch* to the remote; the caller holds ``locked``."""
        publication_hold.hold(self, watch, requires, until)

    def held(self, until: float | None = None) -> str:
        """Why a held automatic change keeps this checkout from pushing or rebasing; nothing when it does not."""
        return publication_hold.refusal(self, until)

    def commit(self, paths: Path | Sequence[Path], message: str, until: float | None = None) -> Committed:
        """Commit ``paths`` alone if they changed; why that failed, else nothing. The caller holds ``locked``.

        The answer also names the commit made (`Committed.commit`), "" when none: the id `git commit` itself printed for
        the commit it made, never HEAD read afterwards, which an owner's commit or amend may already have moved. Hooks
        print to stderr, so stdout's first line is Git's own; when it names no full id of an existing commit, the
        commit made is `unnamed`. Hooks and signing run as configured: only the printed id's length is set.
        """
        until = time.monotonic() + SAVE_SECONDS if until is None else until
        rels = [p.relative_to(self.root).as_posix() for p in ([paths] if isinstance(paths, Path) else paths)]
        why, rels = self._stage(rels, until)
        if why or not rels:
            return Committed(why)  # failed, or nothing changed: no commit was made
        made = _git(self.root, "-c", "core.abbrev=no", "commit", "-m", message, "--", *rels, until=until)
        if made.returncode:
            return Committed(f"saved, but not committed: {made.stderr.strip()[:200]}")
        named = _MADE.match(made.stdout.partition("\n")[0])
        oid = named.group(1) if named else ""
        known = _git(self.root, "rev-parse", "--verify", "-q", f"{oid}^{{commit}}", until=until) if oid else None
        return Committed("", oid) if known and known.stdout.strip() == oid else Committed("", unnamed=True)

    def _stage(self, rels: list[str], until: float) -> tuple[str, list[str]]:
        """Stage those of *rels* that exist or are tracked; why that failed, and those to commit, none if unchanged."""
        try:
            rels = [r for r in rels if (self.root / r).exists() or self._tracked(r, until)]
        except DataRepoError as exc:
            return f"saved, but not committed: {exc}", []
        if not rels:
            return "", []  # removed before it was ever committed: nothing to commit
        if (added := _git(self.root, "add", "--", *rels, until=until)).returncode:
            return f"saved, but not committed: {added.stderr.strip()[:200]}", []
        staged = _git(self.root, "diff", "--cached", "--quiet", "--", *rels, until=until)
        if staged.returncode not in (0, 1):
            why = staged.stderr.strip()[:200] or "git could not read staged changes"
            return f"saved, but not committed: {why}", []
        return "", rels if staged.returncode == 1 else []

    def _tracked(self, rel: str, until: float) -> bool:
        """Whether the index holds ``rel``; a failed probe cannot establish absence."""
        probe = _git(self.root, "ls-files", "-z", "--", rel, until=until)
        if probe.returncode:
            msg = f"git cannot tell whether {rel} is tracked: {probe.stderr.strip()[:200] or 'tracking probe failed'}"
            raise DataRepoError(msg)
        return bool(probe.stdout)

    def _push(self, until: float) -> str:  # noqa: PLR0911 - each push and the rebase between report apart
        """Push; once rejected, rebase on the remote and push again.

        Nothing while a decision batch is unsettled; then a held automatic change is checked, and every push runs as
        the one non-forced refspec proven to land on the upstream (`publication_hold.pushing`).
        """
        if held := self._decision_batch_held(until):
            return f"saved and committed in {self.root}, but not pushed: {held}"
        held, run = publication_hold.pushing(self, ("push", "-q"), until)
        if held:
            return f"saved and committed in {self.root}, but not pushed: {held}"
        if _git(self.root, *run, until=until).returncode == 0:
            publication_hold.settled(self, until)
            return ""
        if pulled := self.pull(until):
            if publication_hold.recorded(self, until):  # never pushed by hand: the remote must be checked first
                return f"saved and committed in {self.root}, but not pushed: {pulled}"
            return f"saved and committed in {self.root}, but it could not be merged with the remote; push it by hand"
        held, run = publication_hold.pushing(self, ("push", "-q"), until)  # the remote may have moved since the rebase
        if held:
            return f"saved and committed in {self.root}, but not pushed: {held}"
        sent = _git(self.root, *run, until=until)
        if sent.returncode:
            return f"saved and committed in {self.root}, but the push failed: {sent.stderr.strip()[:200]}"
        publication_hold.settled(self, until)
        return ""

    def _decision_batch_held(self, until: float) -> str:
        """Why nothing may be pushed or rebased here: a decision batch is interrupted, or its journal cannot be read.

        An interrupted batch may have left an incomplete commit in this checkout; another clone, holding no journal,
        would read it as settled decisions. Only the batch's own publisher and the owner's finish or abandon move it.
        """
        try:
            batch = batch_journal.pending(self, until)  # within the caller's deadline: a lock held past it is not free
        except batch_journal.JournalBusyError as exc:
            return f"whether a decision batch is interrupted is not known yet: {exc}"
        except batch_journal.JournalError as exc:
            return f"the decision batch journal cannot be read ({str(exc)[:200]}); repair it in Decisions"
        if batch is None:
            return ""
        return f"the decision batch {batch.generation} is interrupted; finish or abandon it in Decisions first"

    def pull(self, until: float | None = None) -> str:
        """Rebase on the remote; a failed rebase is left as Git stopped it for the owner. Why it failed, else nothing.

        Nothing is rebased while a decision batch is unsettled (`_decision_batch_held`), checked within the deadline.
        """
        until = time.monotonic() + SAVE_SECONDS if until is None else until
        if held := self._decision_batch_held(until):
            return f"not rebased on the remote: {held}"
        if publication_hold.recorded(self, until):
            return self._pull_held(until)
        pulled = _git(self.root, "-c", "rebase.autoStash=false", "pull", "-q", "--rebase", until=until)
        return self._settle(pulled, "git pull failed", until)

    def _pull_held(self, until: float) -> str:
        """Fetch, check a held automatic change against that remote, then rebase on exactly the revision checked.

        An owner's rebase in progress is left as it is, and nothing is rebased.
        """
        try:
            if self.rebasing(until):
                return f"not rebased on the remote: a rebase is in progress in {self.root}; finish or abort it first"
        except DataRepoError as exc:
            return f"not rebased on the remote: {exc}"
        if held := publication_hold.check(self, until, fetch=True):
            return held
        done = _git(self.root, "-c", "rebase.autoStash=false", "rebase", "-q", "@{upstream}", until=until)
        return self._settle(done, "git rebase failed", until)

    def rebase(self, until: float | None = None, guard: Callable[[], str] | None = None) -> str:
        """Rebase on the upstream as last fetched, without fetching. A failed rebase is never aborted. Why it failed.

        *guard*, an owned caller's final check, runs after the publication hold's own probes and immediately before
        Git starts the rebase: what it refuses, nothing is rebased. Without one the hold alone decides, as before.
        """
        until = time.monotonic() + SAVE_SECONDS if until is None else until
        if held := publication_hold.check(self, until, fetch=False):
            return held
        if guard is not None and (why := guard()):
            return why
        done = _git(self.root, "-c", "rebase.autoStash=false", "rebase", "-q", "@{upstream}", until=until)
        return self._settle(done, "git rebase failed", until)

    def rebasing(self, until: float | None = None) -> bool:
        """Whether Git has a rebase in progress in this checkout, whoever started it; never aborted here.

        Raises `DataRepoError` when Git cannot name its admin directory: that is unknown, never "no rebase".
        """
        until = time.monotonic() + SAVE_SECONDS if until is None else until
        probe = _git(self.root, "rev-parse", "--absolute-git-dir", until=until)
        if probe.returncode or not probe.stdout.strip():
            why = probe.stderr.strip()[:200] or "git named no git directory"
            msg = f"cannot tell whether a rebase is in progress in {self.root}: {why}"
            raise DataRepoError(msg)
        admin = Path(probe.stdout.strip())
        return any((admin / d).exists() for d in ("rebase-merge", "rebase-apply"))

    def _settle(self, done: subprocess.CompletedProcess[str], failed: str, until: float) -> str:
        """Report a failed rebase and leave it exactly as Git stopped it: no abort, no index or worktree change."""
        if done.returncode == 0:
            return ""
        why = done.stderr.strip()[:200] or failed
        try:
            rebasing = self.rebasing(until)
        except DataRepoError as exc:
            return f"{why}; {exc}, so it was left as it is for the owner to check"
        if rebasing:
            return f"{why}; a rebase is in progress in {self.root} and was left as it is for the owner to resolve"
        return why

    def pending(self) -> str:
        """What in the shared checkout is not yet committed or pushed, as a notice; nothing when all is published."""
        until = time.monotonic() + PENDING_SECONDS
        status = _git(self.root, "status", "--porcelain", "--", ".", f":(exclude)*/{MEMORY}/*", until=until)
        if status.returncode:
            return f"the shared settings repository {self.root} cannot be read: {status.stderr.strip()[:200]}"
        files = status.stdout.splitlines()
        unpushed, why = self._unpushed(until)
        if why:
            return f"the shared settings repository {self.root} cannot be read: {why}"
        parts = [f"{len(files)} file(s) not committed"] if files else []
        if unpushed:
            parts.append(f"{unpushed} commit(s) not pushed")
        if held := publication_hold.refusal(self, until):  # a held change waits for the owner, not for a retry
            return f"unpublished in {self.root}: {', '.join(parts) or 'nothing'}; an automatic change is held: {held}"
        return f"unpublished in {self.root}: {', '.join(parts)}; the next save retries" if parts else ""

    def _unpushed(self, until: float) -> tuple[int, str]:
        """Count commits no remote has, distinguishing an unborn checkout from a failed probe."""
        head = _git(self.root, "rev-parse", "--verify", "--quiet", "HEAD", until=until)
        if head.returncode == 1:
            return 0, ""
        if head.returncode:
            return 0, head.stderr.strip()[:200] or "git could not resolve HEAD"
        counted = _git(self.root, "rev-list", "--count", "HEAD", "--not", "--remotes", until=until)
        raw = counted.stdout.strip()
        if counted.returncode or not (raw.isascii() and raw.isdecimal()):
            return 0, counted.stderr.strip()[:200] or "git printed no valid commit count"
        return int(raw), ""


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
    record = _parse(path)
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
    home = local_home.root()
    temp = Path(tempfile.mkdtemp(prefix=CLONING, dir=home))
    quiet = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        done = subprocess.run(  # noqa: S603 - the owner's address, passed after --
            ["git", "clone", *([] if show else ["--quiet"]), "--", url, str(temp)],  # noqa: S607
            env=quiet, stdin=subprocess.DEVNULL, capture_output=not show, text=True, timeout=CLONE_SECONDS, check=False,
        )  # fmt: skip
        why = "" if done.returncode == 0 else (done.stderr or "").strip()[-300:] or f"git exited {done.returncode}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        why = f"{type(exc).__name__}: {exc}"
    if not why and (place.exists() or _parse(pointer()) != {"remote": url}):
        why = f"{place} or {pointer()} changed while cloning; this clone was discarded"
    if why:
        shutil.rmtree(temp, ignore_errors=True)
        if _parse(pointer()) == {"remote": url}:
            _write({"remote": url, "failed": why})
        msg = f"cloning {url} failed: {why}"
        raise DataRepoError(msg)
    temp.rename(place)
    fsync_dir(home)
    _write(_final(place.resolve()))
    return DataRepo(place.resolve()), f"cloned {url} into {place}"


def settle() -> str:
    """Move the old pointer, drop a leftover clone, finish or undo a move; the caller holds `pointer_lock`."""
    _move_old(pointer(), held=True)
    for leftover in local_home.root().glob(f"{CLONING}*"):
        shutil.rmtree(leftover, ignore_errors=True)
    return recover()


def move(dest: Path, writers: Callable[[], list[str]], say: Callable[[str], None]) -> int:
    """Move the shared repository's checkout to *dest*, keeping all it holds; 0 when done, else 1 with the reason said.

    The caller holds `pointer_lock` and has stopped the host. While the pointer names the move, no reader resolves
    either copy; *writers* then lists anything that still could write it, which refuses the move and puts the pointer
    back. A rename moves it, on the same disk only; its linked worktrees are repaired and checked before the pointer
    names it, and a failure there leaves the move for `owlbear data` to finish.
    """
    settle()
    record = stored() or {}
    if not record.get("repository"):
        say("not moved: no shared repository is set (`owlbear data` shows it)")
        return 1
    source = Path(record["repository"]).expanduser().resolve()
    dest = dest.expanduser().parent.resolve() / dest.name
    if why := _unmovable(source, dest):
        say(f"not moved: {why}")
        return 1
    shared = DataRepo(source)
    with shared.locked(wait=0):
        before = inventory(shared)
        say(f"moving {source} to {dest}; only on this machine: " + ("; ".join(before) or "nothing"))
        _write({**_kept(record), "moving_from": str(source), "moving_to": str(dest)})
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
        if why := relink(dest):
            say(f"moved to {dest}, but {why}; fix it, then run `owlbear data` to finish")
            return 1
        _write({**_kept(record), "repository": str(dest), "moved_from": str(source)})
        after = inventory(DataRepo(dest))
    if after != before:
        say("moved, but what only this machine holds differs; check it: " + "; ".join(after))
        return 1
    say(f"moved: the shared repository is now {dest}; nothing is left at {source}")
    return 0


def _kept(record: dict[str, str]) -> dict[str, str]:
    return {"remote": url} if (url := record.get("remote") or _origin(Path(record["repository"]))) else {}


def _unmovable(source: Path, dest: Path) -> str:
    """Why the checkout at *source* cannot be renamed to *dest*; '' when it can. Checked in order, each lazily."""
    misplaced_why = misplaced(dest)
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

    Uncommitted files, memory included; commits on any local branch no remote has; stashes; a held publication; and its
    linked worktrees, which live elsewhere.
    """
    until, root = time.monotonic() + INVENTORY_SECONDS, shared.root
    status = _git(root, "status", "--porcelain=v1", "-uall", until=until)
    ahead = _git(root, "rev-list", "--count", "--branches", "--not", "--remotes", until=until)
    stashes = _git(root, "stash", "list", until=until)
    if failed := next((d for d in (status, ahead, stashes) if d.returncode), None):
        return [f"{root} cannot be read: {failed.stderr.strip()[:200]}"]
    lines = []
    if files := status.stdout.splitlines():
        untracked = sum(f.startswith("??") for f in files)
        lines.append(f"{len(files)} file(s) not committed, {untracked} of them never added")
    if (count := ahead.stdout.strip()) not in {"", "0"}:
        lines.append(f"{count} commit(s) on local branches that no remote has")
    if stashed := stashes.stdout.splitlines():
        lines.append(f"{len(stashed)} stash(es)")
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


def remote_identity(url: str) -> str:
    """A remote's URL without scheme, user and ``.git``: ``github.com/owner/name``."""
    bare = re.sub(r"^[^/@]*@", "", re.sub(r"^[a-z+]+://", "", url)).replace(":", "/", 1)  # user-info only
    return bare.removesuffix("/").removesuffix(".git")


def identity(repo: Path) -> str:
    """Who a project is: its origin remote without scheme, user and ``.git``, else its main checkout's path."""
    if url := _git(repo, "config", "--get", "remote.origin.url").stdout.strip():
        return remote_identity(url)
    top = _git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip()
    return str(Path(top).parent) if top else str(repo.resolve())


def project_name(repo: Path) -> str:
    """The project's repository name (TD-64): the last part of its identity, made safe for a folder name."""
    safe = _UNSAFE.sub("-", identity(repo).rsplit("/", 1)[-1]).strip(".-")
    return safe or "project"


def folder(shared: DataRepo, repo: Path) -> str:
    """The project's folder in ``shared``: the one its repository claims, else one named after the repository."""
    return shared.claimed(identity(repo)) or project_name(repo)
