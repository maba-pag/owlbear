"""Refusing a switched store unless its target still names the folder the switch recorded, by identity and proof."""

from __future__ import annotations

import os
import stat
from typing import TYPE_CHECKING

from owlbear_delivery_next.state_store import fd_tree, format_marker, project_move
from owlbear_delivery_next.state_store.database import StoreError
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


def check_switched(target: Path, pfd: int, rec: dict) -> int:
    """Refuse unless *target* is still the copy the switch recorded, by identity and proof; return its descriptor.

    Raises:
        StoreError: The target is missing, replaced, quarantined, unproven, or holds an unsupported format marker.
    """
    named_switched(target, rec)
    tfd = fd_tree.open_dir(pfd, target.name)
    try:
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
