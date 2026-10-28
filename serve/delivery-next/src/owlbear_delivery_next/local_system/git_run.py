"""One Git command run for the shared data repository, never prompting and never past its caller's deadline.

`data_repo` runs every Git command of its checkout through this, so a deadline a save is given bounds each of them.
"""

from __future__ import annotations

import os
import subprocess
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

EXPIRED = "the deadline passed before git could run"


def run(cwd: Path, *args: str, until: float | None, cap: float, show: bool = False) -> subprocess.CompletedProcess[str]:
    """One git command, ended by ``until`` (monotonic) at the latest and after *cap* seconds; never prompts.

    A command that times out or cannot start is a failed one (exit 128), and so is one whose deadline has already
    passed: Git is then never started. Without ``until`` it runs for *cap* seconds at most. When *show*, Git writes to
    the terminal and only the exit code is returned.
    """
    seconds = cap if until is None else min(cap, until - time.monotonic())
    if seconds <= 0:
        return subprocess.CompletedProcess(["git", *args], 128, "", EXPIRED)
    try:
        return subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=cwd,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            stdin=subprocess.DEVNULL,
            capture_output=not show,
            text=True,
            timeout=seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        # Exit 1 can mean no match or a difference; failure to run Git cannot answer either probe.
        return subprocess.CompletedProcess(["git", *args], 128, "", str(exc))
