"""The one-time carry of today's built-in settings into the shared repository's Global layer (2026-10-23).

The update that removed code defaults runs it when the machine host starts: a Global layer below
``CARRIED_FORMAT`` gets every field it leaves unset from ``carried.layer``, in one commit; a start after a failed
commit commits the filled layer without filling it again; afterwards nothing does. Each machine's first start then
moves its own machine settings: the first move fills Global's and marks it moved, later ones copy nothing (``move``).
Both run on a current checkout (``sync``) and, like every Settings save, keep their progress when publishing fails.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.settings.carried import MACHINE, filled
from owlbear_delivery_next.settings.config import CARRIED_FORMAT, GlobalLayer, MachineValues
from owlbear_delivery_next.state_store.store import read_layer, update_layer

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.local_system.data_repo import DataRepo

    type Keep = Callable[[str], None]

MESSAGE = "settings: today's built-in values carried into Global"  # the carry's commit, found again in the history
MOVED = "settings: this machine's settings moved into Global"
EDITED = "the global settings have an edit that is not saved; the carry waits until it is saved or undone"


def _ignore(_digest: str) -> None:
    """What a carry wrote, unrecorded: a caller without a record of its own."""


def due(shared: DataRepo) -> bool:
    """Whether the carry has work: values to fill in, or a filled Global layer whose carry was never committed."""
    return _unfilled(shared) or _unpublished(shared)


def carry(shared: DataRepo, keep: Keep = _ignore) -> str:
    """Write the built-in values into the Global layer once and commit it; what the owner should know, else ''.

    A layer already filled is only committed: a value the owner cleared after the carry is never filled again. The
    machine settings are ``move``'s. *keep* records what it wrote, so ``sync`` knows the write as its own.
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
            keep(_digest(shared.global_path))
        else:  # an invalid layer is never published: it stays uncommitted, and the host says why (StoreError)
            read_layer(shared.global_path, GlobalLayer)
        return shared.publish(shared.global_path, MESSAGE, until)


def move(shared: DataRepo, local: MachineValues, keep: Keep = _ignore) -> str:
    """Fill Global's machine settings once, marked as moved, and publish them; what the owner should know, else ''.

    Where Global has none, this machine's own *local* values go in, else the built-in ones. The mark is written with
    the values, so a retry only publishes what is there, and a later machine copies nothing: it follows Global, whose
    values the owner may have cleared since (the owner, 2026-10-23: move all, once). A publication that fails keeps
    its progress, as every Settings save does. An invalid Global raises ``StoreError``; a git command that fails
    raises ``DataRepoError``: neither ever counts as done.
    """
    until = time.monotonic() + data_repo.SAVE_SECONDS
    with shared.locked():
        if not read_layer(shared.global_path, GlobalLayer).machine_moved:
            if _dirty(shared, until):
                return EDITED
            deleted = not shared.global_path.exists() and _ran(shared, "HEAD", MOVED, until)
            if not deleted:  # a Global the owner deleted after a move stays deleted; what is unpushed is still pushed
                have = (read_layer(shared.global_path, GlobalLayer).machine or MachineValues()).model_dump(
                    exclude_none=True
                )
                values = MachineValues.model_validate(MACHINE.model_dump() | local.model_dump(exclude_none=True) | have)
                update_layer(shared.global_path, GlobalLayer,
                             lambda g: g.model_copy(update={"machine": values, "machine_moved": True}))  # fmt: skip
                keep(_digest(shared.global_path))
        return shared.publish(shared.global_path, MOVED, until)


def sync(shared: DataRepo, written: str) -> str:
    """Bring the checkout current before a carry or a move writes; why it cannot be, else ''.

    It fetches. When the remote changed Global meanwhile, this machine's own unpublished carry or move (its file
    still holding *written*, the digest of what it wrote) gives way: it is undone for Global alone and redone on
    the current layer if still due. Anything else unpublished in Global is the owner's: kept, and nothing moves on.
    """
    until = time.monotonic() + data_repo.SAVE_SECONDS
    rel = shared.global_path.relative_to(shared.root).as_posix()
    with shared.locked():
        if shared.git("rev-parse", "--abbrev-ref", "@{upstream}", until=until).returncode:
            return (
                "the shared repository's branch tracks no upstream, or it cannot be read; nothing moves until it does"
            )
        _checked(shared, until, "fetch", "-q")
        if _checked(shared, until, "log", "-1", "--format=%H", "HEAD..@{upstream}", "--", rel) and (
            why := _give_way(shared, rel, written, until)
        ):
            return why
        if _dirty(shared, until):  # this machine's own unpublished write is published by its step; else it waits
            return "" if _own(shared, written) else EDITED
        if _checked(shared, until, "rev-list", "--count", "HEAD..@{upstream}") == "0":
            return ""
        return shared.pull(until)


def _give_way(shared: DataRepo, rel: str, written: str, until: float) -> str:
    """Undo this machine's own unpublished carry or move of Global, and nothing else; why not, else ''."""
    base = _checked(shared, until, "merge-base", "HEAD", "@{upstream}")
    mine = _checked(shared, until, "log", "--format=%s", f"{base}..HEAD").splitlines()
    if mine:
        touched = set(_checked(shared, until, "diff", "--name-only", base, "HEAD").splitlines())
        shown = shared.git("show", f"HEAD:{rel}", until=until)
        own = set(mine) <= {MESSAGE, MOVED} and touched == {rel} and shown.returncode == 0
        if not (own and written and _digest_of(shown.stdout.encode()) == written and not _dirty(shared, until)):
            return "this machine has unpublished commits in the shared repository; push or undo them by hand"
        _checked(shared, until, "reset", "-q", "--soft", base)
    elif _dirty(shared, until):
        if not _own(shared, written):
            return EDITED
    else:
        return ""
    if _checked(shared, until, "ls-tree", "--name-only", "HEAD", "--", rel):
        _checked(shared, until, "restore", "--source=HEAD", "--staged", "--worktree", "--", rel)
    else:  # it created Global: it goes again, staged or not
        _checked(shared, until, "rm", "-q", "--cached", "--ignore-unmatch", "--", rel)
        shared.global_path.unlink(missing_ok=True)
    return ""


def _own(shared: DataRepo, written: str) -> bool:
    """Whether Global holds exactly what this machine's carry or move last wrote."""
    return bool(written) and shared.global_path.exists() and _digest(shared.global_path) == written


def _checked(shared: DataRepo, until: float, *args: str) -> str:
    """One git command's output; ``DataRepoError`` when it fails, so an unknown state never counts as known."""
    done = shared.git(*args, until=until)
    if done.returncode:
        msg = f"git {args[0]} failed in {shared.root}: {done.stderr.strip()[:200]}"
        raise data_repo.DataRepoError(msg)
    return done.stdout.strip()


def _dirty(shared: DataRepo, until: float) -> bool:
    rel = shared.global_path.relative_to(shared.root).as_posix()
    return bool(_checked(shared, until, "status", "--porcelain", "--", rel))


def _ran(shared: DataRepo, ref: str, message: str, until: float) -> bool:
    """Whether *ref*'s history holds a commit with *message*; a failed search raises."""
    return bool(_checked(shared, until, "log", "-1", "--format=%H", "--fixed-strings", f"--grep={message}", ref))


def _digest(path: Path) -> str:
    return _digest_of(path.read_bytes())


def _digest_of(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


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
    the owner's. A git command that fails raises ``DataRepoError``, so nothing goes on from an unknown state.
    """
    until = time.monotonic() + data_repo.GIT_SECONDS
    rel = shared.global_path.relative_to(shared.root).as_posix()
    if _checked(shared, until, "ls-tree", "--name-only", "HEAD", "--", rel):
        return _format(_checked(shared, until, "show", f"HEAD:{rel}"))
    return CARRIED_FORMAT if _ran(shared, "HEAD", MESSAGE, until) or _ran(shared, "HEAD", MOVED, until) else 0
