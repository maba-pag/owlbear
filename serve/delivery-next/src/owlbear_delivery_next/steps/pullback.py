"""Pull-back: bring the local target branch up to the merged remote one without losing local work (TD-26).

The local copy is never assumed clean. With no worktree holding the target only its ref is fast-forwarded; with
several it stays behind; with one, that worktree is updated only if no local change (staged or not) and no
untracked or ignored file sits at, above or below a path the update itself changes (``pullback_replay`` applies
it, after replaying any local commits). The index entries and file contents of every local change are compared
before and after. No stash, pull, rebase or force; any failed or timed-out Git command leaves the target behind
with its message.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from owlbear_delivery_next.git.remote_git import RemoteGitError, run_remote_git
from owlbear_delivery_next.models import Pullback
from owlbear_delivery_next.steps import engine, pullback_replay
from owlbear_delivery_next.steps.pullback_replay import SHOWN, BehindError, Local, first, git, must, rev, split_z

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

_IN_PROGRESS = ("MERGE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD", "REVERT_HEAD", "BISECT_LOG")
_HELD = ("rebase-merge/head-name", "rebase-apply/head-name", "BISECT_START")
_FAILURES = (subprocess.TimeoutExpired, RemoteGitError, BehindError, OSError)


def _held(path: str) -> str | None:
    """The branch a detached worktree is rebasing or bisecting, as ``refs/heads/<name>``."""
    if not Path(path).is_dir():
        return None
    for name in _HELD:
        file = Path(path) / git(Path(path), "rev-parse", "--git-path", name).stdout.strip()
        if file.is_file():
            ref = file.read_text(encoding="utf-8").strip()
            return ref if ref.startswith("refs/") else f"refs/heads/{ref}"
    return None


def holders(repo: Path, target: str) -> list[str]:
    """Every worktree that has *target* checked out or mid-rebase/bisect."""
    ref, path, found = f"refs/heads/{target}", None, []
    for line in must(repo, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            path = line.removeprefix("worktree ")
        elif path and (line == f"branch {ref}" or (line == "detached" and _held(path) == ref)):
            found.append(path)
    return found


def _submodules(path: Path, old: str | None, new: str | None) -> bool:
    """Whether a gitlink (mode 160000) changes between the local and the remote target."""
    if not old or not new or old == new:
        return False
    raw = git(path, "diff", "--raw", "--no-renames", old, new).stdout.splitlines()
    return any("160000" in line.split("\t", 1)[0].split()[:2] for line in raw)


def _busy(wt: Path) -> str | None:
    """Why the holding worktree cannot be updated safely, or None."""
    if not wt.is_dir():
        return f"worktree {wt} is missing"
    for name in _IN_PROGRESS:
        if (wt / must(wt, "rev-parse", "--git-path", name).strip()).exists():
            return "in progress"
    if git(wt, "symbolic-ref", "-q", "HEAD").returncode != 0:
        return "detached HEAD"
    return None


def _dirty(wt: Path) -> list[str]:
    """Tracked paths with staged or unstaged changes, with both ends of a rename or copy."""
    fields, paths = iter(must(wt, "status", "--porcelain=v1", "-z", "--untracked-files=no").split("\0")), []
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
    tracked = {key(p) for p in split_z(must(wt, "ls-tree", "-r", "-z", "--name-only", "HEAD"))}
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
    for entry in split_z(must(wt, "--literal-pathspecs", "ls-files", "-s", "-z", "--", *paths)):
        meta, _, path = entry.partition("\t")
        index[path] = f"{index.get(path, '')}{meta};"
    return {p: (index.get(p, ""), _digest(wt / p)) for p in paths}


def _guard(wt: Path, incoming: list[str], *, fold: bool) -> Local:
    """The state of every local change, unless one collides with a path the update changes.

    Raises:
        BehindError: A local path collides.
    """
    dirty = _dirty(wt)
    if hits := _collisions(wt, incoming, dirty, fold=fold):
        msg = f"your local changes to {', '.join(hits[:SHOWN])} overlap the merged change"
        raise BehindError(msg)
    return _local(wt, dirty)


def _checked(wt: Path, reason: str, before: Local) -> tuple[str, str]:
    """``updated``, noting local changes whose index entry or content differs from *before*."""
    after = _local(wt, list(before))
    if moved := [p for p in before if after.get(p) != before[p]]:
        return "updated", f"{reason}; manual check needed: {', '.join(moved[:SHOWN])}"
    return "updated", reason


def _pull(wt: Path, target: str) -> tuple[str, str]:
    """Update the one worktree holding *target* to ``origin/<target>``.

    Raises:
        BehindError: Any precondition, collision or Git failure.
    """
    if reason := _busy(wt):
        raise BehindError(reason)
    ref = f"refs/heads/{target}"
    if git(wt, "symbolic-ref", "-q", "HEAD").stdout.strip() != ref:
        msg = f"{target} is no longer checked out in {wt}"
        raise BehindError(msg)
    old = must(wt, "rev-parse", "--verify", f"{ref}^{{commit}}").strip()
    remote = must(wt, "rev-parse", "--verify", f"origin/{target}^{{commit}}").strip()
    if engine.contains(wt, remote, old):
        return "updated", "already up to date"
    base = must(wt, "merge-base", old, remote).strip()
    fold = git(wt, "config", "--bool", "core.ignorecase").stdout.strip() == "true"

    def guard(paths: list[str]) -> Local:
        return _guard(wt, paths, fold=fold)

    if base == old:
        return _checked(wt, "fast-forwarded", pullback_replay.apply(wt, ref, old, remote, guard))
    count = must(wt, "rev-list", "--count", f"{base}..{old}").strip()
    new, note = pullback_replay.replay(wt, base, old, remote)
    try:
        before = pullback_replay.apply(wt, ref, old, new, guard)
    except BehindError as exc:
        raise BehindError("; ".join(filter(None, (str(exc), note)))) from exc
    state, reason = _checked(wt, f"replayed {count} local commits onto the merged change", before)
    return state, "; ".join(filter(None, (reason, note)))


def _ref_only(repo: Path, target: str) -> tuple[str, str]:
    """Fast-forward a *target* branch no worktree has checked out."""
    if rev(repo, f"refs/heads/{target}") is None:
        return "updated", f"no local {target} branch; origin/{target} updated"
    done = run_remote_git(repo, ("fetch", "--quiet", "--no-tags", "origin", f"{target}:{target}"), kind="read")
    return ("updated", "") if done.returncode == 0 else ("behind", first(done.stderr))


def _update(repo: Path, target: str) -> tuple[str, str, list[str]]:
    """Fetch and bring local *target* up to ``origin/<target>``: ``(state, reason, holders)``."""
    engine.fetch(repo, target)
    held = holders(repo, target)
    old, new = rev(repo, f"refs/heads/{target}"), rev(repo, f"origin/{target}")
    note = "submodules changed" if _submodules(repo, old, new) else ""
    if not held:
        state, why = _ref_only(repo, target)
    elif len(held) > 1:
        state, why = "behind", f"{target} is checked out in {len(held)} worktrees"
    else:
        try:
            state, why = _pull(Path(held[0]), target)
        except _FAILURES as exc:
            state, why = "behind", _reason(exc)
    return state, "; ".join(filter(None, (why, note))), held


def _reason(exc: Exception) -> str:
    return "git timed out" if isinstance(exc, subprocess.TimeoutExpired) else first(str(exc))


def run(repo: Path, target: str, now: datetime) -> Pullback:
    """Fetch the target and update the local branch; never pull, stash, rebase, force or merge with a commit."""
    try:
        state, why, held = _update(repo, target)
    except _FAILURES as exc:
        state, why, held = "behind", _reason(exc), []
    reason = f"local {target} is behind: {why}" if state == "behind" else why
    return Pullback(state=state, reason=reason, worktree=held[0] if len(held) == 1 else "", at=now)
