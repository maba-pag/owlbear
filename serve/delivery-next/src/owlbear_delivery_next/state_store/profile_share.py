"""The confirmed project profile: kept in the project's shared folder, re-checked once in each clone (TD-147).

Without a shared repository it stays in the clone's store. A clone's own profile moves to the shared folder once; the
old file stays as the recovery copy. A clone that found its profile in the shared folder detects its facts once at its
first host start, so confirmations that still hold carry over. Push permission, hooks and install facts stay in this
clone's overlay; another clone's shared copy of those facts never counts.
"""

from __future__ import annotations

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
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.profile_record import ProfileEntry
    from owlbear_delivery_next.local_system.data_repo import DataRepo
    from owlbear_delivery_next.state_store.store import Store

PROFILE = "profile.json"
LOCAL = "profile.local.json"
DETECTED = "profile.detected"  # a new marker forces the old unbound observations to be checked once
ROLES_MOVED = "roles-moved"  # marks that a format-1 profile's role overrides were merged into the settings


def path(store: Store) -> Path:
    """Where the project's profile is: in its shared folder, else in the clone's store."""
    return store.shared.root / store.name / PROFILE if store.shared else store.root / PROFILE


def write(store: Store, prof: Profile) -> str:
    """Write the profile; in the shared folder also commit and push it: what the owner should know, else nothing."""
    _keep_local(store, prof)
    if not store.shared:
        atomic_write(path(store), _shared_part(prof).model_dump_json(indent=1))
        return ""
    with store.shared.locked():
        return _publish(store, store.shared, prof, f"settings: {store.name}: project profile")


def read(store: Store) -> Profile | None:
    """Read through the format gate and overlay this clone's facts; absence alone returns None."""
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports this module

    source = path(store)
    try:
        source.stat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        msg = f"the profile is unreadable: {source}"
        raise StoreError(msg) from exc
    return merged(store, _read(source))


def merged(store: Store, prof: Profile) -> Profile:
    """Only this clone's own local source or overlay supplies its detected capabilities."""
    base = profile.shared_entries(prof.entries) if store.shared else prof.entries
    return prof.model_copy(update={"entries": {**base, **_local(store)}})


def _shared_part(prof: Profile) -> Profile:
    return prof.model_copy(update={"entries": profile.shared_entries(prof.entries)})


def _keep_local(store: Store, prof: Profile) -> None:
    local = {key: entry for key, entry in prof.entries.items() if profile.local_key(key)}
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


def _publish(store: Store, shared: DataRepo, prof: Profile, message: str) -> str:
    target = path(store)
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(target, _shared_part(prof).model_dump_json(indent=1))
    return shared.publish(target, message)


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
        if shared is None:
            write(store, fresh)
        elif not _replaced(store, shared, prof, fresh):
            return store.read_profile()  # retain the other writer's intent and this clone's fresh capabilities
    except DataRepoError as exc:
        msg = f"the detected profile could not be published: {exc}"
        raise StoreError(msg) from exc
    atomic_write(mark, f"profile v{fresh.version} detected in this clone\n")
    return fresh


def _replaced(store: Store, shared: DataRepo, old: Profile, new: Profile) -> bool:
    """Write *new* only while the shared profile is still *old*; whether it was written."""
    with shared.locked():
        _keep_local(store, new)
        current = store.read_profile()
        if current is None or _shared_part(current) != _shared_part(old):
            return False
        _publish(store, shared, new, f"settings: {store.name}: project profile detected in a clone")
    return True


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
