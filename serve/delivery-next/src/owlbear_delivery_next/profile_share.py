"""The confirmed project profile: kept in the project's shared folder, re-checked once in each clone (TD-147).

Without a shared repository it stays in the clone's store. A clone's own profile moves to the shared folder once; the
old file stays as the recovery copy. A clone that found its profile in the shared folder detects its facts once at its
first host start, so confirmations that still hold carry over and facts of this machine (push permission) are its own.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from owlbear_delivery_next import migrations, profile
from owlbear_delivery_next.detector import DetectorError
from owlbear_delivery_next.storage_io import atomic_write, open_lock

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.profile_record import Profile
    from owlbear_delivery_next.store import Store

PROFILE = "profile.json"
CHECKED = "profile.checked"  # in the clone's store: this clone detected the shared profile's facts once
ROLES_MOVED = "roles-moved"  # marks that a format-1 profile's role overrides were merged into the settings


def path(store: Store) -> Path:
    """Where the project's profile is: in its shared folder, else in the clone's store."""
    return store.shared.root / store.name / PROFILE if store.shared else store.root / PROFILE


def write(store: Store, text: str) -> str:
    """Write the profile; in the shared folder also commit and push it: what the owner should know, else nothing."""
    if not store.shared:
        atomic_write(path(store), text)
        return ""
    with store.shared.locked():
        atomic_write(path(store), text)
        return store.shared.publish(path(store), f"settings: {store.name}: project profile")


def adopt(store: Store) -> None:
    """Move the clone's own profile to the project's shared folder once; the old file stays as the recovery copy."""
    local = store.root / PROFILE
    if not store.shared or not local.exists() or path(store).exists():
        return
    with store.shared.locked():
        if path(store).exists():  # another clone moved its profile while this one waited
            return
        path(store).parent.mkdir(parents=True, exist_ok=True)
        atomic_write(path(store), local.read_text())
        store.shared.publish(path(store), f"settings: {store.name}: project profile moved from its clone")
        local.replace(local.with_name(f"{PROFILE}.moved"))


def checked(store: Store, repo: Path) -> Profile | None:
    """The profile, its facts detected once in this clone; a failed detection is tried again at the next start."""
    from owlbear_delivery_next.store import StoreError  # noqa: PLC0415 - the store imports this module

    prof, mark = store.read_profile(), store.root / CHECKED
    if prof is None or not store.shared or mark.exists():
        return prof
    try:
        fresh = profile.detect(repo, profile.provider(prof, repo), prof)
        if fresh != prof:
            store.write_profile(fresh)
    except DetectorError, StoreError:
        return prof
    atomic_write(mark, f"profile v{fresh.version} detected in this clone\n")
    return fresh


def move_roles(store: Store) -> None:
    """Merge a format-1 profile's role overrides into the project settings, once.

    Fields the settings already set win; the old values fill only the empty ones. A marker then records the
    move, so an override cleared later never returns while the old profile is still on disk. An unreadable or
    invalid profile or settings file is left to ``read_profile`` and ``read_config`` to report.
    """
    from owlbear_delivery_next.store import SharedError, StoreError  # noqa: PLC0415 - the store imports this module

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
