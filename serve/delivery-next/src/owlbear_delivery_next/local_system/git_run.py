"""One Git command run for the shared data repository, never prompting and never past its caller's deadline.

`data_repo` runs every Git command of its checkout through this, so a deadline a save is given bounds each of them.
A command that reaches a remote runs as TD-402's account on the repository it reaches (D-01M6G9YHN2XHJANSWDADZTT6EG).
"""

from __future__ import annotations

import os
import subprocess
import time
from typing import TYPE_CHECKING

from owlbear_delivery_next.git.access import Access
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.git.remote_git import RemoteGitError
from owlbear_delivery_next.github.account import AccountMissing, Origin, Writer

if TYPE_CHECKING:
    from pathlib import Path

EXPIRED = "the deadline passed before git could run"
REMOTE = frozenset({"push", "fetch", "pull", "ls-remote", "clone"})


def run(cwd: Path, *args: str, until: float | None, cap: float, show: bool = False) -> subprocess.CompletedProcess[str]:
    """One git command, ended by ``until`` (monotonic) at the latest and after *cap* seconds; never prompts.

    A command that times out or cannot start is a failed one (exit 128), and so is one whose deadline has already
    passed: Git is then never started. Without ``until`` it runs for *cap* seconds at most; that one deadline also
    bounds choosing the account a remote command runs as, and an account that can't be had or a push over SSH is a
    failed command with its reason. When *show*, Git writes to the terminal and only the exit code is returned.
    """
    seconds = cap if until is None else min(cap, until - time.monotonic())
    deadline = time.monotonic() + seconds
    if seconds <= 0:
        return subprocess.CompletedProcess(["git", *args], 128, "", EXPIRED)
    try:
        access = _access(cwd, args, deadline)
        seconds = _left(deadline) if _remote(args) else seconds
    except (AccountMissing, RemoteGitError, TimeoutError, subprocess.TimeoutExpired) as exc:
        said = EXPIRED if isinstance(exc, TimeoutError | subprocess.TimeoutExpired) else str(exc)
        return subprocess.CompletedProcess(["git", *args], 128, "", said)
    command = ["git", *access.options(), *args]
    try:
        return subprocess.run(  # noqa: S603
            command,
            cwd=cwd,
            env=access.environment({**os.environ, "GIT_TERMINAL_PROMPT": "0"}),
            stdin=subprocess.DEVNULL,
            capture_output=not show,
            text=True,
            timeout=seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        # Exit 1 can mean no match or a difference; failure to run Git cannot answer either probe.
        return subprocess.CompletedProcess(command, 128, "", failure(exc))


def _access(cwd: Path, args: tuple[str, ...], deadline: float) -> Access:
    """The account a remote command runs as; a push is first checked for an SSH destination."""
    if not (verb := _remote(args)):
        return Access.LOCAL
    rest = [a for a in args[args.index(verb) + 1 :] if not a.startswith("-")]
    if verb == "clone":
        return Writer.rule(Origin.url(rest[0])).access(until=deadline)
    remote = rest[0] if rest else _default(cwd, "push" if verb == "push" else "upstream", deadline)
    access = Writer.rule(Origin.of(cwd, remote, timeout=_left(deadline))).access(until=deadline)
    if verb == "push":
        access.destinations(cwd, remote, _left(deadline))
    return access


def _remote(args: tuple[str, ...]) -> str:
    """The verb of a command that reaches a remote, found after any leading ``-c key=value`` pairs; else ``""``."""
    at = 0
    while args[at : at + 1] == ("-c",):
        at += 2
    return args[at] if at < len(args) and args[at] in REMOTE else ""


def _default(cwd: Path, kind: str, deadline: float) -> str:
    """The remote a command naming none uses: the current branch's push or upstream remote, else ``origin``."""
    head = _read(cwd, ("symbolic-ref", "-q", "HEAD"), deadline)
    found = _read(cwd, ("for-each-ref", f"--format=%({kind}:remotename)", head), deadline) if head else ""
    return found or "origin"


def _read(cwd: Path, args: tuple[str, ...], deadline: float) -> str:
    done = subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=cwd, capture_output=True, text=True, timeout=_left(deadline), check=False, stdin=subprocess.DEVNULL,
    )  # fmt: skip
    return done.stdout.strip() if done.returncode == 0 else ""


def _left(deadline: float) -> float:
    if (left := deadline - time.monotonic()) <= 0:
        raise TimeoutError(EXPIRED)
    return left
