"""The design pack's one machine lock: an exclusive flock held through an open descriptor until the caller closes it."""

from __future__ import annotations

import fcntl
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


class HeldError(Exception):
    """Another project holds the machine's lock; ``who`` names it."""

    def __init__(self, who: str) -> None:
        super().__init__(who)
        self.who = who


def take(path: Path, owner: str, verify: Callable[[], None]) -> int:
    """Take the lock without waiting; ``verify`` runs while it is held. The caller closes the descriptor to release.

    Raises:
        HeldError: Another open descriptor holds the lock.
    """
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        raise HeldError(path.read_text(encoding="utf-8").strip() or "another project") from None
    try:
        verify()
        os.ftruncate(fd, 0)
        os.write(fd, owner.encode())
    except BaseException:
        os.close(fd)
        raise
    return fd
