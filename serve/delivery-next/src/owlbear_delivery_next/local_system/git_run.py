"""One Git command run for the shared data repository, never prompting and never past its caller's deadline.

`data_repo` runs every Git command of its checkout through this, so a deadline a save is given bounds each of them.
A command that reaches a remote runs as TD-402's account on the repository it reaches (D-01M6G9YHN2XHJANSWDADZTT6EG).
"""

from __future__ import annotations

import errno
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import TypedDict, Unpack

from owlbear_delivery_next.git.access import Access
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.git.remote_git import RemoteGitError
from owlbear_delivery_next.github.account import AccountMissing, Origin, Writer

EXPIRED = "the deadline passed before git could run"
REMOTE = frozenset({"push", "fetch", "pull", "ls-remote", "clone"})
_STDERR_FD = 2


class _RunOptions(TypedDict):
    env: dict[str, str]
    capture_output: bool
    text: bool
    timeout: float


def _decoded(output: bytes | None) -> str | None:
    """Decode captured bytes without translating their line endings."""
    return None if output is None else output.decode("utf-8", "surrogateescape")


def run(
    cwd: Path,
    *args: str,
    until: float | None,
    cap: float,
    show: bool = False,
    lossless: bool = False,
) -> subprocess.CompletedProcess[str]:
    """One git command, ended by ``until`` (monotonic) at the latest and after *cap* seconds; never prompts.

    A command that times out or cannot start is a failed one (exit 128), and so is one whose deadline has already
    passed: Git is then never started. Without ``until`` it runs for *cap* seconds at most; that one deadline also
    bounds choosing the account a remote command runs as, and an account that can't be had or a push over SSH is a
    failed command with its reason. When *show*, Git writes to the terminal and only the exit code is returned.
    *lossless* preserves UTF-8 bytes and line endings for callers that classify separate records in one output.
    """
    remote = _remote(args)
    local_env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"} if not remote else None
    executable = _spawn_executable(cwd, local_env) if local_env is not None else None
    seconds = cap if until is None else min(cap, until - time.monotonic())
    deadline = time.monotonic() + seconds
    if not remote and until is not None:
        deadline = min(deadline, until)
    if seconds <= 0:
        return subprocess.CompletedProcess(["git", *args], 128, "", EXPIRED)
    try:
        access = _access(cwd, args, deadline)
        seconds = _left(deadline) if remote else seconds
    except (AccountMissing, RemoteGitError, TimeoutError, subprocess.TimeoutExpired) as exc:
        said = failure(exc)
        if isinstance(exc, subprocess.TimeoutExpired):  # `_left`'s own TimeoutError already says EXPIRED
            said = f"{EXPIRED}: {said}"
        return subprocess.CompletedProcess(["git", *args], 128, "", said)
    command = ["git", *access.options(), *args]
    environment = local_env if local_env is not None else access.environment({**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    try:
        done = _launch(
            cwd,
            command,
            executable,
            deadline,
            env=environment,
            capture_output=not show,
            text=not lossless,
            timeout=seconds,
        )
    except subprocess.TimeoutExpired as exc:
        exc.cmd = command
        return subprocess.CompletedProcess(command, 128, "", failure(exc))
    except OSError as exc:
        # Exit 1 can mean no match or a difference; failure to run Git cannot answer either probe.
        return subprocess.CompletedProcess(command, 128, "", failure(exc))
    if lossless:
        return subprocess.CompletedProcess(done.args, done.returncode, _decoded(done.stdout), _decoded(done.stderr))
    return done


def _launch(
    cwd: Path,
    command: list[str],
    executable: str | None,
    deadline: float,
    **options: Unpack[_RunOptions],
) -> subprocess.CompletedProcess:
    """Launch with the chosen executable, or let native lookup give its own result and error."""
    while True:
        argv = ["git", "-C", str(cwd), *command[1:]] if executable else command
        try:
            # Shared-data and pack callers own Git verbs/argv; access adds account options, operands stay separate.
            done = subprocess.run(  # noqa: S603 - code-owned Git vectors with per-launch account environment, no shell
                argv,
                **({"executable": executable, "close_fds": False} if executable else {"cwd": cwd}),
                stdin=subprocess.DEVNULL,
                check=False,
                **options,
            )
        except OSError as exc:
            # Only an exec failure allows a retry: the first command must not have started.
            if not executable or exc.filename != executable:
                raise
            executable = None
            seconds = deadline - time.monotonic()
            if seconds <= 0:
                return (
                    subprocess.CompletedProcess(command, 128, "", EXPIRED)
                    if options["text"]
                    else subprocess.CompletedProcess(command, 128, b"", EXPIRED.encode())
                )
            options["timeout"] = seconds
        else:
            if executable:
                done.args = command
            return done


def _spawn_executable(cwd: Path, environment: dict[str, str]) -> str | None:
    """Resolve git only when the child has the same search path and no extra inheritable descriptors."""
    path = environment.get("PATH", "")
    if not all(Path(entry).is_absolute() for entry in path.split(os.pathsep)):
        return None
    # Keep the native launch error when Python would be unable to enter the directory.
    if not cwd.is_dir() or not os.access(cwd, os.X_OK):
        return None
    try:
        for entry in Path("/dev/fd").iterdir():
            if not entry.name.isdecimal() or (fd := int(entry.name)) <= _STDERR_FD:
                continue
            try:
                if os.get_inheritable(fd):
                    return None
            except OSError as exc:
                # The descriptor used for the listing can already be closed.
                if exc.errno != errno.EBADF:
                    raise
    except OSError:
        return None
    return shutil.which("git", path=path)


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
    # Native lookup preserves child PATH and execution-time continuation; _default owns metadata-query argv.
    done = subprocess.run(  # noqa: S603 - internal symbolic-ref/for-each-ref metadata arguments; no shell
        ["git", *args],  # noqa: S607 - preserve native child PATH and execution-time search
        cwd=cwd, capture_output=True, text=True, timeout=_left(deadline), check=False, stdin=subprocess.DEVNULL,
    )  # fmt: skip
    return done.stdout.strip() if done.returncode == 0 else ""


def _left(deadline: float) -> float:
    if (left := deadline - time.monotonic()) <= 0:
        raise TimeoutError(EXPIRED)
    return left
