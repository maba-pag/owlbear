"""Reading and writing versioned state files: the settings layers and the Change record."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from pydantic import ValidationError

from owlbear_delivery_next.change_contracts.models import Record
from owlbear_delivery_next.local_system.storage_io import atomic_write, open_lock
from owlbear_delivery_next.settings import migrations
from owlbear_delivery_next.settings.config import CONFIG_FORMAT, Layer
from owlbear_delivery_next.state_store.database import FormatTooNewError, StoreError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.settings.migrations import Migrations

_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _parse[T: Record](raw: str, name: str, model: type[T], current: int, forward: Migrations) -> T:
    try:
        data = json.loads(raw)
        version = int(data.get("format", 0))
    except (AttributeError, TypeError, ValueError) as exc:
        msg = f"state of {name} is unreadable"
        raise StoreError(msg) from exc
    if version > current:
        msg = f"{name} has format {version}, newer than {current}"
        raise FormatTooNewError(msg)
    written = version
    try:
        while version < current:
            data = forward[version](data)
            version += 1
            data["format"] = version
        return model.model_validate(data)
    except ValidationError as exc:
        if written < current:
            msg = f"state of {name} cannot be migrated to format {current}"
        else:  # the current format with fields this Delivery does not know: a newer or different one wrote it
            msg = f"state of {name} was written by a newer or different Delivery ({_first(exc)})"
        raise StoreError(msg) from exc
    except (KeyError, TypeError, ValueError) as exc:
        msg = f"state of {name} cannot be migrated to format {current}"
        raise StoreError(msg) from exc


def _first(exc: ValidationError) -> str:
    error = exc.errors()[0]
    said = {"extra_forbidden": "unknown field", "missing": "missing field"}.get(error["type"], "invalid field")
    return f"{said} {'.'.join(map(str, error['loc']))}"


def read_layer[T: Layer](path: Path, model: type[T]) -> T:
    """One settings layer under its format gate; an empty layer before the first save."""
    return read_layer_bytes(path, model)[0]


def read_layer_bytes[T: Layer](path: Path, model: type[T]) -> tuple[T, bytes]:
    """One settings layer and the exact bytes it was parsed from; an absent file is the empty layer."""
    try:
        raw = path.read_bytes()
        text = raw.decode()
    except FileNotFoundError:
        return model(), b""
    except (OSError, ValueError) as exc:  # ValueError: bytes that are not UTF-8
        msg = f"state of {path.stem} is unreadable"
        raise StoreError(msg) from exc
    return _parse(text, path.stem, model, CONFIG_FORMAT, migrations.CONFIG), raw


def update_layer[T: Layer](
    path: Path, model: type[T], change: Callable[[T], T], on_written: Callable[[], None] | None = None
) -> T:
    """Read, change and write one layer under its own lock, so no concurrent save is lost; invalid writes nothing.

    *on_written* runs under the same lock right after the write, so nothing can land between the two.
    """
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    dir_fd = os.open(path.parent, _DIR_FLAGS)
    try:
        fd = open_lock(dir_fd, blocking=True, name=f".{path.name}.lock")
    finally:
        os.close(dir_fd)
    try:
        current = read_layer(path, model)
        new = model.model_validate(change(current).model_dump())
        if current.roles_moved and not new.roles_moved:  # the receipt is never lost to a later write
            new = new.model_copy(update={"roles_moved": True})
        atomic_write(path, new.model_dump_json(indent=1))
        if on_written:
            on_written()
        return new
    finally:
        os.close(fd)
