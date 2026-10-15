"""OwlBear's one folder on this machine (TD-139, TD-161): worktrees, snapshots, the data pointer and the design pack.

``OWLBEAR_HOME`` moves the whole tree. Without it the folder is ``~/Library/Application Support/OwlBear`` on macOS
and ``$XDG_DATA_HOME/owlbear`` elsewhere. Until ``owlbear-next home --move`` copies them over, files that only the
old ``~/.owlbear`` holds are read there; writes always go to the new folder, so its copy wins and the old one stays
as a backup.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ENV = "OWLBEAR_HOME"
POINTER, PACKS = "data.json", "design-pack"
MOVED = (POINTER, PACKS)  # what the old folder held; worktrees and snapshots were never there


def root() -> Path:
    """The folder every write goes to."""
    if home := os.environ.get(ENV):
        return Path(home)
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "OwlBear"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "owlbear"


def legacy() -> Path | None:
    """The old folder, read until its files are moved; none when ``OWLBEAR_HOME`` names the whole tree."""
    return None if os.environ.get(ENV) else Path.home() / ".owlbear"


def found(name: str, *older: str) -> Path:
    """Where to read *name*: the new folder, unless only the old one holds it (or one of its *older* names)."""
    new, old = root() / name, legacy()
    if new.exists() or old is None or not any((old / n).exists() for n in (name, *older)):
        return new
    return old / name


def plan() -> list[tuple[Path, Path]]:
    """The old files and folders a move would copy: those the new folder does not hold yet."""
    old = legacy()
    if old is None:
        return []
    return [(old / n, root() / n) for n in MOVED if (old / n).exists() and not (root() / n).exists()]


def move() -> list[tuple[Path, Path]]:
    """Copy each planned item into the new folder, keeping the old one as a backup; return what was copied."""
    done = []
    for old, new in plan():
        new.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if old.is_dir():
            shutil.copytree(old, new, symlinks=True)
        else:
            shutil.copy2(old, new)
        done.append((old, new))
    return done
