"""The chats follower's lock (``chats.lock``): at most one follower follows the chats, a second one waits for it."""

from __future__ import annotations

import fcntl
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import threading
    from collections.abc import Callable


def held(fd: int, closed: threading.Event, poll: float, say: Callable[[str], None]) -> bool:
    """Take the lock open at *fd*, trying every *poll* seconds and *say*-ing once that it waits; False once *closed*."""
    waited = False
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            if not waited:
                say("chats follower: waiting for the previous one to end; no chat is read meanwhile")
                waited = True
            if closed.wait(poll):
                return False
        else:
            return True
