"""Validated Git executable discovery for Delivery subprocesses."""

from __future__ import annotations

import shutil
from functools import cache

_GIT_COMMAND = "git"


@cache
def resolve_git_executable() -> str:
    """Return the Git executable resolved from PATH or fail before invocation."""
    executable = shutil.which(_GIT_COMMAND)
    if executable is None:
        message = "Git executable is unavailable"
        raise RuntimeError(message)
    return executable
