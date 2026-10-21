"""Where a chat's memory server keeps entries when Delivery names no folder (TD-57, TD-72, TD-291).

Delivery's steps name both folders (``OWLBEAR_MEMORY_DIR``, ``OWLBEAR_MEMORY_GLOBAL_DIR``). A chat finds them as
Delivery does: the shared data repository the host passes down (``OWLBEAR_DATA``, empty for none) or the machine's
pointer ``~/.owlbear/data.json`` names, and in it the folder whose ``repository`` file holds the workspace's identity.
Its memory is that folder's ``memory``, Global memory the repository's own ``memory``.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

DATA_ENV = "OWLBEAR_DATA"
POINTER = Path(".owlbear") / "data.json"
CLAIM, MEMORY = "repository", "memory"


class StoreError(RuntimeError):
    """The shared repository's pointer or claims cannot tell the workspace's memory folder."""


def _git(cwd: Path, *args: str) -> str:
    quiet = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        done = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=cwd,
            env=quiet,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except OSError, subprocess.TimeoutExpired:
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def shared_root() -> Path | None:
    """The shared repository: the host's view when passed down, else the machine's pointer; None without either."""
    if (view := os.environ.get(DATA_ENV)) is not None:
        root = Path(view).expanduser().resolve() if view else None
        source = DATA_ENV
    else:
        path = Path.home() / POINTER
        try:
            root = Path(json.loads(path.read_text(encoding="utf-8"))["repository"]).expanduser().resolve()
        except FileNotFoundError:
            return None
        except (OSError, ValueError, KeyError, TypeError) as exc:
            msg = f"{path} names no shared repository"
            raise StoreError(msg) from exc
        source = str(path)
    if root is not None and _git(root, "rev-parse", "--show-toplevel") != str(root):
        msg = f"the shared repository {root}, named by {source}, is no git repository's top folder"
        raise StoreError(msg)
    return root


def identity(workspace: Path) -> str:
    """The workspace as Delivery names a project: its origin without scheme, user and ``.git``, else its path."""
    if url := _git(workspace, "config", "--get", "remote.origin.url"):
        bare = re.sub(r"^[a-z+]+://", "", url).split("@", 1)[-1].replace(":", "/", 1)
        return bare.removesuffix("/").removesuffix(".git")
    common = _git(workspace, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return str(Path(common).parent) if common else str(workspace.resolve())


def _held(claim: Path) -> str:
    try:
        return claim.read_text(encoding="utf-8").strip()
    except OSError, ValueError:
        return ""


def shared_stores(workspace: Path) -> tuple[Path, Path] | None:
    """The workspace's memory and Global memory in the shared repository; None when no folder there claims it."""
    if (root := shared_root()) is None:
        return None
    who = identity(workspace)
    found = sorted(claim.parent for claim in root.glob(f"*/{CLAIM}") if _held(claim) == who)
    if len(found) > 1:
        msg = f"the shared folders {', '.join(p.name for p in found)} all claim {who}; remove all but one"
        raise StoreError(msg)
    return (found[0] / MEMORY, root / MEMORY) if found else None
