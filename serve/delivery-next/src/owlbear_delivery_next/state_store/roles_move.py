"""Merge a format-1 profile's role overrides into the project settings, once (R15)."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.profile_record import PROFILE_FORMAT, Profile
from owlbear_delivery_next.local_system.storage_io import atomic_write, open_lock
from owlbear_delivery_next.settings import migrations
from owlbear_delivery_next.settings.config import Layer
from owlbear_delivery_next.state_store.layers import read_layer
from owlbear_delivery_next.state_store.profile_share import PROFILE, ROLES_MOVED, config_digest

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Role
    from owlbear_delivery_next.change_contracts.profile_record import RoleModel
    from owlbear_delivery_next.state_store.store import Store


def move_roles(store: Store) -> None:
    """Merge a format-1 profile's role overrides into the project settings, once.

    Fields the settings already set win; the old values fill only the empty ones. The move's receipt is written
    with the roles, so a later owner clear is never refilled from the old profile, even if the marker is lost. An
    old profile this build cannot inspect raises ``StoreError`` and stays unmoved; a damaged settings file is left
    to ``read_config`` to report. A refused settings write raises too, so the store never opens as if it had moved.
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
        text = "the format-1 profile's role overrides are merged into config.json\n"
        try:
            if read_layer(store.config_path, Layer).roles_moved:  # applied with its config write; the marker caches it
                atomic_write(marker, text)
                return
        except StoreError:
            return  # read_config reports the damaged settings
        found = _old_roles(old)  # an uninspectable old profile raises: the move stays retryable and visible
        if not found:
            atomic_write(marker, text)
            return
        try:
            from owlbear_delivery_next.state_store.config_save import Prepared  # noqa: PLC0415 (import cycle)

            # The receipt and the roles are one config write; the marker only caches the receipt, so its failure
            # after that write leaves the move applied. A refusal never reaches the write.
            notice = store.update_config(
                Prepared(
                    config_digest(store.config_path),
                    lambda cur: migrations.with_roles(cur, found).model_copy(update={"roles_moved": True}),
                ),
                "role overrides from the old profile",
                on_written=lambda: atomic_write(marker, text),
            )
        except SharedError:
            raise  # the old roles move later; never mark a move that did not happen
        except StoreError:
            return  # refused before writing; read_config reports the damaged settings
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
    from owlbear_delivery_next.state_store.store import (  # noqa: PLC0415 - the store imports this module
        StoreError,
        _parse,
    )

    try:
        raw = old.read_text()
        data = json.loads(raw)
        version = int(data.get("format", 0))
    except (AttributeError, OSError, TypeError, ValueError) as exc:
        msg = (
            f"the old profile could not be read to move its role overrides: {exc}; repair or replace {old}, then reopen"
        )
        raise StoreError(msg) from exc
    if version != 1:
        _parse(raw, PROFILE, Profile, PROFILE_FORMAT, migrations.PROFILE)  # validates or raises StoreError
        return {}
    try:
        return migrations.ROLES.validate_python(data.get("roles", {}))
    except ValueError as exc:  # pydantic's ValidationError is a ValueError
        msg = f"the old profile's role overrides are invalid: {exc}; repair {old}, then reopen"
        raise StoreError(msg) from exc
