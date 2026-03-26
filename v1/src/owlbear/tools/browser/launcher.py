"""Edge browser launcher for CDP automation.

Provides functions to find, launch, probe, and terminate
Microsoft Edge with Chrome DevTools Protocol enabled.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import tempfile
from pathlib import Path

import httpx

# Standard Edge install locations on Windows
_EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_edge(*, executable: str | None = None) -> str | None:
    """Locate the Edge browser executable.

    Args:
        executable: Explicit path override. Returned as-is when provided.

    Returns:
        Path to the Edge binary, or ``None`` if not found.
    """
    if executable is not None:
        return executable

    for candidate in _EDGE_PATHS:
        path = Path(candidate)
        if path.exists():
            return str(path)

    return None


def launch_edge_cdp(*, port: int = 9222, executable: str | None = None) -> int:
    """Launch Edge with CDP remote-debugging enabled.

    Args:
        port: CDP debugging port.
        executable: Optional override for the Edge binary path.

    Returns:
        PID of the spawned Edge process.

    Raises:
        FileNotFoundError: If Edge cannot be found.
    """
    edge_path = find_edge(executable=executable)
    if edge_path is None:
        msg = "Microsoft Edge executable not found"
        raise FileNotFoundError(msg)

    user_data_dir = tempfile.mkdtemp()
    cmd = [
        edge_path,
        f"--remote-debugging-port={port}",
        "--no-first-run",
        f"--user-data-dir={user_data_dir}",
    ]

    proc = subprocess.Popen(cmd)  # noqa: S603
    return proc.pid


async def is_cdp_available(port: int = 9222) -> bool:
    """Check whether the CDP endpoint is responding.

    Args:
        port: CDP debugging port to probe.

    Returns:
        ``True`` if ``/json/version`` returns HTTP 200, ``False`` otherwise.
    """
    url = f"http://localhost:{port}/json/version"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(3, connect=2)) as client:
            resp = await client.get(url)
            return resp.status_code == 200  # noqa: PLR2004
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def kill_edge(pid: int) -> None:
    """Terminate an Edge process by PID.

    Silently ignores processes that are already dead or owned by
    another user.

    Args:
        pid: Process ID to terminate.
    """
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.kill(pid, signal.SIGTERM)
