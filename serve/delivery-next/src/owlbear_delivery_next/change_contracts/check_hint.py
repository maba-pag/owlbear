"""The planner's hint for a check written with its package directory in front: name the command alone.

The Builder runs each task check from its package's directory, so a plan check is the profile's command as listed.
The `cd <package> && <check>` form is never accepted; its error only says what to write instead.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

CD_CHECK = re.compile(r"cd\s+(\S+)\s*&&\s*(\S.*?)")


def _place(directory: str) -> str:
    return PurePosixPath(directory.strip("'\"").strip("/") or ".").as_posix()


def alone(check: str, packages: Sequence[tuple[str, str]]) -> str:
    """For `cd <dir> && <cmd>` where <cmd> is the profile check of the package in <dir>: write <cmd> alone; else ""."""
    found = CD_CHECK.fullmatch(check.strip())
    if found and (_place(found[1]), found[2]) in {(_place(p), c) for p, c in packages}:
        return f'write the command alone: "{found[2]}"; the Builder runs it from that package\'s directory'
    return ""
