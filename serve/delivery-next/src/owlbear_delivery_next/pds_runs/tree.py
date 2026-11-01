"""A PDS run's trees (#777): the candidate worktree, the base, the updater's copy and the identities that bind them.

The candidate is a worktree of the pinned base with the release written in. Its identity has two parts: ``C``, the
pin, vendored tree and served files, fixed once the candidate is made, and ``S``, the pages and the module that serves
them, which the updater changes. The audit, the browser tests and the challenger each judge one ``S``.
"""

from __future__ import annotations

import contextlib
import hashlib
import shutil
from typing import TYPE_CHECKING

from owlbear_delivery_next.impeccable import pack_files
from owlbear_delivery_next.impeccable_runs import pack_gates
from owlbear_delivery_next.pds_runs import audit, pin

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.impeccable.pack_git import Git

PACKAGE = pin.PREFIX
PIN = f"{PACKAGE}{pin.PIN}"
TREE = f"{PACKAGE}{pin.TREE}/"
SERVED = f"{PACKAGE}{pin.WEB}/"
WEB = f"{PACKAGE}web/"
PAGES = f"{PACKAGE}project_host/pages.py"  # serves the pages and puts the pinned version into them
PAGE_TYPES = (".html", ".mjs", ".js", ".css")
EDITABLE = tuple(f"web/{d}/" for d in audit.VENDORED)  # under web/ but never the updater's


class Outside(pack_files.PackError):
    """The updater changed what it may not; nothing it did was taken."""


def worktree(root: Path, at: Path, rev: str, git: Git) -> Path:
    """A fresh detached worktree of *rev* from the checkout *root*, at *at*."""
    remove(root, at, git)
    git(root, ["worktree", "add", "--quiet", "--detach", str(at), rev])
    return at


def remove(root: Path, at: Path, git: Git) -> None:
    """Remove the worktree at *at*, and what is left of it."""
    with contextlib.suppress(pack_files.PackError):  # not a worktree, or gone already
        git(root, ["worktree", "remove", "--force", str(at)])
    shutil.rmtree(at, ignore_errors=True)
    git(root, ["worktree", "prune"])


def lay(at: Path, files: dict[str, bytes | None]) -> None:
    """Write *files* by repository path into the tree at *at*; None removes one."""
    for path, data in files.items():
        if data is None:
            (at / path).unlink(missing_ok=True)
        else:
            (at / path).parent.mkdir(parents=True, exist_ok=True)
            (at / path).write_bytes(data)


def files(at: Path, folder: str) -> dict[str, bytes]:
    """The files under *folder* of the tree at *at*, never a link, by repository path."""
    base = at / folder
    found = sorted(p for p in base.rglob("*") if p.is_file() and not p.is_symlink()) if base.is_dir() else []
    return {p.relative_to(at).as_posix(): p.read_bytes() for p in found}


def protected(at: Path) -> dict[str, bytes]:
    """The pin, the vendored tree and the served files of the tree at *at*, by repository path."""
    pinned = {PIN: (at / PIN).read_bytes()} if (at / PIN).is_file() else {}
    return pinned | files(at, TREE) | files(at, SERVED)


def source(at: Path) -> dict[str, bytes]:
    """The pages and the module that serves them in the tree at *at*, by repository path."""
    pages = {p: d for p, d in files(at, WEB).items() if p.endswith(PAGE_TYPES) and not p.startswith(SERVED)}
    return pages | ({PAGES: (at / PAGES).read_bytes()} if (at / PAGES).is_file() else {})


digest = pack_gates.digest  # one digest over files' paths and bytes


def identity(candidate: str, pages: str) -> str:
    """The whole candidate's identity, from its ``C`` and its ``S``: what a challenge verdict judged."""
    return hashlib.sha256(f"{candidate}\n{pages}".encode()).hexdigest()


def copy(candidate: Path, at: Path, git: Git) -> dict[str, str]:
    """Lay out the updater's copy at *at*: the candidate's pages, in a repository of their own; their digests."""
    shutil.rmtree(at, ignore_errors=True)
    at.mkdir(parents=True)
    audit.copy_files(candidate / WEB, at / "web", skip=audit.VENDORED)
    git(at, ["init", "-q"])  # the session's window places files only in a repository
    return _now(at)


def _now(at: Path) -> dict[str, str]:
    return {p: d for p, d in audit.digests(at).items() if not p.startswith(".git/")}


def taken(at: Path, start: dict[str, str], candidate: Path) -> list[str]:
    """The updater's edits in its copy at *at*, written into the candidate: only existing page files it changed.

    Raises:
        Outside: It added, removed or linked a file, or changed one that is not a page; nothing was written.
    """
    now = _now(at)
    changed = audit.changed(start, now)
    bad = [
        p
        for p in changed
        if p not in start or p not in now or now[p] == "link" or not p.endswith(PAGE_TYPES) or p.startswith(EDITABLE)
    ]
    if bad:
        msg = f"the updater changed files it may not ({', '.join(bad[:8])}); nothing it did was taken"
        raise Outside(msg)
    for p in changed:
        (candidate / PACKAGE / p).write_bytes((at / p).read_bytes())
    return changed
