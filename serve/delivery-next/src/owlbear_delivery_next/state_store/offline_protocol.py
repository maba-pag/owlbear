"""Prepare, reboot, finish: the gates a cross-volume store move must pass before any state changes.

Prepare records the source folder's identity and the boot session it was prepared in, and installs the
future-format fence every older runtime already refuses. Finish refuses unless a different boot session is
readable, the record and the fence still match the folder, and every legacy producer is proven fenced.
"""

import json
import os
import re
import subprocess
import sys
from typing import TYPE_CHECKING

from owlbear_delivery_next.state_store import fd_tree, project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER, StoreError
from owlbear_delivery_next.state_store.legacy_family import Gap, open_gaps
from owlbear_delivery_next.state_store.offline_proof import OfflineProof, same_folder

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

PREPARED = project_move.PREPARED
FENCE = project_move.FENCE
UUID = re.compile(r"[0-9A-F]{8}(?:-[0-9A-F]{4}){3}-[0-9A-F]{12}")
SYSCTL = "/usr/sbin/sysctl"


def boot_session() -> str:
    """Return the kernel boot-session UUID; refuse when the facility is missing, unreadable or malformed."""
    if sys.platform != "darwin":
        msg = "no boot-session facility on this platform: refusing the offline move"
        raise StoreError(msg)
    try:
        done = subprocess.run(  # noqa: S603 - fixed argv, no shell, no input
            [SYSCTL, "-n", "kern.bootsessionuuid"], capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        msg = f"boot-session UUID is unreadable ({exc}): refusing the offline move"
        raise StoreError(msg) from exc
    text = done.stdout.strip()
    if done.returncode != 0 or not UUID.fullmatch(text):
        msg = "boot-session UUID is missing or malformed: refusing the offline move"
        raise StoreError(msg)
    return text


def _pinned(folder: Path) -> int:
    fd = project_move.pin(folder)
    if fd is None:
        msg = f"{folder} is missing: nothing was prepared, so nothing moves"
        raise StoreError(msg)
    return fd


def _read(fd: int, folder: Path, name: str) -> str | None:
    try:
        return fd_tree.read_at(fd, name)
    except (OSError, ValueError) as exc:
        msg = f"{folder / name} is not a regular file OwlBear can read: refusing the offline move"
        raise StoreError(msg) from exc


def _record(folder: Path, fd: int) -> dict:
    text = _read(fd, folder, PREPARED)
    if text is None:
        msg = f"{folder / PREPARED} is missing: nothing was prepared, so nothing moves"
        raise StoreError(msg)
    try:
        data = json.loads(text)
    except ValueError as exc:
        msg = f"{folder / PREPARED} is unreadable: refusing the offline move"
        raise StoreError(msg) from exc
    if not isinstance(data, dict) or set(data) != {"boot", "folder", "marker"} or not _witnessed(data):
        msg = f"{folder / PREPARED} is not a preparation record OwlBear wrote: refusing the offline move"
        raise StoreError(msg)
    return data


def _witnessed(data: dict) -> bool:
    """A stored boot is a UUID and the folder identity two integers; anything else is unknown, never a new boot."""
    folder = data["folder"]
    return (
        isinstance(data["boot"], str)
        and UUID.fullmatch(data["boot"].upper()) is not None
        and isinstance(folder, list)
        and len(folder) == 2  # noqa: PLR2004 - a (device, inode) pair
        and all(type(part) is int for part in folder)
        and isinstance(data["marker"], str)
    )


def _refuse_replaced(folder: Path, fd: int) -> None:
    if not same_folder(folder, fd):
        msg = f"{folder} no longer names the folder that was pinned: nothing was prepared; check it, then start again"
        raise StoreError(msg)


def _prepare_at(folder: Path, fd: int, boot: str) -> dict:
    raw = _read(fd, folder, MARKER) or ""
    current = raw.strip()
    if current == FENCE:
        # Repeated prepare keeps the existing generation; the fence is never recorded as the prior format.
        return _record(folder, fd)
    if current and not current.isdigit():
        msg = f"the format marker {current!r} is malformed: refusing the offline move"
        raise StoreError(msg)
    if current and int(current) >= int(FENCE):
        msg = f"the format marker {current} is not a prior format: refusing the offline move"
        raise StoreError(msg)
    dev, ino = fd_tree.ident(os.fstat(fd))
    record = {"boot": boot, "folder": [dev, ino], "marker": raw}
    fd_tree.write_at(fd, PREPARED, json.dumps(record) + "\n")
    fd_tree.write_at(fd, MARKER, f"{FENCE}\n")
    return record


def prepare(folder: Path, gaps: Callable[[], tuple[Gap, ...]] = open_gaps) -> dict:
    """Record the folder's identity and boot session and install the fence; refuse first if a producer is unfenced.

    The folder is pinned before anything is read; every read and write goes through that descriptor.
    """
    boot = boot_session()
    fd = _pinned(folder)
    try:
        open_gaps = gaps()
        if open_gaps:
            msg = _unfenced(open_gaps)
            raise StoreError(msg)
        _refuse_replaced(folder, fd)
        return _prepare_at(folder, fd, boot)
    finally:
        os.close(fd)


def finish(folder: Path, gaps: Callable[[], tuple[Gap, ...]] = open_gaps) -> OfflineProof:
    """Verify every precondition; return the only proof the migrator accepts, or raise before any state changes.

    The proof carries the identity of the folder verified through this descriptor, so the move can refuse a swap.
    """
    fd = _pinned(folder)
    try:
        record = _record(folder, fd)
        boot = boot_session()
        if boot.upper() == record["boot"].upper():  # UUID case variants name the same boot session
            msg = "still the boot session the source was prepared in: reboot before finishing; nothing moves"
            raise StoreError(msg)
        dev, ino = fd_tree.ident(os.fstat(fd))
        if record["folder"] != [dev, ino] or not same_folder(folder, fd):
            msg = f"{folder} is not the folder that was prepared: refusing the offline move"
            raise StoreError(msg)
        marker = _read(fd, folder, MARKER)
        if marker is None or marker.strip() != FENCE:
            msg = f"the format fence on {folder} is missing or altered: refusing the offline move"
            raise StoreError(msg)
        open_gaps = gaps()
        if open_gaps:
            raise StoreError(_unfenced(open_gaps))
        return OfflineProof(folder, str(record["marker"]), (dev, ino))
    finally:
        os.close(fd)


def prepare_clone(cwd: Path, gaps: Callable[[], tuple[Gap, ...]] = open_gaps) -> dict:
    """Prepare the clone's own store folder for the offline move; the only entry that installs the fence."""
    folder = project_home.clone_dir(cwd)
    return prepare(folder, gaps)


def finish_clone(cwd: Path, gaps: Callable[[], tuple[Gap, ...]] = open_gaps) -> Path:
    """Finish after reboot: prove the preparation, then run the whole-store move; return the project's home."""
    folder = project_home.clone_dir(cwd)
    proof = finish(folder, gaps)
    return project_home.migrated(cwd, proof)


def _unfenced(found: tuple[Gap, ...]) -> str:
    detail = "; ".join(f"{g.path} ({g.version}): {g.reason}" for g in found)
    return f"legacy producers are not proven fenced, so the offline move is refused, nothing was changed: {detail}"
