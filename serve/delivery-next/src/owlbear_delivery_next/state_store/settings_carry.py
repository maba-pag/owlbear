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
from owlbear_delivery_next.state_store.store import read_layer, update_layer

if TYPE_CHECKING:
    from owlbear_delivery_next.local_system.data_repo import DataRepo


def due(shared: DataRepo) -> bool:
    """Whether the carry has work: values to fill in, or a filled Global layer whose carry was never committed."""
    return _unfilled(shared) or _unpublished(shared)


def carry(shared: DataRepo) -> str:
    """Write the built-in values into the Global layer once and commit it; what the owner should know, else ''.

    A layer already filled is only committed: a value the owner cleared after the carry is never filled again.
    """
    if not due(shared):
        return ""
    until = time.monotonic() + data_repo.SAVE_SECONDS
    with shared.locked():
        fill = _unfilled(shared)
        if not fill and not _unpublished(shared):  # another process carried and committed them meanwhile
            return ""
        if fill:
            update_layer(shared.global_path, GlobalLayer, filled)
        else:  # an invalid layer is never published: it stays uncommitted, and the host says why (StoreError)
            read_layer(shared.global_path, GlobalLayer)
        return shared.publish(shared.global_path, "settings: today's built-in values carried into Global", until)


def _format(text: str) -> int | None:
    """The layer's format; ``None`` when the text is no layer."""
    try:
        raw = json.loads(text)
        return int(raw.get("format", 0)) if isinstance(raw, dict) else None
    except ValueError, TypeError:
        return None


def _unfilled(shared: DataRepo) -> bool:
    """Whether the Global layer has not had the built-in values carried into it yet."""
    try:
        found = _format(shared.global_path.read_text())
    except FileNotFoundError:  # deleted after a committed carry: the owner's to restore, never carried again
        found = _committed(shared)
    except OSError:
        return False  # an unreadable layer is reported where it is read, never overwritten here
    return found is not None and found < CARRIED_FORMAT


def _unpublished(shared: DataRepo) -> bool:
    """Whether the committed Global layer predates the carry: an earlier start filled it, and its commit failed.

    Later edits to a carried layer are never published here; a Settings save publishes them.
    """
    found = _committed(shared)
    return found is not None and found < CARRIED_FORMAT


def _committed(shared: DataRepo) -> int | None:
    """The committed Global layer's format: 0 when none is committed, ``None`` when it is no layer."""
    rel = shared.global_path.relative_to(shared.root).as_posix()
    committed = shared.git("show", f"HEAD:{rel}")
    return _format(committed.stdout) if committed.returncode == 0 else 0
