"""The `cd <dir> && <check>` form: the planner's hint to name a check alone, and which reported command ran a check.

The Builder runs each task check from its package's directory, so a plan check is the profile's command as listed;
there the form is never accepted and its error only says what to write instead. A retried task's checks carry it
(TD-246), and a Builder may report a bare check it ran from a package directory in it.
"""

from __future__ import annotations

import re
import shlex
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

WORD = r"""(?:\\.|[^\s'"\\&;|]|'[^']*'|"(?:[^"\\]|\\.)*")+"""  # one shell word, quoted as shlex.quote writes it
CD_CHECK = re.compile(rf"cd\s+({WORD})\s*&&\s*(\S.*)", re.DOTALL)


def _form(command: str) -> tuple[str | None, str]:
    """*command* as (directory, command): `cd <dir> && <cmd>` split with its quoting undone; whitespace collapsed."""
    found = CD_CHECK.fullmatch(command.strip())
    if not found:
        return None, " ".join(command.split())
    return PurePosixPath(shlex.split(found[1])[0] or ".").as_posix(), " ".join(found[2].split())


def ran(check: str, command: str, checks: Sequence[str]) -> bool:
    """Whether the reported *command* ran *check*: that command, or a bare check run as `cd <dir> && <check>`.

    A report that is itself another of the required *checks*, such as another package's run of the same command
    (TD-246), never stands in for the bare one; a check already in a directory gets no other.
    """
    want, got = _form(check), _form(command)
    return got == want or (want[0] is None and got[1] == want[1] and got not in {_form(c) for c in checks})


def alone(check: str, packages: Sequence[tuple[str, str]]) -> str:
    """For `cd <dir> && <cmd>` where <cmd> is the profile check of the package in <dir>: write <cmd> alone; else ""."""
    where, command = _form(check)
    said = [c for p, c in packages if where is not None and (_package(p), " ".join(c.split())) == (where, command)]
    return f'write the command alone: "{said[0]}"; the Builder runs it from that package\'s directory' if said else ""


def _package(path: str) -> str:
    return PurePosixPath(path.strip("/") or ".").as_posix()
