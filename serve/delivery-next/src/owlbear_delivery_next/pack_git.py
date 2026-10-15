"""Activating a design pack update in the package's own checkout (TD-101): one commit, pushed on its branch alone.

The update writes only the manifest and the skills' notice, commits exactly those files on the checkout's current
branch, and pushes that one commit to the branch's own remote branch, never forced. It refuses a checkout that is not
git, has a detached head or no upstream, holds uncommitted changes to tracked files, or has commits not yet pushed.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next import design_pack

if TYPE_CHECKING:
    from collections.abc import Callable

type Git = Callable[[Path, list[str]], str]


def git(cwd: Path, args: list[str]) -> str:
    """One git command in *cwd*; its output, or a PackError with git's own words."""
    quiet = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}  # a host thread never waits on a credential prompt
    try:
        done = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=cwd, env=quiet, stdin=subprocess.DEVNULL, capture_output=True, text=True, check=True, timeout=120,
        )  # fmt: skip
    except subprocess.CalledProcessError as exc:
        msg = f"git {args[0]} failed: {(exc.stderr or exc.stdout).strip()[:300] or f'exit {exc.returncode}'}"
        raise design_pack.PackError(msg) from exc
    except (OSError, subprocess.TimeoutExpired) as exc:
        msg = f"git {args[0]} did not run: {exc}"
        raise design_pack.PackError(msg) from exc
    return done.stdout.strip()


@dataclass(frozen=True)
class Checkout:
    """The package's checkout: its root, current branch, and the remote and remote branch that branch pushes to."""

    root: Path
    branch: str
    remote: str
    merge: str  # the remote branch, such as refs/heads/next/m4-slice1


def checkout(package: Path, run: Git = git) -> Checkout:
    """The package's checkout, when an update may commit and push in it.

    Raises:
        design_pack.PackError: Why it may not, in words the owner can act on.
    """
    try:
        root = run(package, ["rev-parse", "--show-toplevel"])
    except design_pack.PackError as exc:
        msg = f"the package at {package} is not a git checkout, so an update cannot be committed: {exc}"
        raise design_pack.PackError(msg) from exc
    top = Path(root)
    branch = _quiet(run, top, ["symbolic-ref", "--quiet", "--short", "HEAD"])
    if not branch:
        msg = f"the checkout {top} has a detached head; switch to the branch an update should commit on"
        raise design_pack.PackError(msg)
    remote = _quiet(run, top, ["config", f"branch.{branch}.remote"])
    merge = _quiet(run, top, ["config", f"branch.{branch}.merge"])
    if not remote or not merge:
        msg = f"the branch {branch} has no upstream to push to; set one with `git push -u` first"
        raise design_pack.PackError(msg)
    if dirty := run(top, ["status", "--porcelain", "--untracked-files=no"]):
        msg = f"the checkout {top} has uncommitted changes, commit or stash them first: {dirty.splitlines()[0]} …"
        raise design_pack.PackError(msg)
    if (ahead := run(top, ["rev-list", "--count", "@{upstream}..HEAD"])) != "0":
        msg = (
            f"the branch {branch} has {ahead} commit(s) not pushed; push them first, so the update pushes only its own"
        )
        raise design_pack.PackError(msg)
    return Checkout(top, branch, remote, merge)


def _quiet(run: Git, cwd: Path, args: list[str]) -> str:
    try:
        return run(cwd, args)
    except design_pack.PackError:
        return ""


def activate(co: Checkout, files: dict[Path, str], message: str, run: Git = git) -> str:
    """Write *files*, commit exactly them on the branch, and return the commit; on failure restore them unchanged.

    Raises:
        design_pack.PackError: The branch moved or the commit failed; nothing is left changed.
    """
    again = checkout(co.root, run)
    if again != co:
        msg = f"the checkout changed during the update (now {again.branch}); nothing was activated"
        raise design_pack.PackError(msg)
    before = run(co.root, ["rev-parse", "HEAD"])
    kept = {path: path.read_bytes() for path in files}
    try:
        for path, text in files.items():
            path.write_text(text, encoding="utf-8")
        names = [str(path.relative_to(co.root)) for path in files]
        run(co.root, ["add", "--", *names])
        run(co.root, ["commit", "--quiet", "-m", message, "--", *names])
        made = run(co.root, ["rev-parse", "HEAD"])
        if run(co.root, ["rev-parse", f"{made}^"]) != before:
            msg = "the commit did not land on the branch head it started from"
            raise design_pack.PackError(msg)  # noqa: TRY301 - the restore below undoes this commit too
    except BaseException:
        for path, data in kept.items():
            path.write_bytes(data)
        _quiet(run, co.root, ["reset", "--quiet", "--", *[str(p.relative_to(co.root)) for p in files]])
        if _quiet(run, co.root, ["rev-parse", "HEAD"]) not in {before, ""}:
            _quiet(run, co.root, ["reset", "--quiet", "--keep", before])
        raise
    return made


def push(co: Checkout, commit: str, run: Git = git) -> str:
    """Push exactly *commit* to the branch's own remote branch, never forced; on failure take the commit back.

    Raises:
        design_pack.PackError: The push was refused; the local commit is undone so the old pack stays active.
    """
    try:
        return run(co.root, ["push", "--quiet", co.remote, f"{commit}:{co.merge}"])
    except design_pack.PackError as exc:
        undone = run(co.root, ["rev-parse", "HEAD"]) == commit and _undo(co, commit, run)
        tail = "the local commit was undone" if undone else f"the local commit {commit[:12]} is still there"
        msg = f"{exc}; {tail}"
        raise design_pack.PackError(msg) from exc


def _undo(co: Checkout, commit: str, run: Git) -> bool:
    try:
        run(co.root, ["reset", "--quiet", "--keep", f"{commit}^"])
    except design_pack.PackError:
        return False
    return True
