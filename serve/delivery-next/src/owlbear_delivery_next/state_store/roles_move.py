"""Merge a format-1 profile's role overrides into the project settings, once (R15)."""

from __future__ import annotations

import hashlib
import json
import os
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.profile_record import PROFILE_FORMAT, Profile
from owlbear_delivery_next.local_system.storage_io import atomic_write, open_lock
from owlbear_delivery_next.settings import migrations
from owlbear_delivery_next.settings.config import Layer
from owlbear_delivery_next.state_store.layers import read_layer
from owlbear_delivery_next.state_store.profile_share import ABSENT, PROFILE, ROLES_MOVED, config_digest

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Role
    from owlbear_delivery_next.change_contracts.profile_record import RoleModel
    from owlbear_delivery_next.state_store.store import RoleSourceError, Store


def move_roles(store: Store) -> None:
    """Merge a format-1 profile's role overrides into the project settings, once.

    Fields the settings already set win; the old values fill only the empty ones. The move's receipt is written
    with the roles, so a later owner clear is never refilled from the old profile, even if the marker is lost. An
    old profile this build cannot inspect raises ``StoreError`` and stays unmoved; a damaged settings file is left
    to ``read_config`` to report. A refused settings write raises too, so the store never opens as if it had moved.
    """
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports this module

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
        text = "the format-1 profile's role overrides are merged into config.json\n"
        try:
            applied = read_layer(store.config_path, Layer).roles_moved
        except StoreError:
            return  # a damaged settings file: read_config reports it
        if applied:  # applied with its config write; the marker caches it
            atomic_write(marker, text)
            return
        found = _old_roles(old)  # an uninspectable old profile raises: the move stays retryable and visible
        if not found:
            atomic_write(marker, text)
            return
        from owlbear_delivery_next.state_store.config_save import Prepared  # noqa: PLC0415 (import cycle)

        def change(cur: Layer) -> Layer:
            if cur.roles_moved:  # another clone's move or clear landed after this read: never refill it
                return cur
            return migrations.with_roles(cur, found).model_copy(update={"roles_moved": True})

        # The receipt and the roles are one config write; the marker only caches the receipt, so its failure
        # after that write leaves the move applied. A write or refusal failure raises here, never a silent return.
        notice = store.update_config(
            Prepared(config_digest(store.config_path), change),
            "role overrides from the old profile",
            on_written=lambda: atomic_write(marker, text),
        )
        if notice and not marker.exists():  # a refused write is not success-shaped: the caller must see it
            msg = f"the old profile's role overrides were not moved: {notice}"
            raise StoreError(msg)
    finally:
        os.close(fd)


def _old_roles(old: Path) -> dict[Role, RoleModel]:
    """The format-1 profile's role overrides. A validated profile of a later format has none left to move.

    Anything else, an unknown, future, malformed or unreadable profile, raises ``StoreError`` before any marker,
    receipt or config write: the move stays retryable and the store cannot open with its roles silently lost.
    """
    try:
        data = old.read_bytes()
    except OSError as exc:
        raise _unreadable(old, exc) from exc
    return roles_of(data, old)


def roles_of(data: bytes, old: Path) -> dict[Role, RoleModel]:
    """The role overrides of the old profile's *data*, judged as the move judges them (see ``_old_roles``)."""
    from owlbear_delivery_next.state_store.store import (  # noqa: PLC0415 - the store imports this module
        RoleSourceError,
        StoreError,
        _parse,
    )

    try:
        raw = data.decode()
        content = json.loads(raw)
        version = _format_of(content)
    except (TypeError, ValueError) as exc:  # a UnicodeDecodeError is a ValueError too
        raise _unreadable(old, exc) from exc
    roles: dict[Role, RoleModel] = {}
    if version == 1:
        try:
            roles = migrations.ROLES.validate_python(content.get("roles", {}))
        except ValueError as exc:  # pydantic's ValidationError is a ValueError
            msg = f"the old profile's role overrides are invalid: {exc}; repair {old}, then reopen"
            raise RoleSourceError(msg) from exc
    try:
        _parse(raw, PROFILE, Profile, PROFILE_FORMAT, migrations.PROFILE)  # the whole profile must be this build's
    except StoreError as exc:
        raise RoleSourceError(str(exc)) from exc
    return roles


def snapshot(old: Path) -> tuple[str, RoleSourceError | None]:
    """The digest of the old profile's bytes now, and why its role overrides cannot be read from those same bytes.

    ``ABSENT`` with no reason when the file is gone; the caller judges any other ``None`` reason as readable.
    """
    from owlbear_delivery_next.state_store.store import RoleSourceError  # noqa: PLC0415 - the store imports this module

    try:
        data = old.read_bytes()
    except FileNotFoundError:
        return ABSENT, None
    except OSError as exc:
        return "", _unreadable(old, exc)
    try:
        roles_of(data, old)
    except RoleSourceError as exc:
        return hashlib.sha256(data).hexdigest(), exc
    return hashlib.sha256(data).hexdigest(), None


def _unreadable(old: Path, exc: Exception) -> RoleSourceError:
    from owlbear_delivery_next.state_store.store import RoleSourceError  # noqa: PLC0415 - the store imports this module

    msg = f"the old profile could not be read to move its role overrides: {exc}; repair or replace {old}, then reopen"
    return RoleSourceError(msg)


def retire_source(store: Store) -> None:
    """Mark an uninspectable old profile as handled once an owner's confirmed replacement is published.

    Its role overrides were discarded by that confirmation, so later opens do not inspect it again. The file stays.
    """
    text = "the old profile was replaced by a confirmed profile; its roles were not moved\n"
    atomic_write(store.root / ROLES_MOVED, text)


def _format_of(data: object) -> int:
    """The profile's format: a whole number as an int or a digit string; a bool, float or other type is refused."""
    if not isinstance(data, dict):
        msg = "not a profile object"
        raise TypeError(msg)
    fmt = data.get("format", 0)
    if isinstance(fmt, bool) or not isinstance(fmt, int | str):
        msg = f"format {fmt!r} is not a whole number"
        raise TypeError(msg)
    return int(fmt)  # a string such as "1.5" raises ValueError here
