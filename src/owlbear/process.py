"""Shared process-alive utility."""

from __future__ import annotations

import os


def is_process_alive(pid: int) -> bool:
    """Check whether *pid* refers to a running process (cross-platform)."""
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    else:
        return True
