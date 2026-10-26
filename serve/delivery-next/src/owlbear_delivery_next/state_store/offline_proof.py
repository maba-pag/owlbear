"""The offline proof a move needs, and the folder identity it binds: checked again through the pinned descriptor."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from owlbear_delivery_next.state_store import fd_tree
from owlbear_delivery_next.state_store.database import StoreError

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class OfflineProof:
    """Issued only by ``offline_protocol.finish`` after every precondition held; nothing else can build one.

    *previous* is the format marker the store had before the fence, as the preparation recorded it.
    *identity* is the (device, inode) of the folder that finish verified through its own descriptor.
    """

    folder: Path
    previous: str
    identity: tuple[int, int]


def same_folder(folder: Path, folder_fd: int) -> bool:
    """Whether the path *folder* still names the folder the descriptor pins."""
    try:
        return fd_tree.ident(folder.stat()) == fd_tree.ident(os.fstat(folder_fd))
    except OSError:
        return False


def require_identity(folder: Path, folder_fd: int, proof: OfflineProof) -> None:
    """Refuse unless the pinned descriptor is the folder *proof* was issued for, by the identity finish verified.

    A folder swapped in after the proof was issued has another identity, so it is refused before anything in it is read.

    Raises:
        StoreError: The path or the pinned folder is not the one the proof names.
    """
    if proof.folder != folder or tuple(fd_tree.ident(os.fstat(folder_fd))) != proof.identity:
        msg = (
            f"{folder} was replaced after its offline proof was issued: nothing was changed; "
            "start the offline move again"
        )
        raise StoreError(msg)
    if not same_folder(folder, folder_fd):
        msg = f"{folder} no longer names the folder being moved: nothing was changed; check it, then start again"
        raise StoreError(msg)


def require_proof(folder: Path, folder_fd: int, target: Path, proof: OfflineProof | None) -> None:
    """Refuse a move that no offline proof for *folder* covers; the caller has touched nothing yet.

    Raises:
        StoreError: No offline proof was issued for *folder*, or the pinned folder is not the one it proves.
    """
    if proof is None:
        msg = f"{folder} cannot move to {target} yet: no offline proof that nothing else writes it; nothing was moved"
        raise StoreError(msg)
    require_identity(folder, folder_fd, proof)
