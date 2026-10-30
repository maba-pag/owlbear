"""Impeccable's one machine lock: an exclusive flock held through an open descriptor until the caller closes it."""

from __future__ import annotations

import fcntl
import os
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

# A holder check takes the flock shared for an instant, and a child forked by another thread holds a copy until its
# exec: both end well within this, while an update holds the lock for minutes (#805).
SETTLE = 0.5
STEP = 0.01


class HeldError(Exception):
    """Another project holds the machine's lock; ``who`` names it."""

    def __init__(self, who: str) -> None:
        super().__init__(who)
        self.who = who


def take(path: Path, owner: str, verify: Callable[[], None]) -> int:
    """Take the lock, waiting only out a holding brief enough to be no update; ``verify`` runs while it is held.

    The caller closes the descriptor to release.

    Raises:
        HeldError: Another open descriptor still holds the lock after ``SETTLE`` seconds.
    """
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    until = time.monotonic() + SETTLE
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.monotonic() >= until:
                os.close(fd)
                raise HeldError(path.read_text(encoding="utf-8").strip() or "another project") from None
            time.sleep(STEP)
    try:
        verify()
        os.ftruncate(fd, 0)
        os.write(fd, owner.encode())
    except BaseException:
        os.close(fd)
        raise
    return fd
