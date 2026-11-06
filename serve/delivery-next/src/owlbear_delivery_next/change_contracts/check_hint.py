"""Directory-qualified check choices, legacy placement and reported execution identities."""

from __future__ import annotations

import json
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
    where = found and PurePosixPath(shlex.split(found[1])[0] or ".")
    if not found or ".." in where.parts:  # a parent step can name a directory another way
        return None, said
    return where.as_posix(), found[2]


def ran(check: str, command: str, checks: Sequence[str]) -> bool:
    """Whether the reported *command* ran *check*: that command, or a bare check run as `cd <dir> && <check>`.

    A report that is itself another of the required *checks*, such as another package's run of the same command
    (TD-246), never stands in for the bare one; a check already in a directory gets no other.
    """
    want, got = _form(check), _form(command)
    return got == want or (want[0] is None and got[1] == want[1] and got not in {_form(c) for c in checks})


def missing(command: str) -> str:
    """Name a missing execution with a copyable result example, including multiline command bodies."""
    example = json.dumps({"command": command, "exit_code": 0})
    return f'checks: "{command}" missing - run it on your commit and report it, e.g. {example}'


def qualified(package: str, command: str) -> str:
    """A confirmed check as a complete command run from the repository root."""
    directory = PurePosixPath(package.strip("/") or ".").as_posix()
    if directory != ".":
        directory = f"./{directory}"
    return f"cd {shlex.quote(directory)} && {{\n{command}\n}}"


def resolve(checks: Sequence[str], packages: Sequence[tuple[str, str]]) -> list[str]:
    """Keep selected identities; qualify an old bare check only when its confirmed owner is unique."""
    resolved = []
    for check in checks:
        if _form(check)[0] is not None:
            resolved.append(check)
            continue
        matches = {qualified(p, c) for p, c in packages if c == check}
        if len(matches) != 1:
            available = ", ".join(qualified(p, c) for p, c in packages) or "none"
            msg = (
                f"Cannot place legacy check {check!r}: expected one confirmed package, found {len(matches)}; "
                f"available qualified checks: {available}"
            )
            raise ValueError(msg)
        resolved.extend(matches)
    return list(dict.fromkeys(resolved))
