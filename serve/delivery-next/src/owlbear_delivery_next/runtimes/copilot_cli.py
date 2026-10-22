"""The installed Copilot CLI that every SDK session and model list runs."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

FIX = (
    "Install the Copilot CLI with `brew install --cask copilot-cli` or set COPILOT_CLI_PATH to its absolute path; "
    "a Node version switch hides an `npm install -g` copy"
)
SHIM = "copilot-shim"  # VS Code's launcher; without a real CLI it asks on stdin whether to install one


def cli_path() -> str:
    """Return the installed Copilot CLI; the SDK's own runtime download fails behind the proxy (P3, S02)."""
    if not (path := os.environ.get("COPILOT_CLI_PATH") or find(os.environ.get("PATH", os.defpath))):
        msg = f"Copilot CLI {missing()}. {FIX}"
        raise FileNotFoundError(msg)
    return path


def find(path: str) -> str | None:
    """The `copilot` on *path*, skipping VS Code's shim."""
    dirs = path.split(os.pathsep)
    return shutil.which("copilot", path=os.pathsep.join(d for d in dirs if Path(d).name != SHIM))


def missing() -> str:
    """Why no Copilot CLI was found, naming VS Code's shim when it is the only `copilot` on PATH."""
    if (found := shutil.which("copilot")) and Path(found).parent.name == SHIM:
        return f"not found: only VS Code's shim {found}, which is not the CLI"
    return "not found"
