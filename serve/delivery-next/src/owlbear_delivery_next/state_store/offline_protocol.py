"""Prepare, reboot, finish: the gates a cross-volume store move must pass before any state changes.

Prepare records the source folder's identity and the boot session it was prepared in, and installs the
future-format fence every older runtime already refuses. Finish refuses unless a different boot session is
readable, the record and the fence still match the folder, and every legacy producer is proven fenced.
"""

import json
import os
import subprocess
import sys
from typing import TYPE_CHECKING

from owlbear_delivery_next.state_store import fd_tree, format_marker, project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER, StoreError
from owlbear_delivery_next.state_store.legacy_family import Gap, open_gaps
from owlbear_delivery_next.state_store.offline_proof import UUID, OfflineProof, preparation, same_folder

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

PREPARED = project_move.PREPARED
FENCE = project_move.FENCE
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


def _record(folder: Path, fd: int) -> tuple[dict, str]:
    """The preparation record and the exact text it was read as; finish keeps the text as its proof."""
    text = _read(fd, folder, PREPARED)
    if text is None:
        msg = f"{folder / PREPARED} is missing: nothing was prepared, so nothing moves"
        raise StoreError(msg)
    return preparation(text, fd), text


def _refuse_replaced(folder: Path, fd: int) -> None:
    if not same_folder(folder, fd):
        msg = f"{folder} no longer names the folder that was pinned: nothing was prepared; check it, then start again"
        raise StoreError(msg)


def _prepare_at(folder: Path, fd: int, boot: str) -> dict:
    raw = _refuse_unsupported_marker(folder, fd)
    fenced = raw is not None and raw.strip() == FENCE
    if fenced:
        # Repeated prepare keeps the existing generation; the fence is never recorded as the prior format.
        record, prepared = _record(folder, fd)
    else:
        identity = fd_tree.ident(os.fstat(fd))
        prior = "" if raw is None else raw
        prepared = _refuse_foreign_preparation(folder, fd, prior, identity)
        record = {"boot": boot, "folder": identity, "marker": prior}

    def unchanged(expected: str | None) -> None:
        _refuse_replaced(folder, fd)
        observed = _refuse_unsupported_marker(folder, fd)
        if observed != raw or _read(fd, folder, PREPARED) != expected:
            msg = f"{folder} changed while preparing: refusing to replace its marker or preparation; both are kept"
            raise StoreError(msg)

    project_home.ensure_pinned(folder, fd)
    unchanged(prepared)
    if not fenced:
        text = json.dumps(record) + "\n"
        fd_tree.write_at(fd, PREPARED, text, before_replace=lambda: unchanged(prepared))
        fd_tree.write_at(fd, MARKER, f"{FENCE}\n", before_replace=lambda: unchanged(text))
    return record


def _refuse_unsupported_marker(folder: Path, fd: int) -> str | None:
    """Refuse before any write when a present marker is neither the fence nor a supported prior format.

    An absent marker (None) is the markerless prior 0; a present blank marker is refused, not treated as absent.
    """
    raw = _read(fd, folder, MARKER)
    if raw is None or raw.strip() == FENCE:
        return raw
    try:
        format_marker.supported_format(raw)
    except StoreError as exc:
        msg = f"{folder / MARKER}: {exc}"
        raise StoreError(msg) from exc
    return raw


def _refuse_unsupported_prior(folder: Path, record: dict) -> None:
    """Refuse a preparation whose recorded prior format is not one this runtime moves; nothing is written."""
    if not isinstance(record["marker"], str):
        msg = f"{folder / PREPARED} names no prior format: refusing the offline move"
        raise StoreError(msg)
    try:
        format_marker.prior_format(record["marker"])
    except StoreError as exc:
        msg = f"{folder / PREPARED}: {exc}"
        raise StoreError(msg) from exc


def _refuse_foreign_preparation(folder: Path, fd: int, raw: str, identity: list[int]) -> str | None:
    """Refuse to overwrite a preparation record that this folder's own interrupted prepare did not write."""
    text = _read(fd, folder, PREPARED)
    if text is None:
        return None
    data = preparation(text, fd)
    if data["folder"] != identity or data["marker"] != raw:
        msg = f"{folder / PREPARED} is not this folder's own preparation: refusing; nothing was written"
        raise StoreError(msg)
    return text


def _refuse_nothing_to_move(folder: Path, fd: int) -> None:
    """Read the receipt first: retained payload never makes a completed or malformed move preparable."""
    rec = project_move.record_at(folder, fd)
    if rec is not None and rec["phase"] == project_move.SWITCHED:
        msg = f"{folder} has already switched to its external store: nothing was prepared or fenced"
        raise StoreError(msg)
    if rec is not None or project_move.left_at(fd):
        return
    msg = (
        f"{folder} holds no legacy store to move and no move record: the store is already external or new, "
        "so no offline move applies; nothing was prepared or fenced"
    )
    raise StoreError(msg)


def prepare(folder: Path, gaps: Callable[[], tuple[Gap, ...]] = open_gaps) -> dict:
    """Record the folder's identity and boot session and install the fence; refuse first if a producer is unfenced.

    The folder is pinned once, before anything is read. The clone id and the preparation are both made through that
    descriptor, so a path swapped after the pin cannot receive a write. The source identity, marker and preparation
    are rechecked after the id sync and each temporary-file sync, before either preparation or fence is published.
    """
    boot = boot_session()
    fd = _pinned(folder)
    try:
        open_gaps = gaps()
        if open_gaps:
            msg = _unfenced(open_gaps)
            raise StoreError(msg)
        _refuse_replaced(folder, fd)
        _refuse_nothing_to_move(folder, fd)
        return _prepare_at(folder, fd, boot)
    finally:
        os.close(fd)


def finish(folder: Path, gaps: Callable[[], tuple[Gap, ...]] = open_gaps) -> OfflineProof:
    """Verify every precondition; return the only proof the migrator accepts, or raise before any state changes.

    The proof carries the identity of the folder verified through this descriptor and the exact preparation text, so
    the move can refuse a swap or a folder that was not prepared as it was verified.
    """
    fd = _pinned(folder)
    try:
        record, prepared = _record(folder, fd)
        _refuse_unsupported_prior(folder, record)
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
        return OfflineProof(folder, str(record["marker"]), (dev, ino), prepared)
    finally:
        os.close(fd)


def prepare_clone(cwd: Path, gaps: Callable[[], tuple[Gap, ...]] = open_gaps) -> dict:
    """Prepare the clone's own store folder for the offline move; the only entry that installs the fence."""
    folder = project_home.clone_dir(cwd)
    folder.mkdir(mode=0o700, exist_ok=True)
    return prepare(folder, gaps)


def finish_clone(cwd: Path, gaps: Callable[[], tuple[Gap, ...]] = open_gaps) -> Path:
    """Finish after reboot: prove the preparation, then run the whole-store move; return the project's home."""
    folder = project_home.clone_dir(cwd)
    proof = finish(folder, gaps)
    return project_home.migrated(cwd, proof)


def _settle_pack_run(folder: Path) -> None:
    """Standalone compatibility entry; real moves settle inside their pinned proof-checked boundary."""
    fd = _pinned(folder)
    try:
        project_home._settle_pack_run(folder, fd, None)  # noqa: SLF001 - shared settlement owner
    finally:
        os.close(fd)


def _unfenced(found: tuple[Gap, ...]) -> str:
    detail = "; ".join(f"{g.path} ({g.version}): {g.reason}" for g in found)
    return f"legacy producers are not proven fenced, so the offline move is refused, nothing was changed: {detail}"
