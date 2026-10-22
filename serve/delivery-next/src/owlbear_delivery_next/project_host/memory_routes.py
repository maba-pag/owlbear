"""The Memory page's API (TD-85): the project's agent memory in its shared-repository folder (TD-72), and Global.

Global memory (``<shared>/memory/``, TD-241) is read by every project's agents beside their own; the owner moves an
entry there with Make global, and back to the project it came from with Move back. ``?where=global`` reads and acts
on it.

Reads and the owner's actions go through the memory package's engine; each action
names the entry's ``updated_at`` the page showed, holds the shared repository's lock and the memory's writer lock, and
commits and pushes exactly the files the action changed before an agent can write again.
"""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Annotated, Any, Literal

from fastapi import APIRouter, HTTPException
from owlbear_memory import (
    ConcurrencyError,
    MemoryBusyError,
    MemoryCategory,
    MemoryEngine,
    MemoryEntry,
    MemoryState,
    NotFoundError,
    TransitionError,
    storage,
    writer_lock,
)
from owlbear_memory import ValidationError as MemoryValidationError
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from owlbear_delivery_next.local_system import data_repo

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_memory.engine import EditPayload

    from owlbear_delivery_next.state_store.store import Store

NO_SHARED = "No shared repository is set up, so agents keep no memory; set one with `owlbear-next data PATH`"
ENTRY = r"^[A-Za-z0-9-]{1,64}$"  # the engine's ids are UUIDs
type Where = Literal["project", "global"]


class Shown(BaseModel):
    """When the entry the page showed was last changed; any later change refuses the action."""

    model_config = ConfigDict(extra="forbid")

    updated_at: str = Field(min_length=1, max_length=64)


class EditBody(Shown):
    """The owner's edit; only the fields sent change."""

    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)] | None = None
    content: str | None = Field(default=None, max_length=1024)
    categories: list[MemoryCategory] | None = Field(default=None, min_length=1)


class PurgeBody(BaseModel):
    """Remove the files of entries deleted at least this many days ago; Git history keeps them."""

    model_config = ConfigDict(extra="forbid")

    min_age_days: int = Field(default=30, ge=0, le=3650)


def _shown(entry: MemoryEntry) -> dict[str, Any]:
    return entry.model_dump(mode="json", exclude={"assessment_receipts"})


REFUSED: tuple[tuple[type[Exception], int, str], ...] = (  # the first match answers; "" says the error's own text
    (NotFoundError, 404, "no such memory entry"),
    (MemoryBusyError, 409, "the memory is busy; try again"),
    (ConcurrencyError, 409, "this entry changed since the page loaded it; reload"),
    (TransitionError, 409, ""),
    (MemoryValidationError, 422, ""),
    (data_repo.DataRepoError, 409, ""),
)


def _files(folder: Path) -> dict[Path, bytes]:
    return {p: p.read_bytes() for p in folder.glob("*.md")}


def folder_of(store: Store, where: Where) -> Path:
    """The project's memory folder, or the shared repository's Global one."""
    if store.shared is None:
        raise HTTPException(409, NO_SHARED)
    return store.shared.root / "memory" if where == "global" else store.shared.memory_path(store.name)


def _refused(exc: Exception) -> HTTPException:
    status, said = next((s, t) for e, s, t in REFUSED if isinstance(exc, e))
    return HTTPException(status, said or str(exc))


def _act(
    store: Store, entry_id: str, what: str, do: Callable[[MemoryEngine], MemoryEntry], where: Where = "project"
) -> dict[str, Any]:
    """Run one owner action and publish the files it changed, under the shared and the memory writer lock."""
    folder = folder_of(store, where)
    if not re.fullmatch(ENTRY, entry_id):
        raise HTTPException(404, "no such memory entry")
    shared, until = store.shared, time.monotonic() + data_repo.SAVE_SECONDS
    label = "global" if where == "global" else store.name
    try:
        engine = MemoryEngine(folder)
        with shared.locked(), writer_lock(folder):
            before = _files(folder)
            entry = do(engine)
            after = _files(folder)
            changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
            notice = shared.publish(changed, f"memory {label}: {what} {entry.title}", until)
    except tuple(e for e, _, _ in REFUSED) as exc:
        raise _refused(exc) from exc
    return {"entry": _shown(entry), "notice": notice}


def _move(store: Store, entry_id: str, shown: str, *, back: bool) -> dict[str, Any]:
    """Move one entry between the project's memory and Global, as the page showed it, and publish both folders.

    Make global records the project it came from; it moves back only there, and without that record not at all (TD-292).
    """
    source, target = (
        folder_of(store, "global" if back else "project"),
        folder_of(store, "project" if back else "global"),
    )
    if not re.fullmatch(ENTRY, entry_id) or not source.is_dir():
        raise HTTPException(404, "no such memory entry")
    shared, until = store.shared, time.monotonic() + data_repo.SAVE_SECONDS
    target.mkdir(exist_ok=True)
    try:
        with shared.locked(), writer_lock(source), writer_lock(target):
            found = [(p, e) for p in sorted(source.glob("*.md")) if (e := storage.read_entry(p)) and e.id == entry_id]
            if len(found) != 1:
                raise NotFoundError(entry_id)
            path, entry = found[0]
            if _shown(entry)["updated_at"] != shown:
                raise ConcurrencyError(entry_id)
            if back and entry.origin is None:
                raise HTTPException(409, f"{entry.title} was made global before its project was recorded: it stays")
            if back and entry.origin != store.name:
                raise HTTPException(409, f"{entry.title} came from {entry.origin}: only it can take the entry back")
            if not back and entry.state in {MemoryState.PENDING, MemoryState.DELETED}:  # the project's curator first
                raise HTTPException(409, f"{entry.title} is {entry.state}: the curator scopes it before it goes global")
            moved = target / path.name
            if moved.exists() or any(getattr(storage.read_entry(p), "id", "") == entry_id for p in target.glob("*.md")):
                where = store.name if back else "Global memory"
                raise HTTPException(409, f"{where} holds {entry.title} already")
            moving = entry.model_copy(update={"origin": None if back else store.name})
            storage.write_entry(path, moving, memory_dir=source)  # rewritten in place, then moved whole
            try:
                path.replace(moved)
            except OSError as exc:
                storage.write_entry(path, entry, memory_dir=source)  # as it was, so the move can be tried again
                raise HTTPException(409, f"{entry.title} could not move: {exc.strerror or exc}; try again") from exc
            entry = moving
            what = "move back" if back else "make global"
            notice = shared.publish([path, moved], f"memory {store.name}: {what} {entry.title}", until)
    except tuple(e for e, _, _ in REFUSED) as exc:
        raise _refused(exc) from exc
    return {"entry": _shown(entry), "notice": notice}


def _purge(store: Store, days: int, where: Where) -> dict[str, Any]:
    """Remove the files of entries deleted ``days`` ago or earlier and publish their removal."""
    folder = folder_of(store, where)
    if not folder.is_dir():
        return {"purged": 0, "skipped": 0, "failed": 0, "notice": ""}
    shared, until = store.shared, time.monotonic() + data_repo.SAVE_SECONDS
    label = "global" if where == "global" else store.name
    try:
        with shared.locked(), writer_lock(folder):
            before = _files(folder)
            done = MemoryEngine(folder).purge(days)
            after = _files(folder)  # a duplicate repair on the way may add a recovered entry: publish it too
            changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
            notice = shared.publish(changed, f"memory {label}: purge {done.purged} deleted", until) if changed else ""
    except tuple(e for e, _, _ in REFUSED) as exc:
        raise _refused(exc) from exc
    return {"purged": done.purged, "skipped": done.skipped, "failed": done.failed, "notice": notice}


def router(store: Store) -> APIRouter:
    """The memory routes; the caller adds the token check."""
    routes = APIRouter()

    @routes.get("/memory")
    def listed(where: Where = "project") -> dict[str, Any]:
        if store.shared is None:
            return {"available": False, "reason": NO_SHARED, "entries": []}
        folder = folder_of(store, where)
        engine = MemoryEngine(folder)
        return {
            "available": True,
            "folder": str(folder),
            "repository": str(store.shared.root),
            "project": store.name,
            "entries": [_shown(e) for e in engine.get_entries()],
            "parse_errors": engine.parse_errors,
            "states": [s.value for s in MemoryState],
            "categories": [c.value for c in MemoryCategory],
        }

    @routes.post("/memory/{entry_id}/approve")
    def approve(entry_id: str, body: Shown, where: Where = "project") -> dict[str, Any]:
        return _act(store, entry_id, "approve", lambda e: e.approve(entry_id, body.updated_at), where)

    @routes.post("/memory/{entry_id}/resolve")
    def resolve(entry_id: str, body: Shown, where: Where = "project") -> dict[str, Any]:
        return _act(store, entry_id, "resolve", lambda e: e.resolve(entry_id, body.updated_at), where)

    @routes.post("/memory/{entry_id}/edit")
    def edit(entry_id: str, body: EditBody, where: Where = "project") -> dict[str, Any]:
        fields: EditPayload = body.model_dump(exclude={"updated_at"}, exclude_none=True)  # type: ignore[assignment]
        return _act(store, entry_id, "edit", lambda e: e.edit(entry_id, fields, body.updated_at), where)

    @routes.post("/memory/{entry_id}/make-global")
    def make_global(entry_id: str, body: Shown) -> dict[str, Any]:
        return _move(store, entry_id, body.updated_at, back=False)

    @routes.post("/memory/{entry_id}/move-back")
    def move_back(entry_id: str, body: Shown) -> dict[str, Any]:
        return _move(store, entry_id, body.updated_at, back=True)

    @routes.post("/memory/{entry_id}/delete")
    def delete(entry_id: str, body: Shown, where: Where = "project") -> dict[str, Any]:
        return _act(store, entry_id, "delete", lambda e: e.delete(entry_id, body.updated_at), where)

    @routes.post("/memory/purge")
    def purge(body: PurgeBody, where: Where = "project") -> dict[str, Any]:
        return _purge(store, body.min_age_days, where)

    return routes
