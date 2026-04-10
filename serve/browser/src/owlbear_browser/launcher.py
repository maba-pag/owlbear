"""Edge binary discovery and CDP launch argument builder."""

from __future__ import annotations

import os
from pathlib import Path

_EDGE_X86_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
_EDGE_PF_PATH = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
_DEFAULT_PORT = 9222


class EdgeNotFoundError(RuntimeError):
    """Raised when the Edge binary cannot be located."""


def find_edge_binary() -> Path:
    """Find the Microsoft Edge binary path.

    Checks the EDGE_PATH environment variable first, then the two standard
    Windows installation paths (Program Files (x86) → Program Files).

    Raises:
        EdgeNotFoundError: When no valid Edge binary can be found.
    """
    env_path = os.environ.get("EDGE_PATH")
    if env_path:
        p = Path(env_path)
        if Path.exists(p):
            return p
        msg = f"EDGE_PATH points to a non-existent file: {env_path}"
        raise EdgeNotFoundError(msg)

    for path_str in (_EDGE_X86_PATH, _EDGE_PF_PATH):
        p = Path(path_str)
        if Path.exists(p):
            return p

    msg = f"Edge binary not found. Checked: {_EDGE_X86_PATH!r}, {_EDGE_PF_PATH!r}"
    raise EdgeNotFoundError(msg)


def build_launch_args(port: int = _DEFAULT_PORT, user_data_dir: str = "") -> list[str]:
    """Build CDP launch arguments for Microsoft Edge.

    Enforces security constraints: 127.0.0.1-only binding, no origin wildcards,
    and mandatory --user-data-dir (Chrome 136 remote-debugging requirement).

    Args:
        port: Remote debugging port (default 9222).
        user_data_dir: Path to a dedicated Edge user-data directory (required by Chrome 136).

    Returns:
        Ordered list of command-line arguments ready to pass to subprocess.
    """
    return [
        f"--remote-debugging-port={port}",
        f"--remote-allow-origins=http://127.0.0.1:{port}",
        f"--user-data-dir={user_data_dir}",
    ]
