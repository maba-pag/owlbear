"""A curation run's own worktree of the shared repository (#746): only an accepted run's edits reach the checkout.

The curator works in a detached worktree seeded with the checkout's memory as it is, uncommitted files included. Its
commits never land on the checkout's branch, so no publication, its own or another writer's, can carry them. An
accepted run's changed files are written into the checkout and published in one commit; a refused run's edits, committed
or not, are kept in a local ref that no push names.
"""

from __future__ import annotations

import contextlib
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

from owlbear_memory import MemoryState, storage, writer_lock

from owlbear_delivery_next.local_system.data_place import HELD
from owlbear_delivery_next.local_system.data_repo import CONFIG, MEMORY, DataRepoError
from owlbear_delivery_next.local_system.storage_io import atomic_write

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path

    from owlbear_delivery_next.local_system.data_repo import DataRepo

NO_EDITS = "the run changed no memory, so nothing is held"
LISTED = "its worktree is still listed (the log says why)"

_log = logging.getLogger(__name__)


def _git(cwd: Path, *args: str, index: Path | None = None) -> str:
    """One git command's standard output; a failure raises, naming the command and what Git said."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"} | ({"GIT_INDEX_FILE": str(index)} if index else {})
    try:
        done = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector
            ["git", *args],  # noqa: S607
            cwd=cwd, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60,
            check=False,
        )  # fmt: skip
    except (OSError, subprocess.TimeoutExpired) as exc:
        msg = f"git {args[0]} failed: {exc}"
        raise DataRepoError(msg) from exc
    if done.returncode:
        msg = f"git {args[0]} failed: {done.stderr.strip()[:200]}"
        raise DataRepoError(msg)
    return done.stdout.strip()


def _files(root: Path, dirs: Sequence[str]) -> dict[str, bytes]:
    """The regular, non-hidden memory files under *root* by repository-relative path; locks and temps are hidden."""
    found = {}
    for d in dirs:
        folder = root / d
        if folder.is_dir() and not folder.is_symlink():
            for p in folder.iterdir():
                if not p.name.startswith(".") and p.is_file() and not p.is_symlink():
                    found[f"{d}/{p.name}"] = p.read_bytes()
    return found


def _read(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() and not path.is_symlink() else None


def _pending(rel: str, raw: bytes) -> bool:
    """Whether the file is a pending entry, which stays uncommitted as the memory server leaves it."""
    try:  # the model keeps the plain value
        return rel.endswith(".md") and storage.read_entry_bytes_strict(raw).state == MemoryState.PENDING
    except ValueError:
        return False


@dataclass(frozen=True)
class Tree:
    """One run's worktree and the checkout's memory as it was seeded."""

    shared: DataRepo
    root: Path
    base: dict[str, bytes]  # every memory file of the checkout at the seed
    dirs: tuple[str, ...]  # "<folder>/memory" for each project folder, and Global's "memory"
    head: str  # the worktree's HEAD at the seed

    def changed(self) -> dict[str, bytes | None]:
        """The worktree's memory files that differ from the seed, with their bytes; None for one the run removed."""
        now = _files(self.root, self.dirs)
        return {r: b for r, b in now.items() if self.base.get(r) != b} | dict.fromkeys(self.base.keys() - now.keys())

    def hold(self, folder: str, key: str) -> str:
        """Keep the worktree's memory, committed or not, in a local ref; say where, or that the run changed nothing.

        A private index keeps a lingering session's ``index.lock`` from blocking it.
        """
        if not self.changed() and _git(self.root, "rev-parse", "HEAD") == self.head:
            return NO_EDITS
        index = self.root.parent / "held-index"
        _git(self.root, "read-tree", "HEAD", index=index)
        if there := [d for d in self.dirs if (self.root / d).is_dir()]:
            _git(self.root, "add", "-A", "--", *there, index=index)
        if gone := [d for d in self.dirs if not (self.root / d).is_dir()]:
            _git(self.root, "rm", "-r", "-q", "--cached", "--ignore-unmatch", "--", *gone, index=index)
        tree = _git(self.root, "write-tree", index=index)
        said = f"held: refused memory curation of {folder} (machine host)"
        commit = _git(self.root, "commit-tree", tree, "-p", "HEAD", "-m", said)
        ref = f"{HELD}/{key.rpartition(':')[2]}"  # the folder is in its message: '..' or '.lock' make no ref name
        _git(self.root, "update-ref", ref, commit)
        index.unlink(missing_ok=True)
        return f"its edits are held, never published, in {ref}"

    def accept(self, folder: str, key: str) -> tuple[str, str]:
        """Write the run's changes into the checkout and publish them: why it was refused, or the publication notice.

        Refused whole, and held, when a file it changed changed in the checkout meanwhile. Pending entries it wrote
        stay uncommitted there, and so does a deletion its own commits did not make: the memory server defers one
        whose entry lives on pending.
        """
        changed = self.changed()
        texts = {r: None if b is None else b.decode() for r, b in changed.items()}  # undecodable: raised, held
        made = ("diff", "-z", "--name-only", "--no-renames", "--diff-filter=D", self.head, "HEAD", "--", *self.dirs)
        deleted = {r for r in _git(self.root, *made).split("\0") if r}  # its commits' deletions, batch-validated
        shared = self.shared
        touched = sorted(changed.keys() | deleted)
        with shared.locked(), contextlib.ExitStack() as locks:  # the repository lock first, as every writer
            for d in sorted({r.rpartition("/")[0] for r in touched}):
                (shared.root / d).mkdir(exist_ok=True)  # Global's folder, before its first entry, as Make global
                locks.enter_context(writer_lock(shared.root / d))
            if moved := next((r for r in touched if _read(shared.root / r) != self.base.get(r)), None):
                return f"refused, {moved} changed meanwhile; {self.hold(folder, key)}", ""
            for r, text in texts.items():
                if text is None:
                    (shared.root / r).unlink(missing_ok=True)
                else:
                    atomic_write(shared.root / r, text)
            kept = [
                shared.root / r
                for r in touched
                if ((b := changed.get(r)) is None and r in deleted) or (b is not None and not _pending(r, b))
            ]
            try:
                return "", shared.publish(kept, f"chore: memory curation of {folder} (machine host)")
            except (OSError, DataRepoError, subprocess.SubprocessError) as exc:  # live, maybe committed: it stands
                return "", f"written, but not published: {type(exc).__name__}: {exc}"


def seed(shared: DataRepo, at: Path, folders: Sequence[str]) -> Tree:
    """Add a detached worktree at *at* holding the checkout's memory of *folders* and Global, uncommitted included."""
    dirs = (*(f"{f}/{MEMORY}" for f in folders), MEMORY)
    with shared.locked():
        _git(shared.root, "worktree", "prune")  # the worktrees of runs whose workspace is gone
        _git(shared.root, "worktree", "add", "-q", "--detach", str(at), "HEAD")
        with contextlib.ExitStack() as locks:  # a save renames its temp into place under its folder's lock
            for d in sorted(d for d in dirs if (shared.root / d).is_dir()):
                locks.enter_context(writer_lock(shared.root / d))
            base = _files(shared.root, dirs)
        for rel in _files(at, dirs).keys() - base.keys():
            (at / rel).unlink()
        for d in dirs:
            (at / d).mkdir(parents=True, exist_ok=True)
        for rel, raw in base.items():
            (at / rel).write_bytes(raw)
        if (shared.root / CONFIG).is_file():
            shutil.copyfile(shared.root / CONFIG, at / CONFIG)
        head = _git(at, "rev-parse", "HEAD")
    return Tree(shared, at, base, dirs, head)


def prune(shared: DataRepo) -> str:
    """Forget the worktrees whose folder is gone, so the checkout lists none of a finished run; why that failed.

    A failure changes nothing a run did, and the next run's seed prunes again, so it is logged and its row says so.
    """
    try:
        with shared.locked():
            _git(shared.root, "worktree", "prune")
    except DataRepoError as exc:
        _log.warning("%s still lists a finished curation run's worktree: %s", shared.root, exc)
        return LISTED
    return ""


@contextlib.contextmanager
def forgetting(shared: DataRepo) -> Iterator[None]:
    """On an exception, forget the run's worktree as a returning run's caller does, then raise, prune failure added."""
    try:
        yield
    except Exception as exc:
        if pruned := prune(shared):
            msg = f"{pruned}; {type(exc).__name__}: {exc}"  # first: a row keeps the reason's start
            raise RuntimeError(msg) from exc
        raise


@contextlib.contextmanager
def holding(tree: Tree, folder: str, key: str) -> Iterator[None]:
    """On an exception, hold the run's edits and raise again, led by where they are held; unchanged if none."""
    try:
        yield
    except Exception as exc:
        try:
            held = tree.hold(folder, key)
        except (OSError, DataRepoError) as failed:  # the run's own failure stays in its row
            why = f"{type(failed).__name__}: {failed}; {type(exc).__name__}: {exc}"
            msg = f"its edits are not held in a curation ref: {why}"
            raise RuntimeError(msg) from exc
        if held == NO_EDITS:
            raise
        msg = f"{held}; {type(exc).__name__}: {exc}"
        raise RuntimeError(msg) from exc
