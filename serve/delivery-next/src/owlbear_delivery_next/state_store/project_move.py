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
from dataclasses import dataclass
from pathlib import Path

from owlbear_delivery_next.local_system import codebase, local_home
from owlbear_delivery_next.state_store import fd_tree
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


@dataclass(frozen=True)
class OfflineProof:
    """Issued only by ``offline_protocol.finish`` after every precondition held; nothing else can build one.

    *previous* is the format marker the store had before the fence, as the preparation recorded it.
    """

    folder: Path
    previous: str


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
        msg = f"{folder / MOVE_RECORD} is unreadable: nothing was moved; check it, then start again"
        raise StoreError(msg) from exc
    if found is None:
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


def _save(folder: Path, folder_fd: int, rec: dict) -> None:
    """Write the move record into the pinned folder; refused, not written, when the clone path no longer names it."""
    if not _same_folder(folder, folder_fd):
        msg = f"{folder} no longer names the folder being moved: nothing was changed; check it, then start again"
        raise StoreError(msg)
    fd_tree.write_at(folder_fd, MOVE_RECORD, json.dumps(rec, sort_keys=True) + "\n")


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


def _same_folder(folder: Path, folder_fd: int) -> bool:
    """Whether the path *folder* still names the folder the descriptor pins."""
    try:
        return _ident(folder.stat()) == _ident(os.fstat(folder_fd))
    except OSError:
        return False


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
        or not _same_folder(target, tfd)  # the path must still reach the pinned folder through its ancestors
    ):
        raise _not_published(target)
    if not all(_entry_ok(tfd, n, d) for n, d in rec["manifest"].items()) or not _proof_ok(tfd, rec):
        raise _not_published(target)
    if set(os.listdir(tfd)) - {MARKER} != set(rec["manifest"]) | {MOVE_PROOF}:
        raise _not_published(target)


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
        if rec["stage_id"] is None:  # made but not yet recorded: only an empty folder can be ours
            if names:
                raise _unrecorded(stage)
            return
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


def _move(folder: Path, folder_fd: int, target: Path, pfd: int) -> None:
    """Copy the clone's store beside *target*, verify it, rename it into place in one step, then retire the source.

    Raises:
        StoreError: The target or staging folder exists, or the source changed; nothing unowned is overwritten.
    """
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
    sfd = _open_at(pfd, stage_name)
    try:
        rec["stage_id"] = _ident(os.fstat(sfd))
        _save(folder, folder_fd, rec)
        rec["proof"] = secrets.token_hex(16)
        fd_tree.create_verified_at(sfd, MOVE_PROOF, f"{rec['proof']}\n")
        _save(folder, folder_fd, rec)
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
    if _stat_at(pfd, target.name):
        raise _both(folder, target)
    os.rename(stage_name, target.name, src_dir_fd=pfd, dst_dir_fd=pfd)  # the copy becomes the store in one step
    fd_tree.sync(pfd, target.name)
    fd_tree.sync_names(pfd, target, local_home.root())  # durable in its parent and above before the switch
    tfd = _open_at(pfd, target.name)  # held until the switch is recorded: the published copy cannot swap under it
    try:
        if not _same_folder(target, tfd):  # the path moved under the pinned parent: refuse before the switch
            msg = (
                f"{target} no longer names the published store: nothing was removed; "
                "check the folders, then start again"
            )
            raise StoreError(msg)
        if not _source_unchanged(folder_fd, rec):  # a write after the copy: the switch is refused, nothing is lost
            msg = (
                f"{folder} changed after it was copied: the copy is kept at {target} and the switch was not recorded; "
                "stop the other OwlBear process, then start again"
            )
            raise StoreError(msg)
        rec["phase"] = SWITCHED
        _save(folder, folder_fd, rec)  # the target is the authority from here; the source is kept, never removed
    finally:
        os.close(tfd)


def _resume(folder: Path, folder_fd: int, target: Path, pfd: int, rec: dict) -> bool:
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
            if not _source_unchanged(folder_fd, rec):  # the source is still the authority until the switch
                msg = (
                    f"{folder} changed after it was copied: nothing was switched; "
                    "stop the other OwlBear process, then start again"
                )
                raise StoreError(msg)
            tfd = _open_at(pfd, target.name)  # only the copy this move published may stand in for the store
            try:
                _published(pfd, target, tfd, rec)
                fd_tree.sync_names(pfd, target, local_home.root())  # a resumed move syncs before any switch
                rec["phase"] = SWITCHED
                _save(folder, folder_fd, rec)
            finally:
                os.close(tfd)
        return False
    if rec["phase"] == SWITCHED:
        raise _not_published(target)
    _owned(pfd, stage_name, rec, complete=False)
    _pending_ours(folder_fd, pfd, stage_name, rec)
    if _stat_at(pfd, stage_name) is not None:
        fd_tree.keep_entry(pfd, stage_name)  # kept, synced, never reused; the source is still whole
    return True


def named_switched(target: Path, rec: dict) -> None:
    """Refuse unless *target* still names the folder the switch recorded, read without creating anything.

    Raises:
        StoreError: The target is missing, is not a folder, or is another folder.
    """
    try:
        st = os.lstat(target)
    except OSError:
        st = None
    if rec["stage_id"] is None or st is None or not stat.S_ISDIR(st.st_mode) or _ident(st) != rec["stage_id"]:
        raise _not_published(target)


def check_switched(target: Path, pfd: int, rec: dict) -> None:
    """Refuse unless the store at *target* is still the copy the switch recorded: by identity, not by contents.

    The target is in use once switched, so its bytes are not compared. A quarantined entry in it is refused, unowned.

    Raises:
        StoreError: The target is missing or is another folder, or it holds a quarantined entry.
    """
    named_switched(target, rec)
    tfd = _open_at(pfd, target.name)
    try:
        if _ident(os.fstat(tfd)) != rec["stage_id"] or not _same_folder(target, tfd) or not _proof_ok(tfd, rec):
            raise _not_published(target)  # a freed folder can return with the same identity: the proof decides
        fd_tree.refuse_quarantined(tfd, target)
    finally:
        os.close(tfd)


def require_proof(folder: Path, folder_fd: int, target: Path, proof: OfflineProof | None) -> None:
    """Refuse a move that no offline proof for *folder* covers; the caller has touched nothing yet.

    The proof names the folder by path; the pinned descriptor must still be that folder.

    Raises:
        StoreError: No offline proof was issued for *folder*, or the path no longer names the pinned folder.
    """
    if proof is None or proof.folder != folder or not _same_folder(folder, folder_fd):
        msg = f"{folder} cannot move to {target} yet: no offline proof that nothing else writes it; nothing was moved"
        raise StoreError(msg)


def relocate(  # noqa: PLR0913, PLR0917
    folder: Path, folder_fd: int, target: Path, pfd: int, rec: dict | None, proof: OfflineProof | None
) -> None:
    """Move the clone's store into *target* under *pfd*, or finish the move *rec* proves; refused without a proof.

    Raises:
        StoreError: No offline proof was issued, a link is in the way, or the record or a folder is not what it proves.
    """
    require_proof(folder, folder_fd, target, proof)
    st = _stat_at(pfd, target.name)
    if st is not None and stat.S_ISLNK(st.st_mode):
        msg = f"{target} holds a link: refusing to move through it; nothing was moved"
        raise StoreError(msg)
    if rec is None:
        if left_at(folder_fd):
            _move(folder, folder_fd, target, pfd)
        return
    if _resume(folder, folder_fd, target, pfd, rec):
        _move(folder, folder_fd, target, pfd)
