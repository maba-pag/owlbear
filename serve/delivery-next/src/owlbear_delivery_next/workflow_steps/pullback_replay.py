"""Pull-back's changes to the local copy: replay local commits and apply one tree update safely (TD-26).

Local commits (never merges) are replayed with ``cherry-pick --empty=keep`` onto the merged change in a temporary
detached worktree, which is always removed afterwards. An update from *old* to *new* (a fast-forward or a replay
result) is applied by a two-tree ``read-tree -m -u`` (which keeps index entries and files of unchanged paths and
refuses if a changing path has local changes) and a compare-and-swap ``update-ref`` of the expected branch, after
the caller's guard checked every path the update itself changes. If ``read-tree`` fails after writing some files
and the index is untouched, only the paths that hold exactly what it wrote are restored from *old*; anything else
is someone's work and stays. Entries are compared as checkout writes them, with the attributes of the commit
that wrote them, never through a symlink and never by reading a special file. If the ref then fails to move, the
update is reversed, or the exact recovery named.
"""

from __future__ import annotations

import contextlib
import logging
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, NoReturn

from owlbear_delivery_next.change_flow import worktree

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


def _remove(wt: Path, tmp: Path) -> str:
    """Remove the temporary worktree; every step runs even if one fails. A note if anything is left."""
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
    except subprocess.TimeoutExpired, OSError:
        listed = names
    if names & listed or os.path.lexists(tmp):
        _LOG.warning("pull-back could not remove temporary worktree %s", tmp)
        return f"temporary worktree {tmp} was not removed; delete it and run `git worktree prune`"
    return ""


def replay(wt: Path, base: str, old: str, remote: str) -> tuple[str, str]:
    """Cherry-pick ``base..old`` onto *remote* in a temporary detached worktree: the new head, and a cleanup note.

    Raises:
        BehindError: Local merges, a conflict or any other failure; the temporary worktree is removed.
    """
    if must(wt, "rev-list", "--merges", f"{remote}..{old}").strip():
        msg = "local merge commits; pull manually"
        raise BehindError(msg)
    tmp = Path(tempfile.mkdtemp(prefix="owlbear-pullback-"))
    try:
        head = _pick(wt, tmp, f"{base}..{old}", remote)
    except (BehindError, subprocess.TimeoutExpired, OSError) as exc:
        reason = "git timed out" if isinstance(exc, subprocess.TimeoutExpired) else str(exc)
        if note := _remove(wt, tmp):
            msg = f"{reason}; {note}"
            raise BehindError(msg) from exc
        raise
    except BaseException:
        _remove(wt, tmp)
        raise
    return head, _remove(wt, tmp)


def _pick(wt: Path, tmp: Path, commits: str, remote: str) -> str:
    must(wt, "worktree", "add", "--quiet", "--detach", str(tmp), remote)
    done = git(tmp, "cherry-pick", "--allow-empty", "--empty=keep", commits)
    if done.returncode != 0:
        conflict = bool(git(tmp, "ls-files", "-u").stdout.strip())
        git(tmp, "cherry-pick", "--abort")
        raise BehindError("your local commits conflict with the merged change" if conflict else first(done.stderr))
    return must(tmp, "rev-parse", "HEAD").strip()


def _in_tree(wt: Path, commit: str, paths: list[str]) -> set[str]:
    args = ("ls-tree", "-r", "-t", "-z", "--name-only", commit, "--", *paths)
    return set(split_z(must(wt, "--literal-pathspecs", *args)))


def _diff(wt: Path, *args: str) -> set[str]:
    return set(split_z(must(wt, "--literal-pathspecs", "diff", "--name-only", "-z", *args)))


def _left(wt: Path, old: str, paths: list[str]) -> list[str]:
    """Of *paths*, those whose index entry or working file no longer matches *old*."""
    known = _in_tree(wt, old, paths)
    extra = {p for p in paths if p not in known and os.path.lexists(wt / p)}
    return sorted(_diff(wt, old, "--", *paths) | _diff(wt, "--cached", old, "--", *paths) | extra)


def _blobs(wt: Path, commit: str, paths: list[str]) -> dict[str, str]:
    """Mode of each of *paths* in *commit*, and of the directories that hold them."""
    found: dict[str, str] = {}
    for entry in split_z(must(wt, "--literal-pathspecs", "ls-tree", "-r", "-t", "-z", commit, "--", *paths)):
        meta, _, path = entry.partition("\t")
        found[path] = meta.split()[0]
    return found


type Entry = tuple[object, ...] | None
_UNKNOWN: Entry = ("unknown",)  # never equal to a disk entry: the path is kept


def _beyond(wt: Path, rel: str) -> Path | None:
    """The entry above *rel* that is a symlink or not a directory; Git never reads or writes through it."""
    here = wt
    for part in PurePosixPath(rel).parts[:-1]:
        here /= part
        if here.is_symlink() or not here.is_dir():
            return here if os.path.lexists(here) else None
    return None


def _entry(wt: Path, rel: str) -> Entry:
    """What is on disk at *rel* as Git sees it: None for nothing, a kind that never matches for a special file."""
    file = wt / rel
    try:
        if _beyond(wt, rel) is not None or not os.path.lexists(file):
            return None
        st = file.lstat()
        if stat.S_ISLNK(st.st_mode):
            return ("link", os.fsencode(file.readlink()))
        if stat.S_ISDIR(st.st_mode):
            return ("dir",)
        return _regular(file, st)
    except OSError:
        return ("unreadable",)


def _regular(file: Path, st: os.stat_result) -> Entry:
    """A regular file's kind, exec bit and bytes; opened without following a link or blocking on a FIFO."""
    if not stat.S_ISREG(st.st_mode):
        return ("special", stat.S_IFMT(st.st_mode))
    with os.fdopen(os.open(file, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as fd:
        if not stat.S_ISREG(os.fstat(fd.fileno()).st_mode):
            return ("special", 0)
        return ("file", bool(st.st_mode & stat.S_IXUSR), fd.read())


def _want(wt: Path, commit: str, rel: str, modes: dict[str, str]) -> Entry:
    """What checking out *rel* from *commit* writes, with *commit*'s attributes; unknown if Git cannot say."""
    mode = modes.get(rel)
    if mode is None:
        return None
    if mode == "040000":
        return ("dir",)
    kind = {"120000": "link", "100644": "file", "100755": "file"}.get(mode)
    args = ("cat-file", "blob") if kind == "link" else ("cat-file", "--filters")
    try:
        done = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector
            [worktree.GIT, f"--attr-source={commit}", *args, f"{commit}:{rel}"],
            cwd=wt,
            capture_output=True,
            check=False,
            timeout=120,
        )
    except subprocess.TimeoutExpired, OSError:
        return _UNKNOWN
    if kind is None or done.returncode != 0:
        return _UNKNOWN
    return ("link", done.stdout) if kind == "link" else ("file", mode == "100755", done.stdout)


def _clear(wt: Path, rel: str, new: str, wrote: dict[str, str]) -> bool:
    """Remove what the update wrote at *rel*, or the entry it wrote above it; False if anything else is there."""
    target = wt / rel
    try:
        if (above := _beyond(wt, rel)) is not None:
            up = above.relative_to(wt).as_posix()
            if _entry(wt, up) != _want(wt, new, up, wrote):
                return False
            above.unlink()
        elif target.is_dir() and not target.is_symlink():
            target.rmdir()  # only empty: what read-tree left after its files were removed
        elif os.path.lexists(target):
            target.unlink()
    except OSError:
        return False
    return True


def _undo(wt: Path, old: str, new: str, paths: list[str]) -> list[str]:
    """Put back from *old*, deepest first, each path holding exactly what *new* writes; the others are kept.

    Each path is restored right after it is compared, so a save can only be lost in that short window. A file
    that holds exactly *new*'s content is taken for the update's, whoever wrote it.
    """
    was, wrote, kept = _blobs(wt, old, paths), _blobs(wt, new, paths), []
    for rel in sorted(paths, key=lambda p: p.count("/"), reverse=True):
        now = _entry(wt, rel)
        if now == _want(wt, old, rel, was):
            continue
        if now != _want(wt, new, rel, wrote) or not _clear(wt, rel, new, wrote):
            kept.append(rel)  # neither old nor new: written by someone else during pull-back
            continue
        if rel in was:
            git(wt, f"--attr-source={old}", "--literal-pathspecs", "checkout", old, "--", rel)
    return kept


def _reconcile(wt: Path, ref: str, span: tuple[str, str], paths: list[str], error: str) -> NoReturn:
    """Undo what a failed ``read-tree`` from ``span`` (old, new) wrote to *paths*, if the index is untouched.

    Raises:
        BehindError: Always; *error*, the local changes that appeared meanwhile, or the paths left to check.
    """
    old, new = span
    kept: list[str] = []
    if rev(wt, ref) == old and not _diff(wt, "--cached", old, "--", *paths):
        kept = _undo(wt, old, new, paths)
    if left := [p for p in _left(wt, old, paths) if p not in kept]:
        shown = " ".join(left[:SHOWN])
        msg = f"partial update: {shown} differ from {old[:12]}; check them, then retry after fixing {error}"
        raise BehindError(msg)
    if kept:
        error = f"{error}; local changes to {' '.join(kept[:SHOWN])} appeared during pull-back and were kept"
    raise BehindError(error)


def _unapply(wt: Path, ref: str, old: str, new: str, why: str) -> NoReturn:
    """The ref did not move: reverse the tree update if it is still safe, else name the exact recovery.

    Raises:
        BehindError: Always.
    """
    if rev(wt, ref) == old and git(wt, "symbolic-ref", "-q", "HEAD").stdout.strip() == ref:
        try:
            back = git(wt, "read-tree", "-m", "-u", new, old).returncode == 0
        except subprocess.TimeoutExpired, OSError:
            back = False
        if back:
            msg = f"{ref} did not move ({why}); the local copy was put back"
            raise BehindError(msg)
        msg = (
            f"manual check needed: {ref} is at {old[:12]} but the index and files may be partly at {new[:12]} "
            f"({why}); save any edits of your own to the files `git diff --name-only {old} {new}` lists, then run "
            f"`git diff --name-only --no-renames -z {old} {new} | git --literal-pathspecs "
            f"restore --source={old} --staged --worktree --pathspec-from-file=- --pathspec-file-nul`"
        )
        raise BehindError(msg)
    at = (rev(wt, ref) or "?")[:12]
    msg = (
        f"manual check needed: index and files are at {new[:12]} but {ref} is at {at} ({why}); "
        f"finish with `git update-ref {ref} {new} {old}` or undo with `git read-tree -m -u {new} {old}`"
    )
    raise BehindError(msg)


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
        _reconcile(wt, ref, (old, new), paths, "git timed out")
    if done.returncode != 0:
        _reconcile(wt, ref, (old, new), paths, first(done.stderr))
    try:
        done = git(wt, "update-ref", "-m", "pull-back: update to the merged change", ref, new, old)
        why = "" if done.returncode == 0 else first(done.stderr)
    except subprocess.TimeoutExpired:
        why = "git timed out"
    except OSError as exc:
        why = str(exc)
    if why:
        _unapply(wt, ref, old, new, why)
    if rev(wt, "HEAD") != new:
        msg = f"manual check needed: {ref} moved to {new[:12]} but HEAD is now elsewhere"
        raise BehindError(msg)
    return before
