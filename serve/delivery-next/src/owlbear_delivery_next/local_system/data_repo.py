"""Delivery's settings in the shared data repository (TD-57, TD-59, TD-64, TD-98, TD-128).

Where the repository's checkout is and how it gets there is `data_place`'s; this module works in it. The global
layer lives at its root, each project's layer in a folder named
after the project's repository unless the owner chose another name; the folder is claimed by that repository's
identity, and that claim keeps the chosen name for every clone and machine. Every save is committed and pushed
under one repository-wide lock; a failed commit or push is reported, never hidden. A running host passes its view to
its runners through ``OWLBEAR_DATA``; each runner finds the project's folder by its claim.
"""

from __future__ import annotations

import contextlib
import fcntl
import logging
import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system import batch_journal, git_run, publication_hold

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence
    from typing import Self

CONFIG, CLAIM, MEMORY = "config.json", "repository", "memory"
LOCK = "owlbear-delivery.lock"  # in the checkout's Git folder
VIEW = "OWLBEAR_DATA"  # the host's view for its runners: the repository's path, or empty for none
# Delivery's locks, temporary files, calibration screenshots and the backlog migration's journal
EXCLUDE = (".*.lock", ".tmp-*", "*/visual/*/*.png", ".backlog-migration.json")
# Git never combines two versions of one decision file, in any rebase of the checkout: such a rebase stops (TD-424)
ATTRIBUTES = ("**/decisions/*.md -merge",)
GIT_SECONDS, LOCK_SECONDS, SAVE_SECONDS, PENDING_SECONDS = 10, 20, 45, 4  # a save answers within the page's 60 s
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_log = logging.getLogger(__name__)
_HOLDING = threading.local()  # the lock files this thread holds through `DataRepo.locked`


class DataRepoError(ValueError):
    """The pointer names no usable repository, or a project folder belongs to another repository."""


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

    def _lock_file(self) -> Path:
        found = _git(self.root, "rev-parse", "--absolute-git-dir")
        admin = Path(found.stdout.strip())
        if found.returncode or not admin.is_dir():
            msg = f"the git folder of {self.root} cannot be found: {found.stderr.strip()[:200]}"
            raise DataRepoError(msg)
        return admin / LOCK

    @contextlib.contextmanager
    def locked(self, wait: float | None = None) -> Iterator[None]:
        """Hold the repository-wide lock that serializes every write, commit, push and rebase; wait a bounded time."""
        wait = LOCK_SECONDS if wait is None else wait
        lock = self._lock_file()
        admin = lock.parent
        holding: set[Path] = _HOLDING.__dict__.setdefault("paths", set())
        with contextlib.ExitStack() as stack:
            fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            stack.callback(os.close, fd)
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
            if lock not in holding:
                holding.add(lock)
                stack.callback(holding.discard, lock)
            self._exclude(admin)
            yield

    @contextlib.contextmanager
    def quiet(self) -> Iterator[bool]:
        """Whether no writer holds the lock now; while True, none can take it until the block ends.

        This thread's own `locked` counts as quiet. The lock file is made when no writer has made it yet, so the shared
        hold keeps out the first writer too, and what the block reads stays as it is.
        """
        lock = self._lock_file()
        if lock in getattr(_HOLDING, "paths", ()):
            yield True
            return
        fd = os.open(lock, os.O_RDONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BlockingIOError:
                held = False
            else:
                held = True
            yield held
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
    """The shared repository this process uses, or None (`data_place.locate`)."""
    from owlbear_delivery_next.local_system import data_place  # noqa: PLC0415 - it builds on this module

    return data_place.locate()


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
