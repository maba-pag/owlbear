"""OwlBear's one folder on this machine (TD-139, TD-161): worktrees, snapshots, the data pointer and the design pack.

``OWLBEAR_HOME`` moves the whole tree. Without it the folder is ``~/Library/Application Support/OwlBear`` on macOS
and ``$XDG_DATA_HOME/owlbear`` elsewhere. Until ``owlbear-next home --move`` copies them over, items that only the
old ``~/.owlbear`` holds are read there, each on its own; nothing ever writes or deletes there, so the old folder
stays as a backup and the new folder's copy wins.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

ENV = "OWLBEAR_HOME"
POINTER, OLD_POINTER, PACKS = "data.json", "common.json", "design-pack"


def root() -> Path:
    """The folder every write goes to."""
    if home := os.environ.get(ENV):
        return Path(home)
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "OwlBear"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "owlbear"


def legacy() -> Path | None:
    """The old folder, read until its items are moved; none when ``OWLBEAR_HOME`` names the whole tree."""
    return None if os.environ.get(ENV) else Path.home() / ".owlbear"


def found(name: str) -> Path:
    """Where to read *name* (a path inside the folder): the new folder, unless only the old one holds it."""
    new, old = root() / name, legacy()
    return old / name if old is not None and not new.exists() and (old / name).exists() else new


def is_old(path: Path) -> bool:
    """Whether *path* lies in the old folder, where nothing is written."""
    old = legacy()
    return old is not None and path.is_relative_to(old)


def plan() -> list[tuple[Path, Path]]:
    """The old items a move would copy: the pointer (by either name) and each design-pack entry the new lacks."""
    old = legacy()
    if old is None:
        return []
    pointer = next((old / n for n in (POINTER, OLD_POINTER) if (old / n).is_file()), None)
    items = [(pointer, root() / POINTER)] if pointer else []
    if (old / PACKS).is_dir():
        items += [(p, root() / PACKS / p.name) for p in sorted((old / PACKS).iterdir())]
    return [(o, n) for o, n in items if not n.exists()]


def _copy(old: Path, new: Path) -> None:
    """Copy *old* beside *new* first and rename it into place, so a failed copy never shadows the backup."""
    new.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(dir=new.parent, prefix=f".{new.name}."))
    try:
        if old.is_dir():
            shutil.copytree(old, tmp / "x", symlinks=True)
        else:
            shutil.copy2(old, tmp / "x")
        (tmp / "x").rename(new)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def move() -> list[tuple[Path, Path]]:
    """Copy each planned item into the new folder, keeping the old one; return what was copied."""
    done = []
    for old, new in plan():
        _copy(old, new)
        done.append((old, new))
    return done
