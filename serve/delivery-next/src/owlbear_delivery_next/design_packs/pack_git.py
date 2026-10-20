"""A design pack update's commit (TD-101, step 3c): one commit on its own branch, from a clean checkout of main.

The package's own Git checkout stands in for the runtime's repository: its ``origin`` must be OwlBear's repository,
its tracked files clean and its ``HEAD``, pinned when the candidate is made, on the freshly fetched ``origin/main``.
The commit is made in a disposable worktree at that pinned commit, so the running checkout is never touched, and
pushed to its own branch, never forced. A pull request takes it to ``main`` (``pack_publish``).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.design_packs import design_pack

if TYPE_CHECKING:
    from collections.abc import Callable

type Git = Callable[[Path, list[str]], str]
REPOSITORY = "maba-pag/owlbear"  # where OwlBear's own design pack lives (TD-101)
BASE = "main"
_SLUG = re.compile(r"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([\w.-]+/[\w.-]+?)(?:\.git)?/?")


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
class Source:
    """The package's checkout: its root, the repository its ``origin`` names and the commit pinned as the base."""

    root: Path
    repository: str
    base: str


def source(package: Path, run: Git = git, repository: str = REPOSITORY) -> Source:
    """The package's checkout, when an update may be committed from it; its ``HEAD`` pinned.

    Raises:
        design_pack.PackError: Why it may not, in words the owner can act on.
    """
    try:
        top = Path(run(package, ["rev-parse", "--show-toplevel"]))
    except design_pack.PackError as exc:
        msg = f"the package at {package} is not a git checkout, so an update cannot be committed: {exc}"
        raise design_pack.PackError(msg) from exc
    url = _quiet(run, top, ["config", "--get", "remote.origin.url"])  # as written, before any insteadOf
    if (found := _SLUG.fullmatch(url)) is None or found[1].casefold() != repository.casefold():
        msg = f"the checkout {top} has origin {url or 'none'}; a pack update goes to {repository} in a pull request"
        raise design_pack.PackError(msg)
    if dirty := run(top, ["status", "--porcelain", "--untracked-files=no"]):
        msg = f"the checkout {top} has uncommitted changes, commit or stash them first: {dirty.splitlines()[0]} …"
        raise design_pack.PackError(msg)
    run(top, ["fetch", "--quiet", "origin", BASE])
    head = run(top, ["rev-parse", "HEAD"])
    if not _holds(run, top, head, f"origin/{BASE}"):
        msg = f"the checkout {top} is at {head[:12]}, which is not on {BASE}; check out {BASE} or a commit on it"
        raise design_pack.PackError(msg)
    return Source(top, repository, head)


def _quiet(run: Git, cwd: Path, args: list[str]) -> str:
    try:
        return run(cwd, args)
    except design_pack.PackError:
        return ""


def commit(src: Source, files: dict[str, str], message: str, at: Path, run: Git = git) -> str:
    """Commit exactly *files* (paths in the checkout) on the pinned base, in a disposable worktree at *at*."""
    shutil.rmtree(at, ignore_errors=True)
    _quiet(run, src.root, ["worktree", "prune"])
    run(src.root, ["worktree", "add", "--quiet", "--detach", str(at), src.base])
    try:
        for name, text in files.items():
            (at / name).write_text(text, encoding="utf-8")
        run(at, ["add", "--", *files])
        run(at, ["commit", "--quiet", "-m", message, "--", *files])
        return run(at, ["rev-parse", "HEAD"])
    finally:
        _quiet(run, src.root, ["worktree", "remove", "--force", str(at)])
        shutil.rmtree(at, ignore_errors=True)


def remote_head(src: Source, branch: str, run: Git = git) -> str:
    """The commit *branch* holds on ``origin``, or "" when it is not there."""
    said = run(src.root, ["ls-remote", "origin", f"refs/heads/{branch}"])
    return said.split()[0] if said else ""


def push(src: Source, made: str, branch: str, run: Git = git) -> None:
    """Push exactly *made* to its own branch on ``origin``, never forced; a branch already holding it is fine.

    A branch GitHub brought up to date holds it below its head.

    Raises:
        design_pack.PackError: The branch holds other work, or the push was refused.
    """
    there = remote_head(src, branch, run)
    if there == made:
        return
    if there:
        run(src.root, ["fetch", "--quiet", "origin", f"refs/heads/{branch}"])
        if _holds(run, src.root, made, there):
            return
        msg = f"the branch {branch} on {src.repository} holds {there[:12]}, without the update's {made[:12]}"
        raise design_pack.PackError(msg)
    run(src.root, ["push", "--quiet", "origin", f"{made}:refs/heads/{branch}"])


def _holds(run: Git, root: Path, made: str, there: str) -> bool:
    """Whether *there* holds *made*: the same commit or one after it."""
    try:
        run(root, ["merge-base", "--is-ancestor", made, there])
    except design_pack.PackError:
        return False
    return True
