"""The Change worktree under the user data root, its packages' install commands and its observed state (D4 §3.2)."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.tools import Worktree

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_delivery_next.models import Profile

GIT = shutil.which("git") or "git"


def git(cwd: Path, *args: str) -> str:
    """Run one Git command, bounded so a hung Git cannot stall a step, and return its standard output."""
    return subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
        [GIT, *args], cwd=cwd, capture_output=True, text=True, check=True, timeout=60
    ).stdout


def data_root() -> Path:
    """Return the one user data root that holds every worktree, so folder trust is granted once (P8)."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "OwlBear" / "worktrees"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "owlbear" / "worktrees"


def path_for(common_dir: Path, slug: str) -> Path:
    """Return the worktree path, keyed by repository name and a short hash of the common git directory."""
    key = hashlib.sha256(str(common_dir).encode()).hexdigest()[:8]
    return data_root() / f"{common_dir.parent.name}-{key}" / slug


def ensure(repo: Path, common_dir: Path, slug: str, branch: str, target: str) -> Path:
    """Return the Change worktree, creating it and its branch from *target* when absent."""
    path = path_for(common_dir, slug)
    if (path / ".git").exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    git(repo, "worktree", "prune")
    exists = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
        [GIT, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=repo, capture_output=True, check=False
    )
    args = [str(path), branch] if exists.returncode == 0 else ["-b", branch, str(path), tracking(repo, target)]
    git(repo, "worktree", "add", *args)
    return path


def tracking(cwd: Path, target: str) -> str:
    """``origin/<target>`` when it exists, else *target*: the local branch can lag behind merged work."""
    ref = f"refs/remotes/origin/{target}"
    found = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
        [GIT, "rev-parse", "--verify", "--quiet", ref], cwd=cwd, capture_output=True, check=False
    )
    return f"origin/{target}" if found.returncode == 0 else target


def allowed(profile: Profile, kind: str) -> list[str]:
    """Return the profile's extra shell commands for one step kind; for ``check`` they are the launch commands."""
    extra = profile.entries.get(f"allow:{kind}")
    return extra.value.split("\n") if extra else []


def installs(profile: Profile, scope: Sequence[str]) -> list[tuple[str, str]]:
    """Return ``(package, command)`` per known install entry holding a scope path; the Builder runs them (DR3)."""
    found = []
    for key, entry in profile.entries.items():
        package = key.removeprefix("install:")
        if key == package or entry.state != "known":
            continue
        prefix = package.strip("/") + "/"
        if package in {"", "."} or any(p.strip("/") == package.strip("/") or p.startswith(prefix) for p in scope):
            found.append((package, entry.value))
    return found


def checks(profile: Profile) -> list[tuple[str, str]]:
    """Return ``(package, command)`` per known check entry of the profile; plans may name only these commands."""
    found = ((k.removeprefix("check:"), e) for k, e in profile.entries.items() if k.startswith("check:"))
    return sorted((p, e.value) for p, e in found if e.state == "known" and e.value)


def head(path: Path) -> str:
    """Return the worktree's HEAD commit."""
    return git(path, "rev-parse", "HEAD").strip()


def observe(path: Path, target: str, since: str | None = None) -> Worktree:
    """Read the worktree's head, its base, uncommitted paths and paths changed since the base.

    The base is *since* (a task's start) when given, else the merge base on *target*. Paths a target merge
    brought in, unchanged against the target, are not the task's changes.
    """
    head_ = head(path)
    base = git(path, "merge-base", "HEAD", tracking(path, target)).strip()
    status = git(path, "status", "--porcelain=v1", "--untracked-files=all").splitlines()
    changed = diff(path, base)
    if since:
        task = set(diff(path, since))
        base, changed = since, [p for p in changed if p in task]
    return Worktree(head=head_, base=base, dirty=tuple(line[3:] for line in status), changed=tuple(changed))


def diff(path: Path, base: str, rev: str = "HEAD") -> list[str]:
    """Paths added, modified or deleted from *base* to *rev*, both ends of a rename included (F3)."""
    lines = git(path, "diff", "--name-status", "-M", f"{base}...{rev}").splitlines()
    return list(dict.fromkeys(p for line in lines for p in line.split("\t")[1:]))


def tree(path: Path, rev: str = "HEAD") -> str:
    """Return the tree id of *rev*: equal trees are equal content whatever the commit."""
    return git(path, "rev-parse", f"{rev}^{{tree}}").strip()


def between(path: Path, old: str, new: str) -> list[str]:
    """Every path that differs between two trees, both rename ends included, read NUL-separated."""
    fields = git(path, "diff", "--name-status", "-M", "-z", old, new).split("\0")
    out, i = [], 0
    while i < len(fields) and fields[i]:
        n = 2 if fields[i][0] in "RC" else 1
        out += fields[i + 1 : i + 1 + n]
        i += 1 + n
    return list(dict.fromkeys(out))


def fingerprints(path: Path, paths: Sequence[str], rev: str = "HEAD") -> dict[str, str]:
    """Return ``<mode> <type> <oid>`` at *rev* of every file at or under each path, an absent path as ``""``.

    The review and check input that voids an answer when content, mode or presence changes (P5).
    """
    wanted = list(dict.fromkeys(p.strip("/") for p in paths))
    inside = [p for p in wanted if p and not Path(p).is_absolute() and ".." not in Path(p).parts]
    out = git(path, "--literal-pathspecs", "ls-tree", "-r", "-z", "--full-tree", rev, "--", *inside) if inside else ""
    found: dict[str, str] = {}
    for entry in filter(None, out.split("\0")):
        meta, name = entry.split("\t", 1)
        found[name] = meta
    absent = {p: "" for p in wanted if p not in found and not any(k.startswith(f"{p}/") for k in found)}
    return found | absent
