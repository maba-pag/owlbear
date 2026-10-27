"""Refusing a switched store unless its target still names the folder the switch recorded, by identity and proof."""

from __future__ import annotations

import os
import stat
from typing import TYPE_CHECKING

from owlbear_delivery_next.state_store import fd_tree, format_marker, project_move
from owlbear_delivery_next.state_store.database import STORE_FORMAT, FormatTooNewError, StoreError
from owlbear_delivery_next.state_store.offline_proof import preparation, same_folder

if TYPE_CHECKING:
    from pathlib import Path


def prepared_prior(folder_fd: int) -> int:
    """The prior format the source's preparation recorded: 0 only when it recorded an absent marker.

    A missing or malformed preparation proves no prior format, so nothing is admitted on it.

    Raises:
        StoreError: The preparation is missing, unreadable, malformed, or names an unsupported prior format.
    """
    try:
        text = fd_tree.read_at(folder_fd, project_move.PREPARED)
    except (OSError, ValueError) as exc:
        msg = f"{project_move.PREPARED} is unreadable: refusing the switched store; nothing was changed"
        raise StoreError(msg) from exc
    if text is None:
        msg = f"{project_move.PREPARED} is missing: the switched store's prior format is unproven; nothing was changed"
        raise StoreError(msg)
    return format_marker.prior_format(preparation(text, folder_fd)["marker"])


def named_switched(target: Path, rec: dict) -> None:
    """Refuse unless *target* still names the folder the switch recorded, read without creating anything.

    Raises:
        StoreError: The receipt names another store, or the target is missing, is not a folder, or is another folder.
    """
    try:
        st = os.lstat(target)
    except OSError:
        st = None
    if rec["stage_id"] is None or st is None or not stat.S_ISDIR(st.st_mode) or fd_tree.ident(st) != rec["stage_id"]:
        raise project_move._not_published(target)  # noqa: SLF001 - the one refusal every publication path shares


def _refuse_unless_held(target: Path, tfd: int, rec: dict) -> None:
    if (
        fd_tree.ident(os.fstat(tfd)) != rec["stage_id"]
        or not same_folder(target, tfd)
        or not project_move._proof_ok(tfd, rec)  # noqa: SLF001 - the proof this move wrote
    ):
        raise project_move._not_published(target)  # noqa: SLF001 - a freed folder can return with the same identity


def clone_id_at(folder: Path, folder_fd: int) -> str | None:
    """Read the held source's complete clone id; absence alone is None."""
    try:
        text = fd_tree.read_at(folder_fd, project_move.CLONE_ID)
    except (OSError, UnicodeError) as exc:
        msg = f"{folder / project_move.CLONE_ID} is unreadable: {exc}; nothing was changed"
        raise StoreError(msg) from exc
    if text and not text.endswith("\n"):
        msg = f"{folder / project_move.CLONE_ID} is incomplete: its write was cut short; nothing was changed"
        raise StoreError(msg)
    return (text or "").strip() or None


def source_format(folder_fd: int) -> str:
    """Validate a retained ASCII-integer marker, allowing repair of supported older formats."""
    try:
        text = fd_tree.read_at(folder_fd, format_marker.MARKER)
    except (OSError, UnicodeError) as exc:
        msg = "the switched source's format marker is unreadable: nothing was changed"
        raise StoreError(msg) from exc
    value = text.strip() if text is not None else ""
    if text is None or not (value.isascii() and value.isdigit()):
        msg = "the switched source has no readable format marker: nothing was changed"
        raise StoreError(msg)
    try:
        found = int(value)
    except ValueError as exc:
        msg = "the switched source's format marker is not a readable integer: nothing was changed"
        raise StoreError(msg) from exc
    if found == int(project_move.FENCE) or 1 <= found <= STORE_FORMAT:
        return text
    if found > STORE_FORMAT:
        msg = f"switched source format {found} is newer than {STORE_FORMAT}: nothing was changed"
        raise FormatTooNewError(msg)
    msg = f"switched source format {found} is not a known format: nothing was changed"
    raise StoreError(msg)


def source_state(source: tuple[Path, int], pid: str, rec: dict) -> tuple[str, str, str]:
    """The preparation, marker and admitted receipt in the held, still-named source belonging to *pid*."""
    folder, folder_fd = source
    names = (project_move.PREPARED, format_marker.MARKER, project_move.CLONE_ID, project_move.MOVE_RECORD)
    try:
        images = {name: fd_tree.stat_at(folder_fd, name) for name in names}
    except OSError as exc:
        msg = f"{folder}'s source witnesses cannot be checked: nothing was changed"
        raise StoreError(msg) from exc
    observed, image = project_move.record_image(folder, folder_fd)
    if observed != rec or image is None:
        msg = f"{folder}'s move receipt changed during admission: nothing was changed"
        raise StoreError(msg)
    try:
        prepared = fd_tree.read_at(folder_fd, project_move.PREPARED)
    except (OSError, UnicodeError) as exc:
        msg = f"{folder}'s preparation is unreadable: nothing was changed"
        raise StoreError(msg) from exc
    if prepared is None:
        msg = f"{folder}'s preparation is missing: nothing was changed"
        raise StoreError(msg)
    preparation(prepared, folder_fd)
    marker = source_format(folder_fd)
    if clone_id_at(folder, folder_fd) != pid or not same_folder(folder, folder_fd):
        msg = f"{folder} no longer names the retained source of project {pid}: nothing was changed"
        raise StoreError(msg)
    fd_tree.require_text_at(folder_fd, project_move.MOVE_RECORD, image)
    try:
        stable = all(fd_tree.same_image_at(folder_fd, name, before) for name, before in images.items())
    except OSError as exc:
        msg = f"{folder}'s source witnesses cannot be checked: nothing was changed"
        raise StoreError(msg) from exc
    if not stable:
        source_format(folder_fd)  # a concurrently installed newer marker keeps its typed refusal
        msg = f"{folder}'s source witnesses changed during admission: nothing was changed"
        raise StoreError(msg)
    return prepared, marker, image


def held_switched(target: Path, tfd: int, rec: dict) -> None:
    """Revalidate the held target's identity, proof, quarantine state and marker, without reopening it."""
    _refuse_unless_held(target, tfd, rec)
    fd_tree.refuse_quarantined(tfd, target)
    try:
        text = fd_tree.read_at(tfd, format_marker.MARKER)
    except (OSError, UnicodeError) as exc:
        msg = f"{target} holds a format marker OwlBear cannot read: nothing was changed"
        raise StoreError(msg) from exc
    if text is not None:
        format_marker.supported_format(text)
    named_switched(target, rec)


def require_admission(
    source: tuple[Path, int], target: tuple[Path, int], rec: dict, expected: tuple[str, str, str]
) -> None:
    """Revalidate source witnesses and target authority after admission's durability work."""
    path, tfd = target
    held_switched(path, tfd, rec)
    if source_state(source, path.name, rec) != expected:
        msg = f"{source[0]} changed its preparation, format or receipt during admission: nothing was changed"
        raise StoreError(msg)
    named_switched(path, rec)


def check_switched(target: Path, pfd: int, rec: dict) -> int:
    """Refuse unless *target* is still the copy the switch recorded, by identity and proof; return its descriptor.

    Raises:
        StoreError: The target is missing, replaced, quarantined, unproven, or holds an unsupported format marker.
    """
    named_switched(target, rec)
    tfd = fd_tree.open_dir(pfd, target.name)
    try:
        held_switched(target, tfd, rec)
    except BaseException:
        os.close(tfd)
        raise
    return tfd


def require_switched(target: Path, rec: dict) -> None:
    """Prove a switched target read-only and close the descriptors acquired for that lookup.

    Raises:
        StoreError: The target cannot be read or does not pass the held identity, proof and marker checks.
    """
    try:
        pfd = os.open(target.parent, fd_tree.DIR_FLAGS)
        try:
            os.close(check_switched(target, pfd, rec))
        finally:
            os.close(pfd)
    except OSError as exc:
        msg = f"{target} is not a store OwlBear can read: nothing was changed"
        raise StoreError(msg) from exc
