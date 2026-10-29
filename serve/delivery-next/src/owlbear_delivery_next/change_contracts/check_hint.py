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

# One literal shell word as shlex.quote writes it: unquoted, only what it leaves bare; quoted, nothing the shell would
# expand or unescape. So no comment, redirect, expansion or backslash, and shlex.split reads it as the shell does.
WORD = r"""(?:[\w@%+=:,./-]|'[^']*'|"[^"\\$`]*")+"""
CD_CHECK = re.compile(rf"cd[ \t]+({WORD})[ \t]*&&[ \t]*(\S.*)", re.DOTALL)


def _form(command: str) -> tuple[str | None, str]:
    """*command* as (directory, command): `cd <dir> && <cmd>` split with its quoting undone; text kept as written.

    Only the ends are trimmed: other whitespace can separate commands or sit inside a substitution.
    """
    said = command.strip()
    found = CD_CHECK.fullmatch(said)
    if not found:
        return None, said
    return PurePosixPath(shlex.split(found[1])[0] or ".").as_posix(), found[2]


def ran(check: str, command: str, checks: Sequence[str]) -> bool:
    """Whether the reported *command* ran *check*: that command, or a bare check run as `cd <dir> && <check>`.

    A report that is itself another of the required *checks*, such as another package's run of the same command
    (TD-246), never stands in for the bare one; a check already in a directory gets no other.
    """
    want, got = _form(check), _form(command)
    return got == want or (want[0] is None and got[1] == want[1] and got not in {_form(c) for c in checks})


def alone(check: str, packages: Sequence[tuple[str, str]]) -> str:
    """For `cd <dir> && <cmd>` where <cmd> is the profile check of the package in <dir>: write <cmd> alone; else "".

    Only a hint, so it forgives whitespace; check_plan then admits the profile's command as written and no other.
    """
    where, command = _form(check)
    said = [c for p, c in packages if where is not None and (_package(p), c.split()) == (where, command.split())]
    return f'write the command alone: "{said[0]}"; the Builder runs it from that package\'s directory' if said else ""


def _package(path: str) -> str:
    return PurePosixPath(path.strip("/") or ".").as_posix()
