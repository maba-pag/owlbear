"""The installed Copilot CLI that every SDK session and model list runs."""

from __future__ import annotations

import os
import shutil


def cli_path() -> str:
    """Return the installed Copilot CLI; the SDK's own runtime download fails behind the proxy (P3, S02)."""
    if not (path := os.environ.get("COPILOT_CLI_PATH") or shutil.which("copilot")):
        msg = "Copilot CLI not found; install it or set COPILOT_CLI_PATH"
        raise FileNotFoundError(msg)
    return path
