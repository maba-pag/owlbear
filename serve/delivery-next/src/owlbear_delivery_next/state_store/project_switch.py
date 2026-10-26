"""Refusing a switched store unless its target still names the folder the switch recorded, by identity and proof."""

from __future__ import annotations

import os
import stat
from typing import TYPE_CHECKING

from owlbear_delivery_next.state_store import fd_tree, project_move
from owlbear_delivery_next.state_store.offline_proof import same_folder

if TYPE_CHECKING:
    from pathlib import Path


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
    """Refuse unless *target* is still the copy the switch recorded, by identity; return its validated descriptor.

    Raises:
        StoreError: The target is missing or is another folder, or it holds a quarantined entry.
    """
    named_switched(target, rec)
    tfd = fd_tree.open_dir(pfd, target.name)
    try:
        _refuse_unless_held(target, tfd, rec)
        fd_tree.refuse_quarantined(tfd, target)
    except BaseException:
        os.close(tfd)
        raise
    return tfd
