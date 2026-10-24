"""Atomic Change identity allocation shared by shaping and setup-before-publication flows."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.state_store.database import put_record
from owlbear_delivery_next.state_store.store import HANDLE, StoreError

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Callable

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.state_store.store import Lock, Store

RESERVED = "reserved:"


def handles(store: Store) -> dict[str, str]:
    """Return existing handle-to-slug bindings, including handles in unloadable records."""
    found = {}
    for slug in store.slugs():
        try:
            found[store.read(slug).handle] = slug
        except StoreError:
            if raw := store.raw_handle(slug):
                found.setdefault(raw, slug)
    return found


def _claim(store: Store, db: sqlite3.Connection) -> tuple[int, list[str]]:
    reserved = {
        key.removeprefix(RESERVED): handle
        for key, handle in db.execute("SELECT key, value FROM meta WHERE key LIKE ?", (f"{RESERVED}%",))
    }
    held = [*handles(store), *reserved.values()]
    number = max([0, *(int(handle[1:]) for handle in held if HANDLE.fullmatch(handle)), store.issued()]) + 1
    db.execute("INSERT OR REPLACE INTO meta VALUES ('issued', ?)", (str(number),))
    return number, [*store.slugs(), *reserved]


def reserve(store: Store, name: Callable[[int, list[str]], str]) -> tuple[int, str]:
    """Reserve a handle and slug before setup; both remain burned if subsequent setup fails."""
    with store.db.write() as db:
        number, taken = _claim(store, db)
        slug = name(number, taken)
        if slug in taken:
            msg = f"{slug} is taken"
            raise StoreError(msg)
        db.execute("INSERT INTO meta VALUES (?, ?)", (RESERVED + slug, f"c{number}"))
    return number, slug


def publish_new(store: Store, make: Callable[[int, list[str]], Change]) -> Change:
    """Allocate and create a new Change in one cross-process SQLite transaction."""
    with store.db.write() as db:
        number, taken = _claim(store, db)
        change = make(number, taken)
        if change.slug in taken:
            msg = f"{change.slug} is taken"
            raise StoreError(msg)
        put_record(db, change.slug, change.model_dump_json(indent=1))
    return change


def publish_reserved(store: Store, lock: Lock, change: Change) -> None:
    """Finalize setup only for its reserved identity, refusing to overwrite an existing Change."""
    lock.check(change.slug)
    legacy = store.root / "changes" / change.slug / "change.json"
    with store.db.write() as db:
        row = db.execute("SELECT value FROM meta WHERE key = ?", (RESERVED + change.slug,)).fetchone()
        held = db.execute("SELECT 1 FROM changes WHERE slug = ?", (change.slug,)).fetchone()
        if not (row and row[0] == change.handle) or held or legacy.exists():
            msg = f"{change.slug} is not reserved for {change.handle} here"
            raise StoreError(msg)
        put_record(db, change.slug, change.model_dump_json(indent=1))
        db.execute("DELETE FROM meta WHERE key = ?", (RESERVED + change.slug,))
