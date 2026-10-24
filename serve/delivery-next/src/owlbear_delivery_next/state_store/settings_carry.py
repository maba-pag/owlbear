"""The one-time carry of today's built-in settings into the shared repository's Global layer (2026-10-23).

The update that removed code defaults runs it when the machine host starts: a Global layer below
``CARRIED_FORMAT`` gets every field it leaves unset from ``carried.layer``, in one commit; a start after a failed
commit commits the filled layer without filling it again; afterwards nothing does. Each machine's first start then
moves its own machine settings: the first move fills Global's, later ones copy nothing (``move``).
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.settings.carried import MACHINE, filled
from owlbear_delivery_next.settings.config import CARRIED_FORMAT, GlobalLayer, MachineValues
from owlbear_delivery_next.state_store.store import read_layer, update_layer

if TYPE_CHECKING:
    from owlbear_delivery_next.local_system.data_repo import DataRepo

MESSAGE = "settings: today's built-in values carried into Global"  # the carry's commit, found again in the history
MOVED = "settings: this machine's settings moved into Global"


def due(shared: DataRepo) -> bool:
    """Whether the carry has work: values to fill in, or a filled Global layer whose carry was never committed."""
    return _unfilled(shared) or _unpublished(shared)


def carry(shared: DataRepo) -> str:
    """Write the built-in values into the Global layer once and commit it; what the owner should know, else ''.

    A layer already filled is only committed: a value the owner cleared after the carry is never filled again. The
    machine settings are ``move``'s.
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
        return shared.publish(shared.global_path, MESSAGE, until)


def move(shared: DataRepo, local: MachineValues) -> str:
    """The first machine's move fills Global's machine settings, in one commit; what the owner should know, else ''.

    Global's values stay; where it has none, this machine's own *local* values go in, else the built-in ones. Once a
    move is committed, a later machine copies nothing: it follows Global, whose values the owner may have cleared
    since (the owner, 2026-10-23: move all, once). An unreadable or invalid Global layer raises ``StoreError`` before
    anything changes, so the caller keeps its own values and tries again at the next start.
    """
    until = time.monotonic() + data_repo.SAVE_SECONDS
    with shared.locked():
        glob = read_layer(shared.global_path, GlobalLayer)
        if not _moved(shared):
            have = (glob.machine or MachineValues()).model_dump(exclude_none=True)
            values = MachineValues.model_validate(MACHINE.model_dump() | local.model_dump(exclude_none=True) | have)
            update_layer(shared.global_path, GlobalLayer, lambda g: g.model_copy(update={"machine": values}))
        if failed := shared.publish(shared.global_path, MOVED, until):  # also what an earlier start left unpublished
            return failed
        if _moved(shared):
            return ""
        rel = shared.global_path.relative_to(shared.root).as_posix()  # Global had them all: the move is recorded
        made = shared.git("commit", "-q", "--allow-empty", "-m", MOVED, "--", rel, until=until)
        if made.returncode:
            return f"the move was not recorded: {made.stderr.strip()[:200]}"
        return shared.publish(shared.global_path, MOVED, until)


def _moved(shared: DataRepo) -> bool:
    """Whether a machine's move is in the history; its commit may change nothing, so no path limits the search."""
    found = shared.git("log", "-1", "--format=%H", "--fixed-strings", f"--grep={MOVED}")
    return found.returncode == 0 and bool(found.stdout.strip())


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
    """The committed Global layer's format; ``None`` when it is no layer.

    With none committed it is 0, unless the history holds the carry or a move: a deletion committed after either is
    the owner's.
    """
    rel = shared.global_path.relative_to(shared.root).as_posix()
    committed = shared.git("show", f"HEAD:{rel}")
    if committed.returncode == 0:
        return _format(committed.stdout)
    found = shared.git("log", "-1", "--format=%H", "--fixed-strings", f"--grep={MESSAGE}", f"--grep={MOVED}")
    return CARRIED_FORMAT if found.returncode == 0 and found.stdout.strip() else 0
