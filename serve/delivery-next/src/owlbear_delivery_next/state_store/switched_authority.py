"""The read-only authority a completed offline move leaves in its retained source.

Registration and self-check read a fenced source through this check only. It writes nothing, creates nothing and
opens no store, and it accepts the project's store only when the source's own SWITCHED receipt names that store and
the store still holds that receipt's identity, proof and format.
"""

import os
from typing import TYPE_CHECKING

from owlbear_delivery_next.state_store import fd_tree, project_home, project_move, project_switch
from owlbear_delivery_next.state_store.database import StoreError
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
        if rec is not None:
            if rec["phase"] != project_move.SWITCHED or rec["target"] != str(target):
                msg = f"{folder} was not switched to {target}: its receipt names another store; nothing was changed"
                raise StoreError(msg)
            project_switch.prepared_prior(fd)
            _proven(target, rec)
        if not same_folder(folder, fd):
            msg = f"{folder} no longer names the retained source that was checked: nothing was changed"
            raise StoreError(msg)
        return target if rec is not None else None
    finally:
        os.close(fd)


def _proven(target: Path, rec: dict) -> None:
    """Refuse unless *target* is the folder the receipt recorded, holding its proof and format, nothing quarantined."""
    project_switch.require_switched(target, rec)
