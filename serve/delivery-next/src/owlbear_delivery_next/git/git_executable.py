# Copied from serve/delivery/src/owlbear_delivery/git_executable.py at ab9cfc6cb.
"""Validated Git executable discovery for Delivery subprocesses."""

from __future__ import annotations

import os
import shutil
from functools import cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_GIT_COMMAND = "git"


def git_executable_in(cwd: Path) -> str:
    """Resolve Git against the child's directory, including relative and empty PATH entries."""
    search = os.pathsep.join(str(cwd.absolute() / entry) for entry in os.get_exec_path())
    executable = shutil.which(_GIT_COMMAND, path=search)
    if executable is None:
        raise FileNotFoundError(2, "No such file or directory", _GIT_COMMAND)
    return executable


@cache
def resolve_git_executable() -> str:
    """Return the Git executable resolved from PATH or fail before invocation."""
    executable = shutil.which(_GIT_COMMAND)
    if executable is None:
        message = "Git executable is unavailable"
        raise RuntimeError(message)
    return executable
