"""The one-time carry of today's built-in settings into the shared repository's Global layer (2026-10-23).

The update that removed code defaults runs it when the machine host starts: a Global layer below
``CARRIED_FORMAT`` gets every field it leaves unset from ``carried.layer``, in one commit; a start after a failed
commit commits the filled layer without filling it again; afterwards nothing does. Each machine's first start then
moves its own machine settings: the first move fills Global's and marks it moved, later ones copy nothing (``move``).
Both run on a current checkout (``sync``) and, like every Settings save, keep their progress when publishing fails;
nothing is ever undone automatically.

The credit limits' upgrade (``limits``, D-01M5XCD49YHHR1NQKKY8TQD0C3) saves an existing Global in format 16 once, so
the limits its migration writes are in the file and published with it; nothing else of Global is filled again.
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
    from collections.abc import Callable, Sequence
    from pathlib import Path

    from owlbear_delivery_next.local_system.data_repo import DataRepo

    type Keep = Callable[[str], None]

MESSAGE = "settings: today's built-in values carried into Global"  # the carry's commit, found again in the history
MOVED = "settings: this machine's settings moved into Global"
LIMITS = "settings: the credit limits written into Global"  # the limits' upgrade commit
LIMITS_FORMAT = 16  # the format that writes the credit limits into Global
REACHED = '"format": (1[6-9]|[2-9][0-9]|[1-9][0-9]{2,})([^0-9]|$)'  # a Global line of format 16 or later (-G, ERE)
MARK = '"machine_moved": true'  # the moved mark as every write of Global spells it (``model_dump_json(indent=1)``)
EDITED = "the global settings have an edit that is not saved; the carry waits until it is saved or undone"


def _ignore(_digest: str) -> None:
    """What a carry wrote, unrecorded: a caller without a record of its own."""


def due(shared: DataRepo) -> bool:
    """Whether the carry has work: values to fill in, or a filled Global layer whose carry was never committed.

    Once a carry or a move is in the history, never again: a Global the owner deleted, remade or restored stays his.
    """
    until = time.monotonic() + data_repo.GIT_SECONDS
    return not _done(shared, until) and (_unfilled(shared) or _unpublished(shared))


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
            gone = not shared.global_path.exists() and _ran(shared, "HEAD", MESSAGE, until)
            if not gone and not _moved(shared, until):  # a Global the owner deleted or remade stays his
                have = (read_layer(shared.global_path, GlobalLayer).machine or MachineValues()).model_dump(
                    exclude_none=True
                )
                values = MachineValues.model_validate(MACHINE.model_dump() | local.model_dump(exclude_none=True) | have)
                update_layer(shared.global_path, GlobalLayer,
                             lambda g: g.model_copy(update={"machine": values, "machine_moved": True}))  # fmt: skip
                keep(_digest(shared.global_path))
        return shared.publish(shared.global_path, MOVED, until)


def limits_due(shared: DataRepo) -> bool:
    """Whether the credit limits' upgrade has work: an existing Global below format 16, or one not yet published.

    Once the published Global has ever been in format 16 or later, never again: one the owner restores or remakes
    older stays his (as for the carry), and his reads still get the limits from the migration. A git command that
    fails raises ``DataRepoError``, so an unknown state never counts as done.
    """
    until = time.monotonic() + data_repo.GIT_SECONDS
    rel = shared.global_path.relative_to(shared.root).as_posix()
    if _checked(shared, until, "log", "-1", "--format=%H", f"-G{REACHED}", "@{upstream}", "--", rel):
        return False
    if _checked(shared, until, "log", "-1", "--format=%H", f"-G{REACHED}", "HEAD", "--", rel):
        return True  # committed here, its push still pending
    try:
        found = _format(shared.global_path.read_text())
    except FileNotFoundError:
        return False  # no Global, or the owner deleted it: a fresh one is the carry's, which writes the limits too
    except OSError:
        return False  # an unreadable layer is reported where it is read, never overwritten here
    return found is not None


def limits(shared: DataRepo, keep: Keep = _ignore) -> str:
    """Save Global in format 16 with the credit limits its migration wrote, and publish it; what to know, else ''.

    Only the format and the limits change: the migration drops the daily budgets and adds a limit only where Global
    has none. A layer already in format 16 is only published, so a retry after a failed commit or push writes nothing
    again and a value the owner cleared since stays cleared. An unsaved owner edit of Global is never published.
    An invalid Global raises ``StoreError``; a git command that fails raises ``DataRepoError``.
    """
    until = time.monotonic() + data_repo.SAVE_SECONDS
    with shared.locked():
        if not limits_due(shared):
            return ""
        try:
            found = _format(shared.global_path.read_text())
        except FileNotFoundError:
            found = None  # deleted since its commit: only the push is left
        if found is not None and found < LIMITS_FORMAT:
            if _dirty(shared, until):
                return EDITED
            update_layer(shared.global_path, GlobalLayer, lambda g: g)  # the read migrates it; the write keeps it
            keep(_digest(shared.global_path))
        elif found is not None:  # written by an earlier start: an invalid layer is never published
            read_layer(shared.global_path, GlobalLayer)
        return shared.publish(shared.global_path, LIMITS, until)


def sync(shared: DataRepo, written: Sequence[str]) -> str:
    """Bring the checkout current before a carry or a move writes; why it cannot be, else ''.

    It fetches and pulls. An unsaved Global that is not exactly this machine's last carry or move write (*written*)
    is the owner's, and nothing goes on. When the remote changed Global while this machine has an unpublished carry or
    move of it, both are kept as they are and the owner chooses: nothing is undone automatically.
    """
    until = time.monotonic() + data_repo.SAVE_SECONDS
    rel = shared.global_path.relative_to(shared.root).as_posix()
    with shared.locked():
        if shared.git("rev-parse", "--abbrev-ref", "@{upstream}", until=until).returncode:
            return "the shared repository's branch tracks no upstream, or it cannot be read"
        _checked(shared, until, "fetch", "-q")
        dirty = _dirty(shared, until)
        if dirty and not _own(shared, rel, written, until):
            return EDITED
        base = _checked(shared, until, "merge-base", "HEAD", "@{upstream}")
        mine = dirty or bool(_checked(shared, until, "diff", "--name-only", base, "HEAD", "--", rel))
        if mine and _checked(shared, until, "log", "-1", "--format=%H", "HEAD..@{upstream}", "--", rel):
            return (
                f"another machine changed the global settings while this machine's settings carry in {shared.root} "
                f"was not published; publish or undo this machine's change of {rel} there by hand"
            )
        if dirty or _checked(shared, until, "rev-list", "--count", "HEAD..@{upstream}") == "0":
            return ""  # an unpublished carry or move is published by its own step
        return shared.pull(until)


def _own(shared: DataRepo, rel: str, written: Sequence[str], until: float) -> bool:
    """Whether unsaved Global holds exactly this machine's last carry or move write.

    The file must hold it; the index must hold it too, or still the committed copy, or no entry because that write
    created Global. A missing entry for a committed Global is the owner's staged deletion.
    """
    last = written[-1] if written else ""
    if not last or not shared.global_path.exists() or _digest(shared.global_path) != last:
        return False
    tracked = bool(_checked(shared, until, "ls-tree", "--name-only", "HEAD", "--", rel))
    if not _checked(shared, until, "ls-files", "--", rel):
        return not tracked  # no index entry: a new Global, never staged, or the owner's staged deletion
    staged = _digest_of(_blob(shared, f":{rel}", until))
    return staged == last or (tracked and staged == _digest_of(_blob(shared, f"HEAD:{rel}", until)))


def _blob(shared: DataRepo, spec: str, until: float) -> bytes:
    done = shared.git("show", spec, until=until)
    if done.returncode:
        msg = f"git show {spec} failed in {shared.root}: {done.stderr.strip()[:200]}"
        raise data_repo.DataRepoError(msg)
    return done.stdout.encode()


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
    except FileNotFoundError:
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
    """The committed Global layer's format: 0 when none is committed, ``None`` when it is no layer.

    A git command that fails raises ``DataRepoError``, so nothing goes on from an unknown state.
    """
    until = time.monotonic() + data_repo.GIT_SECONDS
    rel = shared.global_path.relative_to(shared.root).as_posix()
    if _checked(shared, until, "ls-tree", "--name-only", "HEAD", "--", rel):
        return _format(_checked(shared, until, "show", f"HEAD:{rel}"))
    return 0


def _done(shared: DataRepo, until: float) -> bool:
    """Whether a carry or a move is in the history: the built-in values were carried once."""
    return _ran(shared, "HEAD", MESSAGE, until) or _moved(shared, until)


def _moved(shared: DataRepo, until: float) -> bool:
    """Whether Global's history ever held the moved mark, whichever commit brought it.

    That is the move's own commit, or a Settings save that committed it after the move's commit failed. Its removal
    by a deletion or a remake is found too.
    """
    rel = shared.global_path.relative_to(shared.root).as_posix()
    return bool(_checked(shared, until, "log", "-1", "--format=%H", f"-G{MARK}", "HEAD", "--", rel))
