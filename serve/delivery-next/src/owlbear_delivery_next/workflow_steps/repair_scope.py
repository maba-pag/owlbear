"""Repair scope and ownership of the checks used to prove a patch."""

from __future__ import annotations

import os
import shlex
import tomllib
from pathlib import PurePosixPath
from traceback import format_exception_only
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import check_hint, evidence
from owlbear_delivery_next.workflow_steps.check_sources import console_script

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change


def hold(path: str, witness: tuple[str, ...], source: Path) -> str:
    """Incomplete original-source discovery holds the fix with the whole error, never applies it."""
    try:
        found = named(path, witness, source)
    except (OSError, SyntaxError, tomllib.TOMLDecodeError) as error:
        detail = "".join(format_exception_only(error)).strip()
        return f"cannot inspect the unchanged check for {path}: {detail}; its altered witness proves nothing alone"
    return f"changes {path}, which the step's check runs, so it proves nothing alone" if found else ""


def named(path: str, witness: tuple[str, ...], source: Path | None = None) -> bool:
    """Whether a check command names *path*: a fix to the check it is proven by needs the owner (never weakened).

    A script by its path, a Python module run with ``-m`` by its file, or the root selector's imported machinery;
    a command that can't be parsed names every path.
    """
    for one in witness:
        where, command = _split(one)
        try:
            words = list(shlex.shlex(command, posix=True, punctuation_chars=True))
        except ValueError:
            return True
        if source is not None and console_script(path, words, source):
            return True
        for before, word in zip(["", *words], words, strict=False):
            found = [word.strip("{}")]
            if before == "-m":
                module = word.replace(".", "/")
                found = [f"{module}.py", f"{module}/__main__.py", f"{module}/__init__.py"]
            for name in found:
                named = os.path.normpath(PurePosixPath(where or ".", name))
                if named == os.path.normpath(path):
                    return True
                if before == "-m" and path.endswith(f"/{name}") and (not where or evidence.within(where, path)):
                    return True  # a module found on the path, as a src/ layout puts it
                if not where and PurePosixPath(name).name == path:
                    return True
    return False


def _split(check: str) -> tuple[str | None, str]:
    """A resolved check as (its directory, the command run there), as ``check_hint`` writes it: `cd <dir> && {…}`."""
    found = check_hint.CD_CHECK.fullmatch(check.strip())
    if not found:
        return None, check
    body = found[2].strip()
    return shlex.split(found[1])[0], body[1:-1] if body.startswith("{") and body.endswith("}") else body


def in_scope(change: Change, path: str) -> bool:
    return not change.brief.scope or any(evidence.within(s, path) for s in change.brief.scope)

