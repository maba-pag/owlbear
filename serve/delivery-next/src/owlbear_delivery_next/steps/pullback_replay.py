"""Pull-back's changes to the local copy: replay local commits and apply one tree update safely (TD-26).

Local commits (never merges) are replayed with ``cherry-pick --empty=keep`` onto the merged change in a temporary
detached worktree, which is always removed afterwards. An update from *old* to *new* (a fast-forward or a replay
result) is applied by a two-tree ``read-tree -m -u`` (which keeps index entries and files of unchanged paths and
refuses if a changing path has local changes) and a compare-and-swap ``update-ref`` of the expected branch, after
the caller's guard checked every path the update itself changes. If ``read-tree`` fails after writing some files
and the index is untouched, those paths are restored from *old*; otherwise the paths to restore are reported.
"""

from __future__ import annotations

import contextlib
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

from owlbear_delivery_next.steps import worktree

if TYPE_CHECKING:
    from collections.abc import Callable

SHOWN = 5
_LOG = logging.getLogger(__name__)

type Local = dict[str, tuple[str, str]]


class BehindError(Exception):
    """The target stays behind; the message is the reason."""


def git(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run one local Git command in *path*."""
    return subprocess.run(  # noqa: S603 - fixed Git executable and argument vector
        [worktree.GIT, *args], cwd=path, capture_output=True, text=True, check=False, timeout=120
    )


def first(stderr: str | bytes) -> str:
    """The first non-blank line of a Git message."""
    text = stderr.decode(errors="replace") if isinstance(stderr, bytes) else stderr
    return next((line.strip() for line in text.splitlines() if line.strip()), "git failed")


def must(path: Path, *args: str) -> str:
    """Stdout of a Git command that must succeed.

    Raises:
        BehindError: The command failed; its first stderr line.
    """
    done = git(path, *args)
    if done.returncode != 0:
        raise BehindError(first(done.stderr))
    return done.stdout


def split_z(out: str) -> list[str]:
    """The non-empty fields of NUL-separated Git output."""
    return [p for p in out.split("\0") if p]


def rev(path: Path, ref: str) -> str | None:
    """The commit *ref* names, or None."""
    done = git(path, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    return done.stdout.strip() if done.returncode == 0 else None


def changed(wt: Path, old: str, new: str) -> list[str]:
    """Paths that differ between two commits, with both ends of a rename or copy."""
    fields, paths = iter(split_z(must(wt, "diff", "--name-status", "-z", "-M", old, new))), []
    for code in fields:
        paths.append(next(fields, ""))
        if code[:1] in {"R", "C"}:
            paths.append(next(fields, ""))
    return [p for p in paths if p]


def _remove(wt: Path, tmp: Path) -> None:
    """Remove the temporary worktree; every step runs even if an earlier one failed, and none fails the caller."""
    steps: tuple[Callable[[], object], ...] = (
        lambda: git(wt, "worktree", "unlock", str(tmp)),
        lambda: git(wt, "worktree", "remove", "--force", "--force", str(tmp)),
        lambda: shutil.rmtree(tmp, ignore_errors=True),
        lambda: git(wt, "worktree", "prune"),
    )
    for step in steps:
        with contextlib.suppress(subprocess.TimeoutExpired, OSError):
            step()
    names = {f"worktree {tmp}", f"worktree {tmp.resolve()}"}
    try:
        listed = set(git(wt, "worktree", "list", "--porcelain").stdout.splitlines())
    except subprocess.TimeoutExpired:
        listed = names
    if names & listed:
        _LOG.warning("pull-back could not unregister temporary worktree %s; run `git worktree prune`", tmp)


def replay(wt: Path, base: str, old: str, remote: str) -> str:
    """Cherry-pick ``base..old`` onto *remote* in a temporary detached worktree; the new head.

    Raises:
        BehindError: Local merges, a conflict or any other failure; the temporary worktree is removed.
    """
    if must(wt, "rev-list", "--merges", f"{remote}..{old}").strip():
        msg = "local merge commits; pull manually"
        raise BehindError(msg)
    tmp = Path(tempfile.mkdtemp(prefix="owlbear-pullback-"))
    try:
        must(wt, "worktree", "add", "--quiet", "--detach", str(tmp), remote)
        done = git(tmp, "cherry-pick", "--allow-empty", "--empty=keep", f"{base}..{old}")
        if done.returncode != 0:
            conflict = bool(git(tmp, "ls-files", "-u").stdout.strip())
            git(tmp, "cherry-pick", "--abort")
            raise BehindError("your local commits conflict with the merged change" if conflict else first(done.stderr))
        return must(tmp, "rev-parse", "HEAD").strip()
    finally:
        _remove(wt, tmp)


def _in_tree(wt: Path, commit: str, paths: list[str]) -> set[str]:
    return set(split_z(must(wt, "--literal-pathspecs", "ls-tree", "-r", "-z", "--name-only", commit, "--", *paths)))


def _diff(wt: Path, *args: str) -> set[str]:
    return set(split_z(must(wt, "--literal-pathspecs", "diff", "--name-only", "-z", *args)))


def _left(wt: Path, old: str, paths: list[str]) -> list[str]:
    """Of *paths*, those whose index entry or working file no longer matches *old*."""
    known = _in_tree(wt, old, paths)
    extra = {p for p in paths if p not in known and os.path.lexists(wt / p)}
    return sorted(_diff(wt, old, "--", *paths) | _diff(wt, "--cached", old, "--", *paths) | extra)


def _reconcile(wt: Path, ref: str, old: str, paths: list[str], error: str) -> NoReturn:
    """Undo a failed ``read-tree`` for *paths*, which the guard found clean, if only working files changed.

    Raises:
        BehindError: Always; *error* if the local copy is as before, else the paths to restore.
    """
    if rev(wt, ref) == old and not _diff(wt, "--cached", old, "--", *paths):
        known = _in_tree(wt, old, paths)
        for rel in paths:
            if rel not in known and ((wt / rel).is_symlink() or (wt / rel).is_file()):
                (wt / rel).unlink()
        if known:
            git(wt, "--literal-pathspecs", "checkout", old, "--", *sorted(known))
    if left := _left(wt, old, paths):
        shown = " ".join(left[:SHOWN])
        msg = f"partial update: {shown} changed; run `git checkout -- {shown}` after fixing {error}"
        raise BehindError(msg)
    raise BehindError(error)


def apply(wt: Path, ref: str, old: str, new: str, guard: Callable[[list[str]], Local]) -> Local:
    """Move *ref* and the local copy from *old* to *new*; the local state *guard* returned, to check against.

    ``read-tree -m -u`` runs no hook and refuses before writing if a differing path has local changes or an
    untracked or ignored file is in the way; ``update-ref`` then moves *ref* only if it is still *old*.
    ``reset --keep`` would drop staged contents.

    Raises:
        BehindError: A path the update changes collides, HEAD is no longer *ref* at *old*, or Git refused.
    """
    paths = changed(wt, old, new)
    before = guard(paths)
    if git(wt, "symbolic-ref", "-q", "HEAD").stdout.strip() != ref or rev(wt, "HEAD") != old:
        msg = f"HEAD moved during pull-back; expected {ref} at {old[:12]}"
        raise BehindError(msg)
    try:
        done = git(wt, "read-tree", "-m", "-u", old, new)
    except subprocess.TimeoutExpired:
        _reconcile(wt, ref, old, paths, "git timed out")
    if done.returncode != 0:
        _reconcile(wt, ref, old, paths, first(done.stderr))
    try:
        done = git(wt, "update-ref", "-m", "pull-back: update to the merged change", ref, new, old)
        why = "" if done.returncode == 0 and rev(wt, "HEAD") == new else first(done.stderr)
    except subprocess.TimeoutExpired:
        why = "git timed out"
    if why:
        msg = f"manual check needed: files are at {new} but {ref} may not have moved: {why}"
        raise BehindError(msg)
    return before
