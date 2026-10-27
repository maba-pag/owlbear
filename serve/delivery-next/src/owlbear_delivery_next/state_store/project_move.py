"""Moving a clone's store into its project folder (TD-334), in verified stages.

``move.json`` in the clone records the move: its target, the staging folder beside the target with its device and
inode, the digest of every source entry before the copy, each copy as it is verified, and the phase. The whole store
is copied into the staging folder and verified; the staging folder is then renamed to the target in one step and the
record marked ``switched``. From then on the target is the authority and the source is kept whole, in place, as a
fenced, non-authoritative backup: nothing in it is removed or moved. A folder or entry that is not what the record
proves is refused and kept; nothing unproven is removed or overwritten.
"""

from __future__ import annotations

import contextlib
import json
import os
import secrets
import stat
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system import codebase, local_home
from owlbear_delivery_next.state_store import fd_tree, format_marker
from owlbear_delivery_next.state_store.database import MARKER, StoreError
from owlbear_delivery_next.state_store.fd_tree import (
    digest_at as _digest_at,
)
from owlbear_delivery_next.state_store.fd_tree import (
    entry_ok as _entry_ok,
)
from owlbear_delivery_next.state_store.fd_tree import (
    holds_text_at as _holds_text_at,
)
from owlbear_delivery_next.state_store.fd_tree import (
    ident as _ident,
)
from owlbear_delivery_next.state_store.fd_tree import (
    open_dir as _open_at,
)
from owlbear_delivery_next.state_store.fd_tree import (
    stat_at as _stat_at,
)
from owlbear_delivery_next.state_store.offline_proof import OfflineProof, require_proof, same_folder

if TYPE_CHECKING:
    from collections.abc import Callable

CLONE_ID = "clone-id"
MOVE_LOCK = "move.lock"
MOVE_RECORD = "move.json"
MOVE_PROOF = ".move-proof"  # random bytes this move wrote into its copy: identity the inode numbers cannot reuse
PREPARED = "prepare.json"  # the offline preparation: stays in the clone, never moves
FENCE = "999"  # reserved source fence: above every admitted producer format, so no admitted runtime can write it
COPYING, SWITCHED = "copying", "switched"
RECORD_KEYS = frozenset({"target", "stage", "stage_id", "proof", "manifest", "copied", "pending", "phase"})
KEPT = frozenset({CLONE_ID, MARKER, MOVE_LOCK, MOVE_RECORD, PREPARED})
STAGE_ID_FIELDS = 2  # a folder's identity: its device and inode


def pin(folder: Path) -> int | None:
    """A descriptor for the clone's folder, or None when it does not exist; a link or non-folder is refused."""
    try:
        return os.open(folder, fd_tree.DIR_FLAGS)
    except FileNotFoundError:
        return None
    except OSError as exc:
        msg = f"{folder} holds a link or is not a folder: nothing was moved"
        raise StoreError(msg) from exc


def left_at(folder_fd: int) -> list[str]:
    """What of a store still lies in the pinned folder; lock files hold no state and never move."""
    return [
        n
        for n in fd_tree.names_at(folder_fd)
        if n not in KEPT and not n.endswith(".lock") and not n.startswith(".tmp-")
    ]


def left(folder: Path) -> list[str]:
    """What of a store still lies in the clone's folder, read through a pinned descriptor."""
    fd = pin(folder)
    if fd is None:
        return []
    try:
        return left_at(fd)
    finally:
        os.close(fd)


def record_at(folder: Path, folder_fd: int) -> dict | None:
    """The cross-volume move the pinned folder began and has not finished, or None; an unreadable record is refused."""
    try:
        text = fd_tree.read_at(folder_fd, MOVE_RECORD)
        found = None if text is None else json.loads(text)
    except (OSError, ValueError) as exc:
        msg = f"{folder / MOVE_RECORD} is unreadable ({exc}): nothing was moved; check it, then start again"
        raise StoreError(msg) from exc
    if text is None:
        return None
    if not _is_record(found):
        msg = f"{folder / MOVE_RECORD} is not a move record: nothing was moved; check it, then start again"
        raise StoreError(msg)
    return found


def record(folder: Path) -> dict | None:
    """The clone's unfinished move record, read through a pinned descriptor; None when there is none."""
    fd = pin(folder)
    if fd is None:
        return None
    try:
        return record_at(folder, fd)
    finally:
        os.close(fd)


def _is_record(found: object) -> bool:
    if not isinstance(found, dict) or set(found) != RECORD_KEYS:
        return False
    ids = found["stage_id"]
    id_ok = ids is None or (
        isinstance(ids, list) and len(ids) == STAGE_ID_FIELDS and all(isinstance(i, int) for i in ids)
    )
    strings_ok = all(isinstance(found[k], str) for k in ("target", "stage", "phase")) and found["phase"] in (
        COPYING,
        SWITCHED,
    )
    pending_ok = found["pending"] is None or isinstance(found["pending"], str)
    proof_ok = found["proof"] is None or isinstance(found["proof"], str)
    maps_ok = all(
        isinstance(m, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in m.items())
        for m in (found["manifest"], found["copied"])
    )
    return id_ok and strings_ok and pending_ok and proof_ok and maps_ok


def _proof_ok(dfd: int, rec: dict) -> bool:
    """Whether *dfd* still holds the regular file with the nonce this move wrote and recorded."""
    return rec["proof"] is not None and _holds_text_at(dfd, MOVE_PROOF, f"{rec['proof']}\n")


def _save(folder: Path, folder_fd: int, rec: dict, *, before_replace: Callable[[], None] | None = None) -> None:
    """Write the move record into the pinned folder; refused, not written, when the clone path no longer names it."""
    if not same_folder(folder, folder_fd):
        msg = f"{folder} no longer names the folder being moved: nothing was changed; check it, then start again"
        raise StoreError(msg)
    fd_tree.write_at(folder_fd, MOVE_RECORD, json.dumps(rec, sort_keys=True) + "\n", before_replace=before_replace)


def make_dir(dfd: int, name: str) -> None:
    """Create folder *name* under *dfd* unless it already exists; a new name is synced in its folder."""
    with contextlib.suppress(FileExistsError):
        os.mkdir(name, 0o700, dir_fd=dfd)
        os.fsync(dfd)


def _make_root(root: Path) -> None:
    """Create *root* and any missing ancestors, each folder that gained a name synced."""
    missing: list[Path] = []
    part = root
    while not part.exists():
        missing.append(part)
        part = part.parent
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    for made in missing:
        dfd = os.open(made.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)


def pin_parent(target: Path) -> int:
    """Open the folder *target* lies in by descriptor, creating what is missing; no folder under root may be a link."""
    root = local_home.root()
    _make_root(root)
    try:
        fd = os.open(root, fd_tree.DIR_FLAGS)
    except OSError as exc:
        msg = f"{root} holds a link or is not a folder: refusing to move through it; nothing was moved"
        raise StoreError(msg) from exc
    try:
        for part in target.parent.relative_to(root).parts:
            make_dir(fd, part)
            child = _open_at(fd, part)
            os.close(fd)
            fd = child
    except BaseException:
        os.close(fd)
        raise
    return fd


def _not_published(target: Path) -> StoreError:
    msg = f"{target} is not the copy this move published: nothing was removed; move it away, then start again"
    return StoreError(msg)


def _unrecorded(stage: Path) -> StoreError:
    msg = f"{stage} is not from a move OwlBear recorded: nothing was moved; move it away, then start again"
    return StoreError(msg)


def _both(folder: Path, target: Path) -> StoreError:
    msg = (
        f"{folder} and {target} both exist: an older OwlBear process may still use the clone; "
        f"stop it (a chat's server: {codebase.STOP}), move one of them away, then start it again"
    )
    return StoreError(msg)


def _stage_name(target: Path) -> str:
    return f".{target.name}.staging"


def _published(pfd: int, target: Path, tfd: int, rec: dict) -> None:
    """Refuse unless the copy this move published, held open at *tfd*, still holds the recorded digests.

    The target's name must still name the same folder the descriptor holds, and the copy holds exactly the manifest.
    """
    st = _stat_at(pfd, target.name)
    if (
        rec["stage_id"] is None
        or st is None
        or not stat.S_ISDIR(st.st_mode)
        or _ident(st) != rec["stage_id"]
        or _ident(os.fstat(tfd)) != rec["stage_id"]
        or not same_folder(target, tfd)  # the path must still reach the pinned folder through its ancestors
    ):
        raise _not_published(target)
    if not all(_entry_ok(tfd, n, d) for n, d in rec["manifest"].items()) or not _proof_ok(tfd, rec):
        raise _not_published(target)
    if set(os.listdir(tfd)) - {MARKER} != set(rec["manifest"]) | {MOVE_PROOF}:
        raise _not_published(target)


def _sync_published(pfd: int, target: Path, tfd: int) -> None:
    """Make the published copy durable through *tfd* before a switch; on failure nothing is switched."""
    try:
        for child in os.listdir(tfd):
            fd_tree.sync(tfd, child)
        os.fsync(tfd)
        fd_tree.sync_names(pfd, target, local_home.root())
    except OSError as exc:
        msg = f"{target} was not made durable ({exc.strerror}): nothing was switched; check the disk, then start again"
        raise StoreError(msg) from exc


def _staged_ok(sfd: int, names: set[str], rec: dict, *, complete: bool) -> bool:
    """Whether the staged entries are the ones the record proves: the proof, and the copies it lists."""
    if MOVE_PROOF in names and not _proof_ok(sfd, rec):
        return False
    body = names - {MOVE_PROOF}
    if complete:
        return rec["pending"] is None and MOVE_PROOF in names and body == set(rec["copied"]) == set(rec["manifest"])
    return body <= set(rec["copied"]) | ({rec["pending"]} - {None})


def _owned(pfd: int, stage_name: str, rec: dict, *, complete: bool) -> None:
    """Refuse unless the staging folder is the one this move made, holding only entries it recorded."""
    st = _stat_at(pfd, stage_name)
    if st is None:
        return
    stage = Path(rec["stage"])
    if not stat.S_ISDIR(st.st_mode):
        raise _unrecorded(stage)
    sfd = _open_at(pfd, stage_name)
    try:
        names = set(os.listdir(sfd))  # noqa: PTH208 - listed by descriptor, not by path
        if rec["stage_id"] is None:  # made but its identity was never recorded: never adopted, even when empty
            raise _unrecorded(stage)
        if _ident(os.fstat(sfd)) != rec["stage_id"] or not _staged_ok(sfd, names, rec, complete=complete):
            raise _unrecorded(stage)
        if not all(_entry_ok(sfd, n, d) for n, d in rec["copied"].items()):
            raise _unrecorded(stage)
    finally:
        os.close(sfd)


def _pending_ours(folder_fd: int, pfd: int, stage_name: str, rec: dict) -> None:
    """Refuse when the entry copied when the move stopped is not a prefix of its source: foreign bytes stay put."""
    if rec["pending"] is None or _stat_at(pfd, stage_name) is None:
        return
    sfd = _open_at(pfd, stage_name)
    try:
        if rec["pending"] in os.listdir(sfd) and not fd_tree.partial_of(folder_fd, sfd, rec["pending"]):  # noqa: PTH208
            raise _unrecorded(Path(rec["stage"]))
    finally:
        os.close(sfd)


def _source_unchanged(folder_fd: int, rec: dict) -> bool:
    """Whether the source still holds exactly the manifest the move recorded: no entry added, removed or edited."""
    return set(left_at(folder_fd)) == set(rec["manifest"]) and all(
        _entry_ok(folder_fd, n, d) for n, d in rec["manifest"].items()
    )


def _copy_each(folder: Path, folder_fd: int, sfd: int, rec: dict) -> None:
    """Copy each source entry into the staging folder, verifying it against the digest taken before the move began.

    A mismatched copy is kept where it is, named as pending in the record; the source keeps every byte.
    """
    for name, digest in rec["manifest"].items():
        src = folder / name
        rec["pending"] = name
        _save(folder, folder_fd, rec)
        fd_tree.copy(folder_fd, name, sfd)
        fd_tree.sync(sfd, name)
        if not _entry_ok(sfd, name, digest) or not _entry_ok(folder_fd, name, digest):
            msg = (
                f"{src} changed while it was copied: the copy is kept in {rec['stage']} and nothing was removed; "
                "stop the other OwlBear process, then start again"
            )
            raise StoreError(msg)
        rec["copied"][name] = digest
        rec["pending"] = None
        _save(folder, folder_fd, rec)


def _move(folder: Path, folder_fd: int, target: Path, pfd: int, proof: OfflineProof) -> None:
    """Copy the clone's store beside *target*, verify it, rename it into place, then keep the source untouched."""
    if _stat_at(pfd, target.name):
        raise _both(folder, target)
    stage_name = _stage_name(target)
    if _stat_at(pfd, stage_name):
        raise _unrecorded(target.parent / stage_name)
    rec = {
        "target": str(target),
        "stage": str(target.parent / stage_name),
        "stage_id": None,
        "proof": None,
        "manifest": {n: _digest_at(folder_fd, n) for n in left_at(folder_fd)},
        "copied": {},
        "pending": None,
        "phase": COPYING,
    }
    _save(folder, folder_fd, rec)  # the record exists before anything is made beside the source
    os.mkdir(stage_name, 0o700, dir_fd=pfd)
    _stage_and_publish(folder, folder_fd, target, pfd, rec, format_marker.prior_format(proof.previous), proof)


def _stage_and_publish(  # noqa: PLR0913, PLR0917
    folder: Path, folder_fd: int, target: Path, pfd: int, rec: dict, previous: int, proof: OfflineProof
) -> None:
    """Record the proof nonce before its file exists, copy the source into the stage, then publish it at *target*."""
    stage_name = _stage_name(target)
    sfd = _open_at(pfd, stage_name)
    try:
        if rec["stage_id"] is None:
            rec["stage_id"] = _ident(os.fstat(sfd))
            _save(folder, folder_fd, rec)  # recorded before any proof or copy can exist in the stage
        if rec["proof"] is None:
            rec["proof"] = secrets.token_hex(16)
            _save(folder, folder_fd, rec)  # the nonce is recorded before its file can exist
        if _stat_at(sfd, MOVE_PROOF) is None:
            fd_tree.create_verified_at(sfd, MOVE_PROOF, f"{rec['proof']}\n")
        _copy_each(folder, folder_fd, sfd, rec)
    finally:
        os.close(sfd)
    _owned(pfd, stage_name, rec, complete=True)
    if not _source_unchanged(folder_fd, rec):
        msg = (
            f"{folder} changed while it was copied: nothing was switched; "
            "stop the other OwlBear process, then start again"
        )
        raise StoreError(msg)
    _publish(folder, folder_fd, target, pfd, rec, previous, proof)


def _commit(  # noqa: PLR0913, PLR0917
    folder: Path, folder_fd: int, target: Path, pfd: int, tfd: int, rec: dict, previous: int, proof: OfflineProof
) -> None:
    """Record the switch only after the held copy is durable, still the one published, and the source unchanged.

    The copy is proven ours before anything is written into it. The target's format marker is then written through
    the held descriptor. The original source proof, manifest and target are checked after both target durability
    and the SWITCHED record's temporary-file sync, immediately before its rename, with no intervening write or sync.
    """
    _published(pfd, target, tfd, rec)  # a foreign or altered copy is refused before any byte is written into it
    format_marker.ensure_target(tfd, previous)
    _sync_published(pfd, target, tfd)  # a retry re-syncs before any switch, so a failure stays uncommitted

    def unchanged() -> None:
        require_proof(folder, folder_fd, target, proof)
        _published(pfd, target, tfd, rec)
        format_marker.written_format(tfd, previous)
        if not _source_unchanged(folder_fd, rec):
            msg = (
                f"{folder} changed after it was copied: the copy is kept at {target} and the switch was not recorded; "
                "stop the other OwlBear process, then start again"
            )
            raise StoreError(msg)

    rec["phase"] = SWITCHED
    _save(folder, folder_fd, rec, before_replace=unchanged)  # only this guarded rename makes the target authoritative


def _publish(  # noqa: PLR0913, PLR0917
    folder: Path, folder_fd: int, target: Path, pfd: int, rec: dict, previous: int, proof: OfflineProof
) -> None:
    """Rename the verified stage to *target*, sync it durably, then record the switch (a failure keeps copying)."""
    if _stat_at(pfd, target.name):
        raise _both(folder, target)
    os.rename(_stage_name(target), target.name, src_dir_fd=pfd, dst_dir_fd=pfd)  # the copy becomes the store at once
    fd_tree.sync(pfd, target.name)
    tfd = _open_at(pfd, target.name)  # held until the switch is recorded: the published copy cannot swap under it
    try:
        _commit(folder, folder_fd, target, pfd, tfd, rec, previous, proof)
    finally:
        os.close(tfd)


def _holds_only_issued_proof(pfd: int, stage_name: str, rec: dict) -> bool:
    """Whether the staging folder holds nothing but the proof this move issued: no copy has begun, so it can resume."""
    if rec["stage_id"] is None or rec["proof"] is None or rec["copied"] or rec["pending"] is not None:
        return False
    sfd = _open_at(pfd, stage_name)
    try:
        return set(os.listdir(sfd)) <= {MOVE_PROOF}  # noqa: PTH208 - listed by descriptor, not by path
    finally:
        os.close(sfd)


def _resume(  # noqa: PLR0913, PLR0917
    folder: Path, folder_fd: int, target: Path, pfd: int, rec: dict, previous: int, proof: OfflineProof
) -> bool:
    """Finish the move the record proves; return True when the move must start again from the source.

    An interrupted staging folder is never reused or removed: it is kept under a quarantine name, and the source
    still holds every byte.
    """
    if rec["target"] != str(target):
        msg = (
            f"{folder / MOVE_RECORD} is for {rec['target']}, not {target}: "
            "nothing was moved; check it, then start again"
        )
        raise StoreError(msg)
    stage_name = _stage_name(target)
    if rec["stage"] != str(target.parent / stage_name):
        msg = f"{folder / MOVE_RECORD} names a staging folder that is not beside {target}: nothing was moved"
        raise StoreError(msg)
    if _stat_at(pfd, target.name):
        if rec["phase"] == COPYING:
            tfd = _open_at(pfd, target.name)  # only the copy this move published may stand in for the store
            try:
                _commit(folder, folder_fd, target, pfd, tfd, rec, previous, proof)
            finally:
                os.close(tfd)
        return False
    if rec["phase"] == SWITCHED:
        raise _not_published(target)
    _owned(pfd, stage_name, rec, complete=False)
    _pending_ours(folder_fd, pfd, stage_name, rec)
    # Nothing copied yet: the issued nonce is reused, not replaced.
    if _stat_at(pfd, stage_name) is not None and _holds_only_issued_proof(pfd, stage_name, rec):
        _stage_and_publish(folder, folder_fd, target, pfd, rec, previous, proof)
        return False
    if _stat_at(pfd, stage_name) is not None:
        fd_tree.keep_entry(pfd, stage_name)  # kept, synced, never reused; the source is still whole
    return True


def relocate(  # noqa: PLR0913, PLR0917
    folder: Path, folder_fd: int, target: Path, pfd: int, rec: dict | None, proof: OfflineProof | None, previous: int
) -> None:
    """Move the clone's store into *target* under *pfd*, or finish the move *rec* proves; refused without a proof.

    *previous* is the format the store held before the move; the target's marker records it.

    Raises:
        StoreError: No offline proof was issued, a link is in the way, or the record or a folder is not what it proves.
    """
    proof = require_proof(folder, folder_fd, target, proof)
    st = _stat_at(pfd, target.name)
    if st is not None and stat.S_ISLNK(st.st_mode):
        msg = f"{target} holds a link: refusing to move through it; nothing was moved"
        raise StoreError(msg)
    if rec is None:
        if left_at(folder_fd):
            _move(folder, folder_fd, target, pfd, proof)
        return
    if _resume(folder, folder_fd, target, pfd, rec, previous, proof):
        _move(folder, folder_fd, target, pfd, proof)
