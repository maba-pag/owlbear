"""OwlBear's one folder on this machine (TD-198): worktrees, snapshots, the data pointer and the design pack.

It is always ``~/.owlbear``, on every system; nothing moves it.
"""

from __future__ import annotations

from pathlib import Path

POINTER, OLD_POINTER, PACKS = "data.json", "common.json", "design-pack"


def root() -> Path:
    """The folder every read and write goes to."""
    return Path.home() / ".owlbear"
