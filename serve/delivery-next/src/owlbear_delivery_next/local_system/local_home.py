"""OwlBear's one folder on this machine (TD-198): worktrees, snapshots, the data pointer and the design pack.

It is always ``~/.owlbear``, on every system; nothing moves it.
"""

from __future__ import annotations

from pathlib import Path

POINTER, OLD_POINTER, PACKS = "data.json", "common.json", "design-pack"
RUNTIME, VERSIONS = "runtime", "versions"  # the alias to the active version, and the versions beside it


def root() -> Path:
    """The folder every read and write goes to."""
    return Path.home() / ".owlbear"


def stable(path: Path) -> Path:
    """How anything outside OwlBear names *path*, so a later version serves it.

    Through the runtime alias when *path* lies in the runtime or an installed version (self-update build §3);
    else *path* itself, as in a developer checkout.
    """
    home, folder = root(), path.parent.resolve()  # the file itself may be a link (a venv's python)
    bases = [(home / RUNTIME).resolve(), *(p.resolve() for p in (home / VERSIONS).glob("*") if p.is_dir())]
    for base in bases:
        if folder == base or base in folder.parents:
            return home / RUNTIME / folder.relative_to(base) / path.name
    return path
