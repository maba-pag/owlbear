"""Each Change's and chat's arm of the Spotter's steered-versus-silent test (design §4): drawn once, kept for good.

A unit (``chg:<project>/<slug>`` or ``chat:<session-id>``) is drawn ``steered`` with the steer share's chance, else
``silent``, the first time it is asked for, by ``random.SystemRandom``; the draw is kept in ``arms.json`` in the
Spotter's owner-only folder (``~/.owlbear/spotter/``) and never drawn again, whatever the share is later and across
restarts, so all of a Change's steps, and all of a chat's turns, are in one arm. The file is read and written under its
lock and replaced atomically.
"""

from __future__ import annotations

import json
import os
import random
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal, cast

from owlbear_delivery_next.local_system import local_home, storage_io

if TYPE_CHECKING:
    from pathlib import Path

type Arm = Literal["steered", "silent"]
FILE, LOCK = "arms.json", "arms.lock"


def arm(unit: str, share: int) -> Arm:
    """*unit*'s arm: the one kept, else drawn now with *share* percent ``steered`` and kept.

    Raises:
        ValueError: The kept arms cannot be read as JSON (the file's path and the parser's error say where).
    """
    folder = local_home.root() / "spotter"
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
    try:
        lock = storage_io.open_lock(fd, blocking=True, name=LOCK)
        try:
            return _kept_or_drawn(folder / FILE, unit, share)
        finally:
            os.close(lock)
    finally:
        os.close(fd)


def _kept_or_drawn(path: Path, unit: str, share: int) -> Arm:
    raw = storage_io.read_regular(path)
    try:
        arms = json.loads(raw) if raw is not None else {}
    except ValueError as exc:
        msg = f"the Spotter's arms in {path} cannot be read: {exc}"
        raise ValueError(msg) from exc
    if unit in arms:
        return cast("Arm", arms[unit]["arm"])
    drawn: Arm = "steered" if random.SystemRandom().random() * 100 < share else "silent"
    arms[unit] = {"arm": drawn, "share": share, "at": datetime.now(UTC).isoformat(timespec="seconds")}
    storage_io.atomic_write(path, json.dumps(arms, indent=1, sort_keys=True) + "\n")
    return drawn
