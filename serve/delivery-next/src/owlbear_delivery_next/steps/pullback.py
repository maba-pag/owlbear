"""Pull-back: bring the local target branch up to the merged remote one without losing local work (TD-26).

The local copy is never assumed clean. With no worktree holding the target only its ref is fast-forwarded; with
several it stays behind; with one, that worktree is updated only if no local change (staged or not) and no
untracked or ignored file sits at, above or below a path the merged change brings in. A target that is only
behind is fast-forwarded with ``merge --ff-only``. Local commits (never merges) are replayed with ``cherry-pick``
onto the merged change in a temporary detached worktree, and the result is applied to the local copy by a two-tree
``read-tree -m -u`` (which keeps index entries and files of unchanged paths and refuses if a changing path has local
changes) and a compare-and-swap ``update-ref`` of the branch. The index
entries and file contents of every local change are compared before and after. No stash, pull, rebase or force;
any failed Git command leaves the target behind with its message.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from owlbear_delivery_next.git.remote_git import run_remote_git
from owlbear_delivery_next.models import Pullback
from owlbear_delivery_next.steps import engine, worktree

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

_IN_PROGRESS = ("MERGE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD", "REVERT_HEAD", "BISECT_LOG")
_HELD = ("rebase-merge/head-name", "rebase-apply/head-name", "BISECT_START")
_SHOWN = 5

type Local = dict[str, tuple[str, str]]


class _BehindError(Exception):
    """The target stays behind; the message is the reason."""


def _git(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed Git executable and argument vector
        [worktree.GIT, *args], cwd=path, capture_output=True, text=True, check=False, timeout=120
    )


def _first(stderr: str | bytes) -> str:
    text = stderr.decode(errors="replace") if isinstance(stderr, bytes) else stderr
    return next((line.strip() for line in text.splitlines() if line.strip()), "git failed")


def _must(path: Path, *args: str) -> str:
    """Stdout of a Git command that must succeed.

    Raises:
        _BehindError: The command failed; its first stderr line.
    """
    done = _git(path, *args)
    if done.returncode != 0:
        raise _BehindError(_first(done.stderr))
    return done.stdout


def _z(out: str) -> list[str]:
    return [p for p in out.split("\0") if p]


def _held(path: str) -> str | None:
    """The branch a detached worktree is rebasing or bisecting, as ``refs/heads/<name>``."""
    if not Path(path).is_dir():
        return None
    for name in _HELD:
        file = Path(path) / _git(Path(path), "rev-parse", "--git-path", name).stdout.strip()
        if file.is_file():
            ref = file.read_text(encoding="utf-8").strip()
            return ref if ref.startswith("refs/") else f"refs/heads/{ref}"
    return None


def holders(repo: Path, target: str) -> list[str]:
    """Every worktree that has *target* checked out or mid-rebase/bisect."""
    ref, path, found = f"refs/heads/{target}", None, []
    for line in _must(repo, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            path = line.removeprefix("worktree ")
        elif path and (line == f"branch {ref}" or (line == "detached" and _held(path) == ref)):
            found.append(path)
    return found


def _rev(path: Path, ref: str) -> str | None:
    done = _git(path, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    return done.stdout.strip() if done.returncode == 0 else None


def _submodules(path: Path, old: str | None, new: str | None) -> bool:
    """Whether a gitlink (mode 160000) changes between the local and the remote target."""
    if not old or not new or old == new:
        return False
    raw = _git(path, "diff", "--raw", "--no-renames", old, new).stdout.splitlines()
    return any("160000" in line.split("\t", 1)[0].split()[:2] for line in raw)


def _busy(wt: Path) -> str | None:
    """Why the holding worktree cannot be updated safely, or None."""
    if not wt.is_dir():
        return f"worktree {wt} is missing"
    for name in _IN_PROGRESS:
        if (wt / _must(wt, "rev-parse", "--git-path", name).strip()).exists():
            return "in progress"
    if _git(wt, "symbolic-ref", "-q", "HEAD").returncode != 0:
        return "detached HEAD"
    return None


def _incoming(wt: Path, base: str, remote: str) -> list[str]:
    """Paths the merged change touches, with both ends of a rename or copy."""
    fields, paths = iter(_z(_must(wt, "diff", "--name-status", "-z", "-M", base, remote))), []
    for code in fields:
        paths.append(next(fields, ""))
        if code[:1] in {"R", "C"}:
            paths.append(next(fields, ""))
    return [p for p in paths if p]


def _dirty(wt: Path) -> list[str]:
    """Tracked paths with staged or unstaged changes, with both ends of a rename or copy."""
    fields, paths = iter(_must(wt, "status", "--porcelain=v1", "-z", "--untracked-files=no").split("\0")), []
    for entry in fields:
        if path := entry[3:]:  # after the "XY " status columns
            paths.append(path)
            if {"R", "C"} & set(entry[:2]):
                paths.append(next(fields, ""))
    return [p for p in paths if p]


def _on_disk(wt: Path, rel: str, *, fold: bool) -> Path | None:
    """The filesystem entry at *rel*, matched case-insensitively when Git ignores case."""
    if not fold:
        return wt / rel if os.path.lexists(wt / rel) else None
    here = wt
    for part in PurePosixPath(rel).parts:
        try:
            names = [entry.name for entry in here.iterdir()]
        except OSError:
            return None
        if (match := next((n for n in names if n.casefold() == part.casefold()), None)) is None:
            return None
        here = here / match
    return here


def _untracked(wt: Path, chain: list[str], tracked: set[str], key: Callable[[str], str], *, fold: bool) -> bool:
    """Whether an entry not tracked in HEAD sits at the path (``chain[0]``) or as a non-directory above it."""
    for i, rel in enumerate(chain):
        entry = _on_disk(wt, rel, fold=fold)
        if entry is not None and key(rel) not in tracked and (i == 0 or entry.is_symlink() or not entry.is_dir()):
            return True
    return False


def _collisions(wt: Path, incoming: list[str], dirty: list[str], *, fold: bool) -> list[str]:
    """Incoming paths at, above or below a local change, or where an untracked or ignored entry exists."""
    key: Callable[[str], str] = str.casefold if fold else str
    tracked = {key(p) for p in _z(_must(wt, "ls-tree", "-r", "-z", "--name-only", "HEAD"))}
    local = {key(p) for p in dirty}
    above = {key(str(d)) for p in dirty for d in PurePosixPath(p).parents}
    hits = set()
    for path in incoming:
        chain = [path, *(str(d) for d in PurePosixPath(path).parents if str(d) != ".")]
        local_hit = key(path) in above or any(key(c) in local for c in chain)
        if local_hit or _untracked(wt, chain, tracked, key, fold=fold):
            hits.add(path)
    return sorted(hits)


def _digest(file: Path) -> str:
    try:
        data = str(file.readlink()).encode() if file.is_symlink() else file.read_bytes()
    except OSError:
        return ""
    return hashlib.sha256(data).hexdigest()


def _local(wt: Path, paths: list[str]) -> Local:
    """Index entries and working-file digest of each path."""
    if not paths:
        return {}
    index: dict[str, str] = {}
    for entry in _z(_must(wt, "--literal-pathspecs", "ls-files", "-s", "-z", "--", *paths)):
        meta, _, path = entry.partition("\t")
        index[path] = f"{index.get(path, '')}{meta};"
    return {p: (index.get(p, ""), _digest(wt / p)) for p in paths}


def _guard(wt: Path, incoming: list[str], *, fold: bool) -> Local:
    """The state of every local change, unless one collides with the merged change.

    Raises:
        _BehindError: A local path collides.
    """
    dirty = _dirty(wt)
    if hits := _collisions(wt, incoming, dirty, fold=fold):
        msg = f"your local changes to {', '.join(hits[:_SHOWN])} overlap the merged change"
        raise _BehindError(msg)
    return _local(wt, dirty)


def _checked(wt: Path, reason: str, before: Local) -> tuple[str, str]:
    """``updated``, noting local changes whose index entry or content differs from *before*."""
    after = _local(wt, list(before))
    if moved := [p for p in before if after.get(p) != before[p]]:
        return "updated", f"{reason}; manual check needed: {', '.join(moved[:_SHOWN])}"
    return "updated", reason


def _replay(wt: Path, base: str, old: str, remote: str) -> str:
    """Cherry-pick ``base..old`` onto *remote* in a temporary detached worktree; the new head.

    Raises:
        _BehindError: Local merges, a conflict or any other failure; the temporary worktree is removed.
    """
    if _must(wt, "rev-list", "--merges", f"{remote}..{old}").strip():
        msg = "local merge commits; pull manually"
        raise _BehindError(msg)
    tmp = Path(tempfile.mkdtemp(prefix="owlbear-pullback-"))
    try:
        _must(wt, "worktree", "add", "--quiet", "--detach", str(tmp), remote)
        done = _git(tmp, "cherry-pick", f"{base}..{old}")
        if done.returncode != 0:
            conflict = bool(_git(tmp, "ls-files", "-u").stdout.strip())
            _git(tmp, "cherry-pick", "--abort")
            raise _BehindError(
                "your local commits conflict with the merged change" if conflict else _first(done.stderr)
            )
        return _must(tmp, "rev-parse", "HEAD").strip()
    finally:
        _git(wt, "worktree", "remove", "--force", str(tmp))
        _git(wt, "worktree", "prune")
        shutil.rmtree(tmp, ignore_errors=True)


def _apply(wt: Path, old: str, new: str, incoming: list[str], *, fold: bool) -> Local:
    """Move the branch and local copy from *old* to *new* by a two-tree merge; the local state checked against.

    ``read-tree -m -u`` carries forward index entries and files of paths equal in both trees, refuses before
    writing if a differing path has local changes or an untracked or ignored file is in the way, and runs no hook;
    ``update-ref`` then moves the branch only if it is still *old*. ``reset --keep`` would drop staged contents.

    Raises:
        _BehindError: HEAD moved, a local path now collides, or Git refused.
    """
    branch = _must(wt, "symbolic-ref", "-q", "HEAD").strip()
    if _rev(wt, "HEAD") != old:
        msg = "HEAD moved during pull-back"
        raise _BehindError(msg)
    before = _guard(wt, incoming, fold=fold)
    _must(wt, "read-tree", "-m", "-u", old, new)
    done = _git(wt, "update-ref", "-m", "pull-back: replay onto the merged change", branch, new, old)
    if done.returncode != 0 or _rev(wt, "HEAD") != new:
        msg = f"manual check needed: files are at {new} but {branch} did not move: {_first(done.stderr)}"
        raise _BehindError(msg)
    return before


def _pull(wt: Path, remote: str) -> tuple[str, str]:
    """Update the one worktree holding the target to *remote*.

    Raises:
        _BehindError: Any precondition, collision or Git failure.
    """
    if reason := _busy(wt):
        raise _BehindError(reason)
    old = _must(wt, "rev-parse", "--verify", "HEAD").strip()
    if engine.contains(wt, remote, old):
        return "updated", "already up to date"
    base = _must(wt, "merge-base", old, remote).strip()
    incoming = _incoming(wt, base, remote)
    fold = _git(wt, "config", "--bool", "core.ignorecase").stdout.strip() == "true"
    if base == old:
        before = _guard(wt, incoming, fold=fold)
        _must(wt, "merge", "--quiet", "--ff-only", "--no-autostash", "--no-overwrite-ignore", remote)
        return _checked(wt, "fast-forwarded", before)
    _guard(wt, incoming, fold=fold)
    count = _must(wt, "rev-list", "--count", f"{base}..{old}").strip()
    new = _replay(wt, base, old, remote)
    before = _apply(wt, old, new, incoming, fold=fold)
    return _checked(wt, f"replayed {count} local commits onto the merged change", before)


def _ref_only(repo: Path, target: str) -> tuple[str, str]:
    """Fast-forward a *target* branch no worktree has checked out."""
    if _rev(repo, f"refs/heads/{target}") is None:
        return "updated", f"no local {target} branch; origin/{target} updated"
    done = run_remote_git(repo, ("fetch", "--quiet", "--no-tags", "origin", f"{target}:{target}"), kind="read")
    return ("updated", "") if done.returncode == 0 else ("behind", _first(done.stderr))


def _update(repo: Path, target: str, held: list[str]) -> tuple[str, str]:
    """Bring local *target* up to ``origin/<target>``: ``(state, reason)``."""
    if not held:
        return _ref_only(repo, target)
    if len(held) > 1:
        return "behind", f"{target} is checked out in {len(held)} worktrees"
    try:
        return _pull(Path(held[0]), f"origin/{target}")
    except _BehindError as exc:
        return "behind", str(exc)
    except subprocess.TimeoutExpired:
        return "behind", "git timed out"


def run(repo: Path, target: str, now: datetime) -> Pullback:
    """Fetch the target and update the local branch; never pull, stash, rebase, force or merge with a commit."""
    try:
        engine.fetch(repo, target)
        held = holders(repo, target)
    except (engine.RemoteGitFailed, _BehindError) as exc:
        return Pullback(state="behind", reason=f"local {target} is behind: {_first(str(exc))}", at=now)
    old, new = _rev(repo, f"refs/heads/{target}"), _rev(repo, f"origin/{target}")
    state, why = _update(repo, target, held)
    if _submodules(repo, old, new):
        why = f"{why}; submodules changed" if why else "submodules changed"
    reason = f"local {target} is behind: {why}" if state == "behind" else why
    return Pullback(state=state, reason=reason, worktree=held[0] if len(held) == 1 else "", at=now)
