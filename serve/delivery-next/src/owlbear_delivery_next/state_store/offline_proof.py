"""The offline proof a move needs, and the folder identity it binds: checked again through the pinned descriptor."""

from __future__ import annotations

import contextlib
import json
import os
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from owlbear_delivery_next.state_store import fd_tree, format_marker
from owlbear_delivery_next.state_store.database import MARKER, StoreError

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

UUID = re.compile(r"[0-9A-F]{8}(?:-[0-9A-F]{4}){3}-[0-9A-F]{12}")


def preparation(text: str, folder_fd: int) -> dict:
    """Validate the complete preparation and its pinned source identity, including the supported prior format.

    Every source consumer uses this witness, not just Finish: copied metadata proves no custody of another folder.
    """
    try:
        data = json.loads(text)
    except ValueError as exc:
        msg = "offline preparation is unreadable: refusing it; nothing was changed"
        raise StoreError(msg) from exc
    valid = isinstance(data, dict) and set(data) == {"boot", "folder", "marker"}
    if valid:
        folder = data["folder"]
        valid = (
            isinstance(data["boot"], str)
            and UUID.fullmatch(data["boot"].upper()) is not None
            and isinstance(folder, list)
            and len(folder) == 2  # noqa: PLR2004 - a (device, inode) pair
            and all(type(part) is int for part in folder)
            and isinstance(data["marker"], str)
        )
    if not valid:
        msg = "not a preparation record OwlBear wrote: refusing it; nothing was changed"
        raise StoreError(msg)
    if data["folder"] != fd_tree.ident(os.fstat(folder_fd)):
        msg = "not the folder that was prepared: refusing it; nothing was changed"
        raise StoreError(msg)
    format_marker.prior_format(data["marker"])
    return data


@dataclass(frozen=True)
class OfflineProof:
    """Issued only by ``offline_protocol.finish`` after every precondition held; nothing else can build one.

    *previous* is the format marker the store had before the fence, as the preparation recorded it.
    *identity* is the (device, inode) of the folder that finish verified through its own descriptor.
    *prepared* is the exact preparation record text finish read; admission requires the same bytes to be there.
    """

    folder: Path
    previous: str
    identity: tuple[int, int]
    prepared: str

    @contextlib.contextmanager
    def guard(
        self, folder_fd: int, target: Path, target_fd: int | None = None, payload: fd_tree.PayloadImages | None = None
    ) -> Iterator[None]:
        """Retain source, optional target and collected payload images through all validation reads."""
        try:
            groups = [(folder_fd, ("prepare.json", MARKER, "clone-id", "move.json", "."))]
            if target_fd is not None:
                groups.append((target_fd, (".move-proof", MARKER, ".")))
            images = [(dfd, name, fd_tree.stat_at(dfd, name)) for dfd, names in groups for name in names]
            yield
            for name, tree in payload.items() if payload is not None else ():
                fd_tree.confirm_at(folder_fd, name, tree)
            if not all(fd_tree.same_image_at(dfd, name, before) for dfd, name, before in images):
                marker = fd_tree.read_at(folder_fd, MARKER)
                if marker is not None and marker.strip() != "999":
                    format_marker.supported_format(marker)
                if target_fd is not None:
                    marker = fd_tree.read_at(target_fd, MARKER)
                    if marker is not None:
                        format_marker.supported_format(marker)
                msg = f"{self.folder}'s offline witnesses changed during validation: nothing was switched"
                raise StoreError(msg)
            if not same_folder(self.folder, folder_fd) or (
                target_fd is not None and not same_folder(target, target_fd)
            ):
                msg = f"{self.folder} or {target} no longer names its verified folder: nothing was switched"
                raise StoreError(msg)
        except (OSError, UnicodeError) as exc:
            msg = f"{self.folder}'s offline witnesses cannot be checked: nothing was switched"
            raise StoreError(msg) from exc


def same_folder(folder: Path, folder_fd: int) -> bool:
    """Whether the path *folder* still names the folder the descriptor pins."""
    try:
        st = folder.stat(follow_symlinks=False)
        return fd_tree.ident(st) == fd_tree.ident(os.fstat(folder_fd))
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


def require_proof(folder: Path, folder_fd: int, target: Path, proof: OfflineProof | None) -> OfflineProof:
    """Require the issued source identity, exact preparation, fence and clone-id binding to *target*.

    Raises:
        StoreError: No proof covers this source generation and target; nothing was changed.
    """
    if proof is None:
        msg = f"{folder} cannot move to {target} yet: no offline proof that nothing else writes it; nothing was moved"
        raise StoreError(msg)
    require_identity(folder, folder_fd, proof)
    with proof.guard(folder_fd, target):
        try:
            prepared = fd_tree.read_at(folder_fd, "prepare.json")
            marker = fd_tree.read_at(folder_fd, MARKER)
            clone = fd_tree.read_at(folder_fd, "clone-id")
        except (OSError, UnicodeError) as exc:
            msg = f"{folder} has an unreadable offline witness: nothing was switched"
            raise StoreError(msg) from exc
        if prepared is not None:
            preparation(prepared, folder_fd)  # classify a future prior format without adopting a new preparation
        if marker is not None and marker.strip() != "999":
            format_marker.supported_format(marker)  # a future marker keeps its upgrade diagnostic
        if prepared != proof.prepared or marker is None or marker.strip() != "999":
            msg = (
                f"{folder} is not the folder finish verified as prepared and fenced: nothing was switched; start again"
            )
            raise StoreError(msg)
        if clone is None or not clone.endswith("\n") or clone.strip() != target.name:
            msg = f"{folder} no longer binds its clone id to {target}: nothing was switched"
            raise StoreError(msg)
    return proof
