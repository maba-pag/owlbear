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
from owlbear_delivery_next.settings.config import CARRIED_FORMAT, GlobalLayer, MachineValues
from owlbear_delivery_next.state_store.store import read_layer, update_layer

if TYPE_CHECKING:
    from owlbear_delivery_next.local_system.data_repo import DataRepo

MESSAGE = "settings: today's built-in values carried into Global"  # the carry's commit, found again in the history
MOVED = "settings: this machine's settings moved into Global"


def due(shared: DataRepo) -> bool:
    """Whether the carry has work: values to fill in, or a filled Global layer whose carry was never committed."""
    return _unfilled(shared) or _unpublished(shared)


def carry(shared: DataRepo, local: MachineValues | None = None) -> str:
    """Write the built-in values into the Global layer once and commit it; what the owner should know, else ''.

    Its machine settings take *local*, this machine's own, first. A layer already filled is only committed: a value
    the owner cleared after the carry is never filled again.
    """
    if not due(shared):
        return ""
    until = time.monotonic() + data_repo.SAVE_SECONDS
    with shared.locked():
        fill = _unfilled(shared)
        if not fill and not _unpublished(shared):  # another process carried and committed them meanwhile
            return ""
        if fill:
            since = _found(shared)
            update_layer(shared.global_path, GlobalLayer, lambda glob: filled(glob, since, local))
        else:  # an invalid layer is never published: it stays uncommitted, and the host says why (StoreError)
            read_layer(shared.global_path, GlobalLayer)
        return shared.publish(shared.global_path, MESSAGE, until)


def move(shared: DataRepo, local: MachineValues) -> str:
    """Copy this machine's settings into Global's where Global has none, in one commit; what the owner should know.

    An unreadable or invalid Global layer raises ``StoreError`` before anything changes, so the caller keeps its own
    values and tries again at the next start (the owner, 2026-10-23: every machine follows Global).
    """
    until = time.monotonic() + data_repo.SAVE_SECONDS
    with shared.locked():
        have = (read_layer(shared.global_path, GlobalLayer).machine or MachineValues()).model_dump(exclude_none=True)
        if local.model_dump(exclude_none=True).keys() - have.keys():
            values = MachineValues.model_validate(local.model_dump(exclude_none=True) | have)
            update_layer(shared.global_path, GlobalLayer, lambda glob: glob.model_copy(update={"machine": values}))
        return shared.publish(
            shared.global_path, MOVED, until
        )  # also what an earlier start left uncommitted or unpushed


def _format(text: str) -> int | None:
    """The layer's format; ``None`` when the text is no layer."""
    try:
        raw = json.loads(text)
        return int(raw.get("format", 0)) if isinstance(raw, dict) else None
    except ValueError, TypeError:
        return None


def _found(shared: DataRepo) -> int:
    """The Global layer's format as written, before any migration; the committed one's while it is deleted."""
    try:
        return _format(shared.global_path.read_text()) or 0
    except FileNotFoundError:
        return _committed(shared) or 0  # deleted after a carry: what the owner cleared stays cleared


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
    """The committed Global layer's format; ``None`` when it is no layer.

    With none committed it is 0, unless the history holds the carry: a deletion committed after it is the owner's.
    """
    rel = shared.global_path.relative_to(shared.root).as_posix()
    committed = shared.git("show", f"HEAD:{rel}")
    if committed.returncode == 0:
        return _format(committed.stdout)
    carried = shared.git("log", "-1", "--format=%H", "--fixed-strings", f"--grep={MESSAGE}", "--", rel)
    return CARRIED_FORMAT if carried.returncode == 0 and carried.stdout.strip() else 0
