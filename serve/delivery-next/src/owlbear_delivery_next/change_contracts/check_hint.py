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
WORDS = re.compile(rf"{WORD}(?:[ \t]+{WORD})*")


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


def body(command: str) -> tuple[str | None, str]:
    """The named directory and command inside Delivery's shell group."""
    directory, said = _form(command)
    if said.startswith("{\n") and said.endswith("\n}"):
        said = said[2:-2]
    return directory, said


def _literal_targets(targets: Sequence[str]) -> bool:
    return any(target != "--" for target in targets) and all(
        target == "--"
        or (
            target not in {"", ".", "./"}
            and not target.startswith(("-", "~"))
            and not PurePosixPath(target).is_absolute()
            and ".." not in PurePosixPath(target).parts
        )
        for target in targets
    )


def offered(command: str, choices: Sequence[str]) -> bool:
    """An offered check, or literal test targets appended to its same runner and package."""
    if command in choices:
        return True
    directory, said = body(command)
    if directory is None:
        return False
    for choice in choices:
        package, original = body(choice)
        if package != directory or not WORDS.fullmatch(original) or not said.startswith(original + " "):
            continue
        suffix = said[len(original) + 1 :]
        if not WORDS.fullmatch(suffix):
            continue
        if _literal_targets(shlex.split(suffix)):
            return True
    return False


def qualified(package: str, command: str) -> str:
    """A confirmed check as a complete command run from the repository root."""
    directory = PurePosixPath(package.strip("/") or ".").as_posix()
    if directory != ".":
        directory = f"./{directory}"
    return f"cd {shlex.quote(directory)} && {{\n{command}\n}}"


def changed_runner(command: str) -> tuple[str, list[str]] | None:
    """OwlBear's root runner with literal targets and frozen spans; other commands have no adapter."""
    directory, said = body(command)
    if directory != ".":
        return None
    for runner in ("uv run test --changed", "uv run tests --changed"):
        if said in {runner, f"{runner} && uv run lint --no-fix"}:
            return runner, []
        rest = said[len(runner) + 1 :]
        if not said.startswith(runner + " ") or not WORDS.fullmatch(rest):
            continue
        words = iter(shlex.split(rest))
        targets, spans = [], []
        measurement = False
        for word in words:
            if word in {"-m", "--measurement"}:
                measurement = True
            elif word == "--keep-span":
                if (span := next(words, None)) is None:
                    return None
                spans.append(span)
            else:
                targets.append(word)
        if targets and not _literal_targets(targets):
            return None
        suffix = "".join(f" {shlex.quote(target)}" for target in targets if target != "--")
        return runner + (" -m" if measurement else "") + suffix, spans
    return None


def freeze(command: str, spans: Sequence[str]) -> str:
    """Keep original checked deltas in a compact root invocation, without changing another package."""
    if (found := changed_runner(command)) is None:
        return command
    runner, kept = found
    arguments = "".join(f" --keep-span {shlex.quote(span)}" for span in dict.fromkeys([*kept, *spans]))
    return qualified(".", runner + arguments)


def task_command(command: str, base: str | None, target: str) -> str:
    """Bind a root changed check to the host's task and target; its frozen scopes survive this binding."""
    if (found := changed_runner(command)) is None:
        return command
    if base is None:
        msg = "Cannot scope the task check: its build has no recorded starting commit"
        raise ValueError(msg)
    runner, spans = found
    arguments = f" --task-base {shlex.quote(base)} --target {shlex.quote(target)}"
    arguments += "".join(f" --keep-span {shlex.quote(span)}" for span in spans)
    return qualified(".", runner + arguments)


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
