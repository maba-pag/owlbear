"""Pull-back: bring the local target branch up to the merged remote one without losing local work (TD-26).

A checked-out target may be dirty. Local changes, untracked or ignored files at a path the merge brings in leave
it behind and untouched. Otherwise a target that is only behind is fast-forwarded; one with local commits is
rebased with Git's autostash, which cannot conflict because the stashed and the incoming paths are disjoint. A
failed rebase is aborted and the restored HEAD, branch and local files verified. Never pull, reset or force.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from owlbear_delivery_next.git.remote_git import run_remote_git
from owlbear_delivery_next.models import Pullback
from owlbear_delivery_next.steps import engine, worktree

if TYPE_CHECKING:
    from datetime import datetime

_IN_PROGRESS = ("MERGE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD", "REVERT_HEAD", "BISECT_LOG")
_HELD = ("rebase-merge/head-name", "rebase-apply/head-name", "BISECT_START")
_REBASE = ("-c", "rebase.autoStash=true", "-c", "rebase.autoSquash=false", "-c", "rebase.updateRefs=false")
_SHOWN = 5

type Snapshot = tuple[str | None, str | None, dict[str, str]]


def _git(path: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed Git executable and argument vector
        [worktree.GIT, *args], cwd=path, input=stdin, capture_output=True, text=True, check=False, timeout=120
    )


def _z(out: str) -> list[str]:
    return [p for p in out.split("\0") if p]


def _first(stderr: str | bytes) -> str:
    text = stderr.decode(errors="replace") if isinstance(stderr, bytes) else stderr
    return next((line.strip() for line in text.splitlines() if line.strip()), "git failed")


def _held(path: str) -> str | None:
    """The branch a detached worktree is rebasing or bisecting, as ``refs/heads/<name>``."""
    for name in _HELD:
        file = Path(path) / _git(Path(path), "rev-parse", "--git-path", name).stdout.strip()
        if file.is_file():
            ref = file.read_text(encoding="utf-8").strip()
            return ref if ref.startswith("refs/") else f"refs/heads/{ref}"
    return None


def checked_out(repo: Path, target: str) -> str | None:
    """The worktree that has *target* checked out or mid-rebase/bisect, from ``git worktree list --porcelain``."""
    path = None
    for line in _git(repo, "worktree", "list", "--porcelain").stdout.splitlines():
        if line.startswith("worktree "):
            path = line.removeprefix("worktree ")
        elif line == f"branch refs/heads/{target}" or (
            line == "detached" and path and _held(path) == f"refs/heads/{target}"
        ):
            return path
    return None


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
    """Why the checked-out worktree cannot be updated safely, or None."""
    for name in _IN_PROGRESS:
        rel = _git(wt, "rev-parse", "--git-path", name).stdout.strip()
        if rel and (wt / rel).exists():
            return "in progress"
    if _git(wt, "symbolic-ref", "-q", "HEAD").returncode != 0:
        return "detached HEAD"
    return None


def _local(wt: Path) -> list[str]:
    """Changed (staged or not) and untracked paths, with both ends of a rename or copy."""
    fields = iter(_git(wt, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout.split("\0"))
    paths = []
    for entry in fields:
        if path := entry[3:]:  # after the "XY " status columns
            paths.append(path)
            if {"R", "C"} & set(entry[:2]):
                paths.append(next(fields, ""))
    return [p for p in paths if p]


def _overlap(wt: Path, remote: str, local: list[str]) -> list[str]:
    """Local paths, and ignored files, that the merged change also touches."""
    incoming = set(_z(_git(wt, "diff", "--name-only", "-z", "--no-renames", f"HEAD...{remote}").stdout))
    if not incoming:
        return []
    spec = "\0".join(sorted(incoming))
    args = ("--literal-pathspecs", "ls-files", "-z", "--others", "--ignored", "--exclude-standard")
    ignored = _z(_git(wt, *args, "--pathspec-from-file=-", "--pathspec-file-nul", stdin=spec).stdout)
    dirs = {str(d) for p in incoming for d in PurePosixPath(p).parents}
    return sorted(
        p
        for p in {*local, *ignored}
        if p in incoming or p in dirs or any(str(d) in incoming for d in PurePosixPath(p).parents)
    )


def _digest(file: Path) -> str:
    try:
        data = str(file.readlink()).encode() if file.is_symlink() else file.read_bytes()
    except OSError:
        return ""
    return hashlib.sha256(data).hexdigest()


def _snapshot(wt: Path, target: str, local: list[str]) -> Snapshot:
    return _rev(wt, "HEAD"), _rev(wt, f"refs/heads/{target}"), {p: _digest(wt / p) for p in local}


def _unverified(wt: Path, target: str, before: Snapshot, after: Snapshot) -> str:
    """Describe what differs from the pre-rebase state; the autostash, if any, is left in ``git stash list``."""
    parts = [f"{what} moved" for what, old, new in zip(("HEAD", target), before, after, strict=False) if old != new]
    if changed := [p for p, digest in before[2].items() if after[2].get(p) != digest]:
        parts.append(f"local files differ: {', '.join(changed[:_SHOWN])}")
    if busy := _busy(wt):
        parts.append(f"operation {busy}")
    return f"manual check needed: {'; '.join(parts) or 'state unknown'}; see git status and git stash list"


def _rebase(wt: Path, target: str, remote: str, local: list[str]) -> tuple[str, str]:
    before = _snapshot(wt, target, local)
    count = _git(wt, "rev-list", "--count", f"{remote}..HEAD").stdout.strip()
    done = _git(wt, *_REBASE, "rebase", "--no-fork-point", remote)
    if done.returncode == 0:
        after = _snapshot(wt, target, local)
        if after[2] != before[2] or _busy(wt):
            return "behind", _unverified(wt, target, (*after[:2], before[2]), after)
        return "updated", f"rebased {count} local commits"
    _git(wt, "rebase", "--abort")
    after = _snapshot(wt, target, local)
    if after != before or _busy(wt):
        return "behind", _unverified(wt, target, before, after)
    return "behind", f"rebase undone: {_first(done.stderr)}"


def _ref_only(repo: Path, target: str) -> tuple[str, str]:
    """Fast-forward a *target* branch no worktree has checked out."""
    if _rev(repo, f"refs/heads/{target}") is None:
        return "updated", f"no local {target} branch; origin/{target} updated"
    done = run_remote_git(repo, ("fetch", "--quiet", "--no-tags", "origin", f"{target}:{target}"), kind="read")
    return ("updated", "") if done.returncode == 0 else ("behind", _first(done.stderr))


def _update(repo: Path, target: str, wt: str | None) -> tuple[str, str]:
    """Bring local *target* up to ``origin/<target>``: ``(state, reason)``."""
    remote = f"origin/{target}"
    if wt is None:
        return _ref_only(repo, target)
    path = Path(wt)
    if reason := _busy(path):
        return "behind", reason
    if engine.contains(path, remote, "HEAD"):
        return "updated", "already up to date"
    local = _local(path)
    if hits := _overlap(path, remote, local):
        return "behind", f"your local changes to {', '.join(hits[:_SHOWN])} overlap the merged change"
    if not engine.contains(path, "HEAD", remote):
        return _rebase(path, target, remote, local)
    done = _git(path, "merge", "--ff-only", "--no-autostash", "--no-overwrite-ignore", remote)
    return ("updated", "") if done.returncode == 0 else ("behind", _first(done.stderr))


def run(repo: Path, target: str, now: datetime) -> Pullback:
    """Fetch the target and update the local branch; never pull, reset, force or merge with a commit."""
    try:
        engine.fetch(repo, target)
    except engine.RemoteGitFailed as exc:
        return Pullback(state="behind", reason=f"local {target} is behind: {_first(str(exc))}", at=now)
    wt = checked_out(repo, target)
    old, new = _rev(repo, f"refs/heads/{target}"), _rev(repo, f"origin/{target}")
    state, why = _update(repo, target, wt)
    if _submodules(repo, old, new):
        why = f"{why}; submodules changed" if why else "submodules changed"
    reason = f"local {target} is behind: {why}" if state == "behind" else why
    return Pullback(state=state, reason=reason, worktree=wt or "", at=now)
