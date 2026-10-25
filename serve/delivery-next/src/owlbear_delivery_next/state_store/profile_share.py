"""The confirmed project profile: kept in the project's shared folder, re-checked once in each clone (TD-147).

Without a shared repository it stays in the clone's store. A clone's own profile moves to the shared folder once; the
old file stays as the recovery copy. A clone that found its profile in the shared folder detects its facts once at its
first host start, so confirmations that still hold carry over. Push permission, hooks and install facts stay in this
clone's overlay; another clone's shared copy of those facts never counts.
"""

from __future__ import annotations

import contextlib
import json
import os
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.profile_record import PROFILE_FORMAT, Profile
from owlbear_delivery_next.design_packs.detector import DetectorError
from owlbear_delivery_next.github.provider import ProviderError
from owlbear_delivery_next.local_system.data_repo import DataRepoError
from owlbear_delivery_next.local_system.storage_io import atomic_write, open_lock
from owlbear_delivery_next.settings import migrations, profile

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.profile_record import ProfileEntry
    from owlbear_delivery_next.local_system.data_repo import DataRepo
    from owlbear_delivery_next.state_store.store import Store

PROFILE = "profile.json"
LOCAL = "profile.local.json"
DETECTED = "profile.detected"  # a new marker forces the old unbound observations to be checked once
ROLES_MOVED = "roles-moved"  # marks that a format-1 profile's role overrides were merged into the settings
UNPUBLISHED = "prefs-import.unpublished"  # the legacy import is done here but its completion was not published yet


def path(store: Store) -> Path:
    """Where the project's profile is: in its shared folder, else in the clone's store."""
    return store.shared.root / store.name / PROFILE if store.shared else store.root / PROFILE


def write(store: Store, prof: Profile) -> str:
    """Write the profile; in the shared folder also commit and push it: what the owner should know, else nothing."""
    with _writer(store):
        current = _read_unlocked(store)
        if current is not None:  # only mark() moves the legacy import marker; a snapshot never rewinds it
            prof = prof.model_copy(update={"prefs_import": current.prefs_import, "prefs_basis": current.prefs_basis})
        _keep_local(store, prof)
        return _publish(store, store.shared, prof, f"settings: {store.name}: project profile")


def mark(store: Store, expect: str, to: str, basis: str = "") -> tuple[str, str, bool]:
    """Move the legacy import marker from *expect* to *to* on the latest profile.

    Returns (state after, publication notice, applied): *applied* is False when the marker was not at *expect*, so
    another run made the move and this one changed nothing. A pending claim records its config *basis*; leaving
    pending clears it.
    """
    from owlbear_delivery_next.state_store.store import SharedError  # noqa: PLC0415 - the store imports this module

    with _writer(store):
        prof = _read_unlocked(store)
        if prof is None or prof.prefs_import != expect:
            return (prof.prefs_import if prof else "", "", False)
        marked = prof.model_copy(update={"prefs_import": to, "prefs_basis": basis if to == "pending" else ""})
        _keep_local(store, marked)
        try:
            notice = _publish(store, store.shared, marked, f"settings: {store.name}: legacy preference import {to}")
        except DataRepoError as exc:
            if to == "done":
                _unpublished(store, failed=True)
            raise SharedError(str(exc)) from exc
        if to == "done":
            _unpublished(store, failed=bool(notice))
        return to, notice, True


def unpublished(store: Store) -> bool:
    """Whether a completed legacy import is marked done here but its publication was refused, so it still needs one."""
    return (store.root / UNPUBLISHED).exists()


def _unpublished(store: Store, *, failed: bool) -> None:
    flag = store.root / UNPUBLISHED
    if failed:
        store.root.mkdir(parents=True, exist_ok=True)
        flag.touch()
    else:
        flag.unlink(missing_ok=True)


def retry(store: Store) -> str:
    """Publish the current completed marker again after a refusal; the publication notice when it is still refused."""
    if not unpublished(store):
        return ""
    with _writer(store):
        prof = _read_unlocked(store)
        if prof is None or prof.prefs_import != "done":
            _unpublished(store, failed=False)
            return ""
        try:
            notice = _publish(store, store.shared, prof, f"settings: {store.name}: legacy preference import done")
        except DataRepoError as exc:
            notice = str(exc)
        _unpublished(store, failed=bool(notice))
        return notice


@contextlib.contextmanager
def _writer(store: Store, *, create: bool = True) -> Iterator[None]:
    if store.shared:
        with store.shared.locked():
            yield
        return
    if create:
        store.root.mkdir(parents=True, exist_ok=True)
    directory = os.open(store.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = open_lock(directory, blocking=True, name=".profile.lock")
    finally:
        os.close(directory)
    try:
        yield
    finally:
        os.close(fd)


def read(store: Store) -> Profile | None:
    """Read both profile halves under their writer lock; absence alone returns None."""
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports this module

    if not _present(path(store)):
        return None
    try:
        with _writer(store, create=False):
            return _read_unlocked(store)
    except FileNotFoundError:
        return None
    except (DataRepoError, OSError, ValueError) as exc:
        msg = f"the profile could not be read: {exc}"
        raise StoreError(msg) from exc


def _read_unlocked(store: Store) -> Profile | None:
    """The coherent reader for a caller already holding the profile's writer lock."""
    source = path(store)
    return merged(store, _read(source)) if _present(source) else None


def _present(source: Path) -> bool:
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports this module

    try:
        source.stat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        msg = f"the profile is unreadable: {source}"
        raise StoreError(msg) from exc
    return True


def merged(store: Store, prof: Profile) -> Profile:
    """Only this clone's own local source or overlay supplies its detected capabilities."""
    base = profile.shared_entries(prof.entries) if store.shared else prof.entries
    return prof.model_copy(update={"entries": {**base, **_local(store)}})


def _shared_part(prof: Profile) -> Profile:
    return prof.model_copy(update={"entries": profile.shared_entries(prof.entries)})


def _local_part(prof: Profile) -> dict[str, ProfileEntry]:
    return {key: entry for key, entry in prof.entries.items() if profile.local_key(key)}


def _keep_local(store: Store, prof: Profile) -> None:
    local = _local_part(prof)
    store.root.mkdir(parents=True, exist_ok=True)
    overlay = store.root / LOCAL
    if local:
        atomic_write(overlay, Profile(entries=local).model_dump_json(indent=1))
    else:
        overlay.unlink(missing_ok=True)


def _read(source: Path) -> Profile:
    from owlbear_delivery_next.state_store.store import _load  # noqa: PLC0415 - the store imports this module

    return _load(source, Profile, PROFILE_FORMAT, migrations.PROFILE)


def _local(store: Store) -> dict[str, ProfileEntry]:
    from owlbear_delivery_next.state_store.store import StoreError, _parse  # noqa: PLC0415 - circular at import time

    overlay = store.root / LOCAL
    try:
        fd = os.open(overlay, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return {}
    except OSError as exc:
        msg = f"this clone's profile facts are unreadable: {overlay}"
        raise StoreError(msg) from exc
    try:
        with os.fdopen(fd, encoding="utf-8") as source:
            local = _parse(source.read(), "profile.local", Profile, PROFILE_FORMAT, migrations.PROFILE)
    except (OSError, UnicodeError) as exc:
        msg = f"this clone's profile facts are unreadable: {overlay}"
        raise StoreError(msg) from exc
    if any(not profile.local_key(key) for key in local.entries):
        msg = "the clone's profile overlay contains non-local facts"
        raise StoreError(msg)
    return local.entries


def _publish(store: Store, shared: DataRepo | None, prof: Profile, message: str) -> str:
    target = path(store)
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(target, _shared_part(prof).model_dump_json(indent=1))
    return shared.publish(target, message) if shared else ""


def adopt(store: Store) -> None:
    """Move the clone's own profile to the project's shared folder once, after its roles moved; the old file stays."""
    local = store.root / PROFILE
    if not store.shared or not local.exists() or path(store).exists() or not (store.root / ROLES_MOVED).exists():
        return
    with store.shared.locked():
        if path(store).exists():  # another clone moved its profile while this one waited
            return
        path(store).parent.mkdir(parents=True, exist_ok=True)
        own = _read(local)
        own = own.model_copy(update={"entries": {**own.entries, **_local(store)}})
        _keep_local(store, own)
        _publish(store, store.shared, own, f"settings: {store.name}: project profile moved from its clone")
        local.replace(local.with_name(f"{PROFILE}.moved"))


def checked(store: Store, repo: Path) -> Profile | None:
    """Observe shared or unbound legacy facts once in this clone; only a saved success gets its marker."""
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports this module

    prof, mark, shared = store.read_profile(), store.root / DETECTED, store.shared
    if prof is None or mark.exists():
        return prof
    if shared is None and not profile.unbound(prof):
        return prof
    try:
        fresh = profile.detect(repo, profile.provider(prof, repo), prof)
    except DetectorError, ProviderError:
        return prof
    try:
        kept = _replaced(store, prof, fresh)
        if kept is None:
            return store.read_profile()  # a changed snapshot must be reconciled before detection is acknowledged
        fresh = kept
    except DataRepoError as exc:
        msg = f"the detected profile could not be published: {exc}"
        raise StoreError(msg) from exc
    atomic_write(mark, f"profile v{fresh.version} detected in this clone\n")
    return fresh


def _replaced(store: Store, old: Profile, new: Profile) -> Profile | None:
    """Keep concurrent local intent; publish fresh shared facts only against the snapshot they observed."""
    with _writer(store):
        current = _read_unlocked(store)
        before, now = _local_part(old), _local_part(current) if current is not None else _local(store)
        found = _local_part(new)
        local: dict[str, ProfileEntry] = {}
        for key in sorted(before.keys() | now.keys() | found.keys()):
            entry = now.get(key) if now.get(key) != before.get(key) else found.get(key)
            if entry is not None:
                local[key] = entry
        kept = new.model_copy(update={"entries": {**profile.shared_entries(new.entries), **local}})
        _keep_local(store, kept)
        if current is None or _shared_part(current) != _shared_part(old):
            return None
        notice = _publish(store, store.shared, kept, f"settings: {store.name}: project profile detected in a clone")
        if notice:
            raise DataRepoError(notice)
    return None if now != before else kept


def move_roles(store: Store) -> None:
    """Merge a format-1 profile's role overrides into the project settings, once.

    Fields the settings already set win; the old values fill only the empty ones. A marker then records the
    move, so an override cleared later never returns while the old profile is still on disk. An unreadable or
    invalid profile or settings file is left to ``read_profile`` and ``read_config`` to report.
    """
    from owlbear_delivery_next.state_store.store import (  # noqa: PLC0415 - the store imports this module
        SharedError,
        StoreError,
    )

    old, marker = store.root / PROFILE, store.root / ROLES_MOVED
    if marker.exists() or not old.exists():
        return
    dir_fd = os.open(store.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = open_lock(dir_fd, blocking=True, name=f".{ROLES_MOVED}.lock")
    finally:
        os.close(dir_fd)
    try:
        if marker.exists():  # another opener finished the move while this one waited
            return
        try:
            data = json.loads(old.read_text())
            found = migrations.ROLES.validate_python(data.get("roles", {})) if int(data.get("format", 0)) == 1 else {}
        except AttributeError, OSError, TypeError, ValueError:
            return  # read_profile reports the damaged profile
        if found:
            try:
                store.update_config(
                    lambda cur: migrations.with_roles(cur, found), "role overrides from the old profile"
                )
            except SharedError:
                raise  # the old roles move later; never mark a move that did not happen
            except StoreError:
                return  # refused before writing; read_config reports the damaged settings
        atomic_write(marker, "the format-1 profile's role overrides are merged into config.json\n")
    finally:
        os.close(fd)
