"""The whole text of a failed command or any other failure, for pages and logs (D-01M64TXG1P1HMPQH7Q9CWAYSSW)."""

from __future__ import annotations

import subprocess


def _said(stream: object) -> str:
    """A captured stream as text; a ``TimeoutExpired`` keeps bytes even when the command ran with ``text=True``."""
    if stream is None:
        return ""
    return (stream.decode(errors="replace") if isinstance(stream, bytes) else str(stream)).strip()


def streams(exc: BaseException) -> str:
    """What a command *exc* carries printed, or nothing when it carries none.

    The one stream that said something as it is, or both, labelled, stderr first. ``str()`` of a
    ``CalledProcessError`` or ``TimeoutExpired`` leaves it out.
    """
    stderr, stdout = _said(getattr(exc, "stderr", None)), _said(getattr(exc, "output", None))
    if stderr and stdout:
        return f"stderr:\n{stderr}\nstdout:\n{stdout}"
    return stderr or stdout


def failure(exc: BaseException) -> str:
    """Its type and message, then what a command it carries printed (`streams`) on its own lines, then its notes.

    Notes added on the way up (``add_note``, a cleanup that also failed) follow, each on its own line.
    """
    out = streams(exc)
    notes = "".join(f"\n{note}" for note in getattr(exc, "__notes__", ()))
    return f"{type(exc).__name__}: {exc}" + (f"\n{out}" if out else "") + notes


def failed(done: subprocess.CompletedProcess) -> str:
    """A command that exited non-zero without raising, said as the ``CalledProcessError`` it stands for."""
    return failure(subprocess.CalledProcessError(done.returncode, done.args, done.stdout, done.stderr))
