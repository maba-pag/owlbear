"""The one-time carry of today's built-in settings into the shared repository's Global layer (2026-10-23).

The update that removed code defaults runs it when the machine host starts: a Global layer below
``CARRIED_FORMAT`` gets every field it leaves unset from ``carried.layer``, in one commit; a start after a failed
commit commits the filled layer without filling it again; afterwards nothing does.
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.settings.carried import filled
from owlbear_delivery_next.settings.config import CARRIED_FORMAT, GlobalLayer
from owlbear_delivery_next.state_store.store import update_layer

if TYPE_CHECKING:
    from owlbear_delivery_next.local_system.data_repo import DataRepo


def due(shared: DataRepo) -> bool:
    """Whether the carry has work: values to fill in, or a filled Global layer an earlier start left uncommitted."""
    return _unfilled(shared) or _uncommitted(shared)


def carry(shared: DataRepo) -> str:
    """Write the built-in values into the Global layer once and commit it; what the owner should know, else ''.

    A layer already filled is only committed: a value the owner cleared after the carry is never filled again.
    """
    if not due(shared):
        return ""
    until = time.monotonic() + data_repo.SAVE_SECONDS
    with shared.locked():
        fill = _unfilled(shared)
        if not fill and not _uncommitted(shared):  # another process carried and committed them meanwhile
            return ""
        if fill:
            update_layer(shared.global_path, GlobalLayer, filled)
        return shared.publish(shared.global_path, "settings: today's built-in values carried into Global", until)


def _unfilled(shared: DataRepo) -> bool:
    """Whether the Global layer has not had the built-in values carried into it yet."""
    try:
        raw = json.loads(shared.global_path.read_text())
    except FileNotFoundError:
        return True
    except OSError, ValueError:
        return False  # an unreadable layer is reported where it is read, never overwritten here
    return not isinstance(raw, dict) or int(raw.get("format", 0)) < CARRIED_FORMAT


def _uncommitted(shared: DataRepo) -> bool:
    """Whether the Global layer differs from what is committed; a failed git status counts as committed."""
    found = shared.git("status", "--porcelain", "--", shared.global_path.relative_to(shared.root).as_posix())
    return found.returncode == 0 and bool(found.stdout.strip())
