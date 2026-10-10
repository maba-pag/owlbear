# Copied from serve/delivery/src/owlbear_delivery/remote_git.py at ab9cfc6cb.
"""Bounded, noninteractive remote Git transport for Delivery."""

from __future__ import annotations

import contextlib
import os
import re
import shlex
import signal
import subprocess
from pathlib import PurePath
from typing import TYPE_CHECKING, Literal

from owlbear_delivery_next.git.git_executable import resolve_git_executable

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

RemoteGitKind = Literal["read", "write"]
WriteReadback = Literal["applied", "not-applied", "conflict"]

READ_TIMEOUT_SECONDS = 120.0
WRITE_TIMEOUT_SECONDS = 120.0
REAP_TIMEOUT_SECONDS = 5.0
CONFIG_TIMEOUT_SECONDS = 10.0
_LS_REMOTE_MISSING = 2
_LS_REMOTE_FIELDS = 2
_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
_REPOSITORY_VARIABLES = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")
_BATCH_SSH_OPTION = "-o BatchMode=yes"
_BATCH_SSH_COMMAND = f"ssh {_BATCH_SSH_OPTION}"
_CONFIG_UNSET = 1
# Git global options that take their value as the next argument.
_GLOBAL_OPTIONS_WITH_VALUE = frozenset({"-c", "-C", "--config-env", "--git-dir", "--work-tree", "--namespace"})


class RemoteGitError(RuntimeError):
    """One remote Git operation did not produce a usable result."""

    def __init__(
        self,
        detail: str,
        *,
        retry_safe: bool,
        result: subprocess.CompletedProcess[bytes] | None = None,
    ) -> None:
        super().__init__(detail)
        self.retry_safe = retry_safe
        self.result = result


class RemoteGitTimeout(RemoteGitError):  # noqa: N818 - interface name fixed by the N02 plan.
    """A remote read exceeded its bound; nothing remote changed, so it is retry-safe."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail, retry_safe=True)


class RemoteGitFailed(RemoteGitError):  # noqa: N818 - interface name fixed by the N02 plan.
    """Git could not run, or a remote observation returned no valid answer."""


class RemoteGitWriteUnknown(RemoteGitError):  # noqa: N818 - interface name fixed by the N02 plan.
    """A remote write timed out or failed; its outcome needs a readback before any retry."""

    def __init__(
        self,
        detail: str,
        *,
        timed_out: bool,
        result: subprocess.CompletedProcess[bytes] | None = None,
    ) -> None:
        super().__init__(detail, retry_safe=False, result=result)
        self.timed_out = timed_out


def remote_git_environment(
    base: Mapping[str, str] | None = None,
    *,
    configured_ssh_command: str | None = None,
) -> dict[str, str]:
    """Return an environment in which Git and its transports can never prompt.

    Git prefers ``GIT_SSH_COMMAND`` to ``core.sshCommand`` (``configured_ssh_command``, from every scope
    including the operation's own ``-c``) to ``GIT_SSH``, and the user's choice keeps its identity, port and
    proxy options. Only a configured command whose program is ``ssh`` also gets ``BatchMode=yes``, inserted
    straight after the program because OpenSSH keeps the first value it obtains; an unknown wrapper's
    arguments are left alone. Every transport still runs without a controlling terminal
    (``run_remote_git``) and without askpass, so none can prompt.
    """
    environment = dict(os.environ if base is None else base)
    for name in _REPOSITORY_VARIABLES:
        environment.pop(name, None)
    environment.update(
        {
            "GIT_TERMINAL_PROMPT": "0",
            "GCM_INTERACTIVE": "never",
            # Set but empty: Git then skips core.askPass and SSH_ASKPASS instead of falling back to them.
            "GIT_ASKPASS": "",
            "SSH_ASKPASS": "",
            "SSH_ASKPASS_REQUIRE": "never",
        }
    )
    if "GIT_SSH_COMMAND" in environment:
        return environment
    if configured_ssh_command is not None:
        batch_command = _with_batch_mode(configured_ssh_command)
        if batch_command is not None:
            environment["GIT_SSH_COMMAND"] = batch_command
        return environment
    if "GIT_SSH" not in environment:
        environment["GIT_SSH_COMMAND"] = _BATCH_SSH_COMMAND
    return environment


def _with_batch_mode(command: str) -> str | None:
    """Insert ``BatchMode=yes`` after a direct ``ssh`` program, keeping the rest of the shell text verbatim."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=False)
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        program = lexer.get_token()
    except ValueError:
        return None
    if program is None or PurePath(program).name != "ssh":
        return None
    end = lexer.instream.tell()
    rest = command[end:]
    return f"{command[:end].rstrip()} {_BATCH_SSH_OPTION}" + (f" {rest}" if rest else "")


def _global_options(arguments: Sequence[str]) -> tuple[str, ...]:
    """Return the Git global options before the subcommand, which scope configuration like the operation."""
    index = 0
    while index < len(arguments) and arguments[index].startswith("-"):
        index += 2 if arguments[index] in _GLOBAL_OPTIONS_WITH_VALUE else 1
    return tuple(arguments[:index])


def _configured_ssh_command(repository: Path, base: Mapping[str, str], global_options: Sequence[str]) -> str | None:
    """Read ``core.sshCommand`` as the operation's own Git would, including its ``-c`` options."""
    environment = {name: value for name, value in base.items() if name not in _REPOSITORY_VARIABLES}
    try:
        result = subprocess.run(  # noqa: S603 - fixed Git executable and code-owned argument vector.
            (
                resolve_git_executable(),
                "-C",
                str(repository),
                *global_options,
                "config",
                "--get",
                "core.sshCommand",
            ),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            env=environment,
            timeout=CONFIG_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        error = RemoteGitFailed("Git SSH configuration could not be read", retry_safe=True)
        raise error from exc
    except OSError as exc:
        error = RemoteGitFailed("Git is unavailable for remote access", retry_safe=False)
        raise error from exc
    if result.returncode == _CONFIG_UNSET:
        return None
    if result.returncode != 0:
        error = RemoteGitFailed("Git SSH configuration could not be read", retry_safe=False, result=result)
        raise error
    # A set but empty or valueless command is still Git's own choice; Git reports it when it connects.
    return result.stdout.decode(errors="replace").rstrip("\n")


def run_remote_git(
    repository: Path,
    arguments: Sequence[str],
    *,
    kind: RemoteGitKind,
    timeout: float | None = None,
    environment: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """Run one remote Git command in its own session and kill the whole group at the bound.

    A read returns its completed process whatever its exit status. A write returns only on exit 0;
    a timeout or failure raises ``RemoteGitWriteUnknown`` so the caller reads the remote back first.
    """
    bound = timeout if timeout is not None else (READ_TIMEOUT_SECONDS if kind == "read" else WRITE_TIMEOUT_SECONDS)
    base = os.environ if environment is None else environment
    configured = (
        None if "GIT_SSH_COMMAND" in base else _configured_ssh_command(repository, base, _global_options(arguments))
    )
    command = (resolve_git_executable(), "-C", str(repository), *arguments)
    try:
        process = subprocess.Popen(  # noqa: S603 - fixed Git executable and code-owned argument vectors.
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=remote_git_environment(base, configured_ssh_command=configured),
            start_new_session=True,
        )
    except OSError as exc:
        error = RemoteGitFailed("Git is unavailable for remote access", retry_safe=False)
        raise error from exc
    finished = False
    try:
        stdout, stderr = process.communicate(timeout=bound)
        finished = True
    except subprocess.TimeoutExpired as exc:
        _terminate_group(process)
        finished = True
        if kind == "write":
            write_error = RemoteGitWriteUnknown(f"remote Git write exceeded {bound:g} s", timed_out=True)
            raise write_error from exc
        read_error = RemoteGitTimeout(f"remote Git read exceeded {bound:g} s")
        raise read_error from exc
    finally:
        if not finished:
            _terminate_group(process)
    result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    if kind == "write" and result.returncode != 0:
        detail = "remote Git write did not confirm its outcome"
        raise RemoteGitWriteUnknown(detail, timed_out=False, result=result)
    return result


def _terminate_group(process: subprocess.Popen[bytes]) -> None:
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(process.pid, signal.SIGKILL)
    try:
        process.communicate(timeout=REAP_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        # A descendant that left the group still holds the output pipes; Git itself is already dead.
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                stream.close()
        process.wait()


def read_remote_ref(
    repository: Path,
    remote: str,
    reference: str,
    *,
    timeout: float | None = None,
) -> str | None:
    """Read one exact remote ref through a bounded ``ls-remote``; ``None`` means absent."""
    result = run_remote_git(
        repository,
        ("ls-remote", "--exit-code", "--refs", remote, reference),
        kind="read",
        timeout=timeout,
    )
    if result.returncode == _LS_REMOTE_MISSING:
        return None
    if result.returncode != 0:
        detail = "remote ref could not be observed"
        raise RemoteGitFailed(detail, retry_safe=True, result=result)
    lines = result.stdout.decode(errors="replace").strip().splitlines()
    fields = lines[0].split("\t") if len(lines) == 1 else []
    if len(fields) != _LS_REMOTE_FIELDS or fields[1] != reference or _COMMIT_PATTERN.fullmatch(fields[0]) is None:
        detail = "remote ref response is invalid"
        raise RemoteGitFailed(detail, retry_safe=False, result=result)
    return fields[0]


def classify_write_readback(observed: str | None, *, intended: str, expected_old: str | None) -> WriteReadback:
    """Classify one remote readback taken after an uncertain write."""
    if observed == intended:
        return "applied"
    if observed == expected_old:
        return "not-applied"
    return "conflict"


__all__ = [
    "READ_TIMEOUT_SECONDS",
    "WRITE_TIMEOUT_SECONDS",
    "RemoteGitError",
    "RemoteGitFailed",
    "RemoteGitKind",
    "RemoteGitTimeout",
    "RemoteGitWriteUnknown",
    "classify_write_readback",
    "read_remote_ref",
    "remote_git_environment",
    "run_remote_git",
]
