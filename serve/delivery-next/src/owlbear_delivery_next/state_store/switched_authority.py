"""The read-only authority a completed offline move leaves in its retained source.

Registration and self-check read a fenced source through this check only. It writes nothing, creates nothing and
opens no store, and it accepts the project's store only when the source's own SWITCHED receipt names that store and
the store still holds that receipt's identity, proof and format.
"""

import os
from typing import TYPE_CHECKING

from owlbear_delivery_next.state_store import fd_tree, format_marker, project_home, project_move, project_switch
from owlbear_delivery_next.state_store.database import MARKER, StoreError
from owlbear_delivery_next.state_store.offline_proof import same_folder

if TYPE_CHECKING:
    from pathlib import Path


def retained_target(folder: Path, pid: str) -> Path | None:
    """The project's store that the SWITCHED receipt in the retained source *folder* names, or None without a receipt.

    Raises:
        StoreError: The receipt is not SWITCHED to the project's store, or that store is missing, replaced,
            quarantined, unproven or not a supported store format.
    """
    target = project_home.home(pid)
    try:
        fd = os.open(folder, fd_tree.DIR_FLAGS)
    except OSError as exc:
        msg = f"{folder} holds a link or is not a folder: nothing was checked"
        raise StoreError(msg) from exc
    try:
        rec = project_move.record_at(folder, fd)
    finally:
        os.close(fd)
    if rec is None:
        return None
    if rec["phase"] != project_move.SWITCHED or rec["target"] != str(target):
        msg = f"{folder} was not switched to {target}: its receipt names another store; nothing was changed"
        raise StoreError(msg)
    project_switch.named_switched(target, rec)
    _proven(target, rec)
    return target


def _proven(target: Path, rec: dict) -> None:
    """Refuse unless *target* is the folder the receipt recorded, holding its proof and format, nothing quarantined."""
    try:
        tfd = os.open(target, fd_tree.DIR_FLAGS)
    except OSError as exc:
        msg = f"{target} is not a folder OwlBear can read: nothing was changed"
        raise StoreError(msg) from exc
    try:
        if fd_tree.ident(os.fstat(tfd)) != rec["stage_id"] or not same_folder(target, tfd):
            msg = f"{target} is not the store the move switched to: nothing was changed"
            raise StoreError(msg)
        if rec["proof"] is None or fd_tree.read_at(tfd, project_move.MOVE_PROOF) != f"{rec['proof']}\n":
            msg = f"{target} lost the proof its move recorded: nothing was changed"
            raise StoreError(msg)
        fd_tree.refuse_quarantined(tfd, target)
        text = fd_tree.read_at(tfd, MARKER)  # an absent marker is the owned repair the store's own open makes
        if text is not None:
            format_marker.supported_format(text)
    except OSError as exc:
        msg = f"{target} holds an entry OwlBear cannot read: nothing was changed"
        raise StoreError(msg) from exc
    finally:
        os.close(tfd)
