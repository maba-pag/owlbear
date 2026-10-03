"""Release-gated entry for provider effects whose request body must never come from stdin.

The owner freezes the request body to a read-only file, spawns this module in a new session,
records the process group, records the release and only then writes one fixed-size token. The
launcher reads the whole token, re-hashes the frozen file, replaces stdin with ``/dev/null`` and
only on an exact match ``exec``s ``gh api … --input <file>`` in the same process group. EOF, a
short or wrong token, a missing file or a digest mismatch exit without any request.

The launcher half uses only the standard library so it can run as ``python -I -S <this file>``.
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import os
import re
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery.publication_provider import RequestPublicationMerge

LAUNCHER_UNSENT_EXIT = 86
_LAUNCH_ID_PATTERN = re.compile(r"[0-9a-f]{32}")
_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")
TOKEN_SIZE = 32 + 1 + 64 + 1
_REAP_SECONDS = 5.0
_PROC_STAT_START_TIME_INDEX = 19
_LAUNCHER_FIXED_ARGUMENTS = 4


class FrozenBodyMismatchError(ValueError):
    """The frozen body file differs from the approved request; nothing was spawned or sent."""


def freeze_body(request: RequestPublicationMerge) -> bytes:
    """Return the canonical frozen JSON body of one approved merge request."""
    # Imported lazily: the launcher half of this module must run without third-party packages.
    from owlbear_delivery.publication_provider import merge_request_body  # noqa: PLC0415

    return merge_request_body(request)


def body_digest(body: bytes) -> str:
    """Return the content address of one frozen body."""
    return hashlib.sha256(body).hexdigest()


def release_token(launch_id: str, digest: str) -> bytes:
    """Return the fixed-size release token for one launch and frozen body digest."""
    if _LAUNCH_ID_PATTERN.fullmatch(launch_id) is None or _DIGEST_PATTERN.fullmatch(digest) is None:
        message = "release token requires one launch identity and one body digest"
        raise ValueError(message)
    return f"{launch_id}:{digest}\n".encode()


def read_process_start_time(pid: int) -> str | None:
    """Return an OS start-time identity for one live process, or ``None`` when unreadable."""
    stat = Path(f"/proc/{pid}/stat")
    if stat.is_file():
        try:
            fields = stat.read_text(encoding="ascii").rsplit(")", maxsplit=1)[1].split()
        except OSError, IndexError, UnicodeDecodeError:
            return None
        if len(fields) <= _PROC_STAT_START_TIME_INDEX:
            return None
        return f"proc-stat:{fields[_PROC_STAT_START_TIME_INDEX]}"
    try:
        completed = subprocess.run(  # noqa: S603 - fixed ps vector with a numeric pid.
            ("/bin/ps", "-o", "lstart=", "-p", str(pid)),
            check=False,
            capture_output=True,
            env={"LC_ALL": "C", "PATH": "/bin:/usr/bin"},
            timeout=_REAP_SECONDS,
        )
    except OSError, subprocess.TimeoutExpired:
        return None
    started = " ".join(completed.stdout.decode(errors="replace").split())
    return f"ps-lstart:{started}" if completed.returncode == 0 and started else None


@dataclass(frozen=True, slots=True)
class LaunchedEffect:
    """One spawned launcher still blocked on its release token."""

    process: subprocess.Popen[bytes]
    launch_id: str
    digest: str

    @property
    def group_id(self) -> int:
        """Return the launcher's process group, equal to its pid in its new session."""
        return self.process.pid

    def write_token(self) -> None:
        """Write the whole release token and close the only write end of the launcher's stdin."""
        stdin = self.process.stdin
        if stdin is None:
            message = "launcher stdin is not a pipe"
            raise RuntimeError(message)
        try:
            stdin.write(release_token(self.launch_id, self.digest))
            stdin.flush()
        finally:
            stdin.close()

    def abandon(self) -> None:
        """Close the token pipe unsent, then reap the launcher, killing its group if it lingers."""
        if self.process.stdin is not None and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.communicate(timeout=_REAP_SECONDS)
        except subprocess.TimeoutExpired:
            kill_group(self.process)

    def finish(self, timeout_seconds: float) -> subprocess.CompletedProcess[bytes]:
        """Wait for the released effect; on timeout kill its group and re-raise the timeout."""
        try:
            stdout, stderr = self.process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            kill_group(self.process)
            raise
        return subprocess.CompletedProcess(self.process.args, self.process.returncode, stdout, stderr)


def kill_group(process: subprocess.Popen[bytes]) -> None:
    """Kill one launcher's whole process group and reap its leader."""
    with contextlib.suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)
    process.communicate()


def spawn_effect(gh_arguments: tuple[str, ...], body_path: Path) -> LaunchedEffect:
    """Spawn the launcher for one frozen body in its own session; nothing is sent before release."""
    body = body_path.read_bytes()
    digest = body_digest(body)
    launch_id = os.urandom(16).hex()
    _validate_gh_arguments(list(gh_arguments), str(body_path))
    process = subprocess.Popen(  # noqa: S603 - fixed interpreter, this module and validated gh arguments.
        (sys.executable, "-I", "-S", __file__, launch_id, str(body_path), digest, "--", *gh_arguments),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        start_new_session=True,
    )
    return LaunchedEffect(process=process, launch_id=launch_id, digest=digest)


def run_release_gated(
    gh_arguments: tuple[str, ...],
    body_path: Path,
    release: Callable[[int, str], None],
    timeout_seconds: float,
) -> subprocess.CompletedProcess[bytes]:
    """Spawn, report the group to ``release``, then write the token and wait for the effect.

    A raising ``release`` or an unreadable start time closes the pipe unsent. A timeout after the
    token kills the group and re-raises ``subprocess.TimeoutExpired``.
    """
    launched = spawn_effect(gh_arguments, body_path)
    try:
        release(launched.group_id, _require_start_time(launched.group_id))
    except BaseException:
        launched.abandon()
        raise
    # A launcher that ended before the token reports its exit status through finish().
    with contextlib.suppress(BrokenPipeError):
        launched.write_token()
    return launched.finish(timeout_seconds)


def _require_start_time(pid: int) -> str:
    start_time = read_process_start_time(pid)
    if start_time is None:
        message = "effect launcher start time is unreadable"
        raise ProcessLookupError(message)
    return start_time


def _validate_gh_arguments(arguments: list[str], body_path: str) -> None:
    if not arguments or arguments[0] != "gh" or arguments[-2:] != ["--input", body_path]:
        message = "effect launcher runs only gh with the frozen body file as its final input"
        raise ValueError(message)
    if arguments.count("--input") != 1 or "-" in arguments:
        message = "effect launcher never reads a request body from stdin"
        raise ValueError(message)


def _read_token(file_descriptor: int) -> bytes:
    chunks: list[bytes] = []
    remaining = TOKEN_SIZE
    while remaining:
        chunk = os.read(file_descriptor, remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _unsent(reason: str) -> int:
    sys.stderr.write(f"owlbear-effect-launcher: unsent: {reason}\n")
    return LAUNCHER_UNSENT_EXIT


def _released_command(argv: list[str]) -> tuple[list[str], str | None]:
    if len(argv) <= _LAUNCHER_FIXED_ARGUMENTS or argv[3] != "--":
        return [], "invalid launcher arguments"
    launch_id, body_path, digest, gh_arguments = argv[0], argv[1], argv[2], argv[4:]
    try:
        expected = release_token(launch_id, digest)
        _validate_gh_arguments(gh_arguments, body_path)
    except ValueError:
        return [], "invalid launcher arguments"
    if not hmac.compare_digest(_read_token(0), expected):
        return [], "release token missing or incomplete"
    try:
        body = Path(body_path).read_bytes()
    except OSError:
        return [], "frozen body unreadable"
    if not hmac.compare_digest(body_digest(body), digest):
        return [], "frozen body digest mismatch"
    return gh_arguments, None


def main(argv: list[str]) -> int:
    """Wait for the release token, verify the frozen body and ``exec`` the provider command."""
    gh_arguments, refusal = _released_command(argv)
    if refusal is not None:
        return _unsent(refusal)
    null = os.open(os.devnull, os.O_RDONLY)
    os.dup2(null, 0)
    os.close(null)
    try:
        os.execvp(gh_arguments[0], gh_arguments)  # noqa: S606 - validated fixed gh vector.
    except OSError:
        return _unsent("provider command unavailable")
    return LAUNCHER_UNSENT_EXIT


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
