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
    since (the owner, 2026-10-23: move all, once). It runs only on a fetched, current checkout whose Global has no
    uncommitted edit, and a move that cannot commit and push is undone at once, so nothing is left half done: the
    caller keeps its own values and tries again at the next start. An invalid Global layer raises ``StoreError``.
    """
    until = time.monotonic() + data_repo.SAVE_SECONDS
    rel = shared.global_path.relative_to(shared.root).as_posix()
    with shared.locked():
        if why := _ready(shared, rel, until):
            return why
        glob = read_layer(shared.global_path, GlobalLayer)
        before = shared.git("rev-parse", "HEAD", until=until).stdout.strip()
        existed = shared.git("cat-file", "-e", f"{before}:{rel}", until=until).returncode == 0
        if not _moved(shared):
            have = (glob.machine or MachineValues()).model_dump(exclude_none=True)
            values = MachineValues.model_validate(MACHINE.model_dump() | local.model_dump(exclude_none=True) | have)
            update_layer(shared.global_path, GlobalLayer, lambda g: g.model_copy(update={"machine": values}))
        failed = shared.commit(shared.global_path, MOVED, until)
        if not failed and not _moved(shared):  # Global had them all: an empty commit records the move
            made = shared.git("commit", "-q", "--allow-empty", "-m", MOVED, "--", rel, until=until)
            failed = f"the move was not recorded: {made.stderr.strip()[:200]}" if made.returncode else ""
        if not failed and _upstream(shared, until):
            sent = shared.git("push", "-q", until=until)  # also what was unpushed before it
            failed = f"the move was not pushed: {sent.stderr.strip()[:200]}" if sent.returncode else ""
        if failed:
            shared.git("reset", "-q", "--keep", before, until=until)
            if existed:
                shared.git("checkout", "-q", before, "--", rel, until=until)  # its file and index as they were
            else:
                shared.git("rm", "-q", "--cached", "--ignore-unmatch", "--", rel, until=until)
                shared.global_path.unlink(missing_ok=True)
        return failed


def sync(shared: DataRepo) -> str:
    """Before any carry writes: fetch, and take in upstream commits this checkout lacks; why not, else ''.

    A Global layer with an uncommitted edit, such as a carry an earlier start could not commit, is left as it is.
    """
    until = time.monotonic() + data_repo.SAVE_SECONDS
    rel = shared.global_path.relative_to(shared.root).as_posix()
    with shared.locked():
        if shared.git("status", "--porcelain", "--", rel, until=until).stdout.strip():
            return ""
        return _ready(shared, rel, until)


def _upstream(shared: DataRepo, until: float) -> bool:
    return shared.git("rev-parse", "--abbrev-ref", "@{upstream}", until=until).returncode == 0


def _moved(shared: DataRepo, ref: str = "HEAD") -> bool:
    """Whether a machine's move is in *ref*'s history; its commit may change nothing, so no path limits the search."""
    found = shared.git("log", "-1", "--format=%H", "--fixed-strings", f"--grep={MOVED}", ref)
    return found.returncode == 0 and bool(found.stdout.strip())


def _ready(shared: DataRepo, rel: str, until: float) -> str:
    """Why a move waits: an uncommitted edit of Global, or a checkout that cannot be brought current; else ''."""
    if shared.git("status", "--porcelain", "--", rel, until=until).stdout.strip():
        return "the global settings have an uncommitted edit; the move waits until it is saved or undone"
    if not _upstream(shared, until):  # a local-only repository has nothing to fetch; a remote-backed one waits
        remotes = shared.git("remote", until=until).stdout.strip()
        return "the shared repository's branch tracks no upstream; the move waits until it does" if remotes else ""
    if (fetched := shared.git("fetch", "-q", until=until)).returncode:
        return f"the shared repository could not be fetched: {fetched.stderr.strip()[:200]}"
    behind = shared.git("rev-list", "--count", "HEAD..@{upstream}", until=until).stdout.strip()
    return shared.pull(until) if behind not in {"", "0"} else ""


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
