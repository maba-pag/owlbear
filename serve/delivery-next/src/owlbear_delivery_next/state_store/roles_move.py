"""Merge a format-1 profile's role overrides into the project settings, once (R15)."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

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
    unreadable or invalid profile or settings file is left to ``read_profile`` and ``read_config`` to report.
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
            found = _old_roles(old)
        except StoreError:
            return  # read_config reports the damaged settings
        if not found:
            atomic_write(marker, text)
            return
        try:
            from owlbear_delivery_next.state_store.config_save import Prepared  # noqa: PLC0415 (import cycle)

            # The receipt and the roles are one config write; the marker only caches the receipt, so its failure
            # after that write leaves the move applied. A refusal never reaches the write.
            store.update_config(
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
    finally:
        os.close(fd)


def _old_roles(old: Path) -> dict[Role, RoleModel]:
    """The format-1 profile's role overrides; a non-format-1 profile has none, and a damaged one is an error.

    A format-1 profile that cannot be read or whose roles are invalid raises ``StoreError``: the move stays
    retryable and is never marked done with its roles lost.
    """
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports this module

    try:
        data = json.loads(old.read_text())
        if not isinstance(data, dict) or int(data.get("format", 0)) != 1:
            return {}
    except (OSError, TypeError, ValueError) as exc:
        msg = f"the old profile could not be read to move its role overrides: {exc}"
        raise StoreError(msg) from exc
    try:
        return migrations.ROLES.validate_python(data.get("roles", {}))
    except ValueError as exc:  # pydantic's ValidationError is a ValueError
        msg = f"the old profile's role overrides are invalid: {exc}"
        raise StoreError(msg) from exc
