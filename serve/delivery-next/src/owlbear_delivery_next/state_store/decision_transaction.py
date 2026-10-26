"""Journaled writes and publications of decision files: one batch, completed only on proof (DEC-01)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, NamedTuple

from owlbear_delivery_next.local_system.data_repo import SAVE_SECONDS, DataRepoError
from owlbear_delivery_next.state_store import decision_batch
from owlbear_delivery_next.state_store import decision_store as store

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    from owlbear_delivery_next.local_system.data_repo import DataRepo

    type Fence = Callable[[], None]  # a writer's last proof before its rename; it raises when the write must not land


class Step(NamedTuple):
    """What a batch's step reports: its notice, whether its publication is unknown, and whether it is a known refusal.

    `refused` is set only by a producer that proves nothing of the batch reached Git, such as a failed commit with HEAD
    unmoved. A notice alone never counts as a refusal.
    """

    notice: str
    unknown: bool = False
    refused: bool = False


def guard(shared: DataRepo) -> None:
    """Refuse a new write while an interrupted batch is pending; the caller holds the lock.

    Producers call this before `decision_sync.prepare`, so a refused write never fetches, rebases or pushes. Owner
    Finish and Abandon do not come through here: they recover the pending generation.
    """
    store._interrupted(shared)  # noqa: SLF001 - same package; store helpers stay private to it


def transaction(  # noqa: PLR0913, PLR0917 - the head the caller proved travels with its project, files and step
    shared: DataRepo,
    project: str,
    message: str,
    files: Sequence[tuple[Path, bytes]],
    step: Callable[[str, Fence], Step],
    head: str,
) -> str:
    """Run *step*, which writes and publishes *files*, as one journaled batch; the caller holds the lock.

    *head* is the one `decision_sync.prepare` proved on the remote before the caller planned *files*; the journal names
    it and *step* receives it for every publication, with the fence (`write_fence`) each of its writes runs immediately
    before its rename. The before images are read, then every path is checked plain again before the journal. The
    journal completes once the files landed in HEAD, or when the producer's known refusal left HEAD unmoved and put
    them back as they were. An unknown publication, a partial commit, a bare notice without that refusal, or an
    exception stays interrupted for the owner: it is never completed on a guess. Nothing nests: a batch within it would
    be a second one.
    """
    store._interrupted(shared)  # noqa: SLF001 - same package; store helpers stay private to it
    rows = [(p.relative_to(shared.root).as_posix(), store._content(p), data) for p, data in files]  # noqa: SLF001
    planned(shared, [p for p, _ in files])
    generation = decision_batch.begin(shared, project, head, message, [p.stem for p, _ in files], rows)
    images = {shared.root / rel: (before, after) for rel, before, after in rows}
    try:
        outcome = step(head, write_fence(shared, images, head))
    except BaseException:
        if landed(shared, head, rows):
            decision_batch.complete(shared, generation)
        raise
    if landed(shared, head, rows) and not outcome.unknown:
        decision_batch.complete(shared, generation)
        return outcome.notice
    if outcome.refused and not outcome.unknown and settle(shared, images, head, generation):
        return outcome.notice
    text = f"interrupted batch {generation}: finish or abandon it in Decisions"
    return store._join(outcome.notice, text)[:300]  # noqa: SLF001


def planned(shared: DataRepo, paths: Sequence[Path]) -> None:
    """Refuse before any journal unless every path read for the batch's plan still lies under plain folders."""
    if not decision_batch.still_plain(shared.root, paths):
        msg = "a decision folder changed while the batch was planned, so nothing is written; check the checkout"
        raise store.DecisionsUnavailable(msg, store.READ)


def write_fence(shared: DataRepo, images: dict[Path, tuple[bytes | None, bytes]], head: str) -> Fence:
    """The proof each of a batch's own writes runs after its new bytes are durable and immediately before its rename.

    No rebase is active or unknown, every file of the batch is plain and holds its before or after image (checked
    again after those reads), and HEAD, read last, is still *head*. Nothing more is written when it fails, and the
    batch stays interrupted for the owner; the index is not part of it, as a write never needed it clean.
    """

    def fence() -> None:
        if operation_idle(shared) and decision_batch.owned(shared.root, images) and head_commit(shared) == head:
            return
        msg = "a decision file, its folder, Git's head or a rebase changed during the write, so nothing more is written"
        raise store.DecisionsUnavailable(msg, store.RECOVER)

    return fence


class _Moved(Exception):  # noqa: N818 - a refused proof, not an error: the batch stays for the owner
    """The owner's epoch no longer holds, so nothing more is put back."""


def settle(shared: DataRepo, images: dict[Path, tuple[bytes | None, bytes]], head: str, generation: str) -> bool:
    """Put a failed or refused batch's files back and complete it, only while HEAD is proved still *head* around it.

    The owner's epoch (`_owner_epoch`) is proved inside each put-back, after its new bytes are durable and immediately
    before its rename or unlink; the first failure stops the put-back, so a file the owner edited or committed meanwhile
    is never touched. Nothing is put back while a rebase is active or unknown, once HEAD moved from *head* (an owner's
    commit is never reverted), while the index holds a change to any of the files, or when a file holds neither image.
    At the end every file must hold exactly its before image, and HEAD is proved last. Returns whether the batch was
    completed; when not, it stays interrupted for the owner's finish or abandon.
    """

    def fence() -> None:
        if not _owner_epoch(shared, images, head):
            raise _Moved

    try:
        for path, (text, _) in images.items():
            store._put_back(path, text, fence, shared.root)  # noqa: SLF001 - same package; store helpers stay private
    except OSError, _Moved:
        return False
    before = {path: text for path, (text, _) in images.items()}
    if not decision_batch.restored(shared.root, before) or not _settled(shared, images, before, head):
        return False
    decision_batch.complete(shared, generation)
    return True


def _settled(
    shared: DataRepo, images: dict[Path, tuple[bytes | None, bytes]], before: dict[Path, bytes | None], head: str
) -> bool:
    """The final proof of a put-back, a file put back and then changed during a probe keeping the batch.

    No rebase and a clean index, then every file exactly its before image again, read after those blocking probes, and
    HEAD read last.
    """
    if not operation_idle(shared) or _staged(shared, images):
        return False
    return decision_batch.holds_before(shared.root, before) and head_commit(shared) == head


def _owner_epoch(shared: DataRepo, images: dict[Path, tuple[bytes | None, bytes]], head: str) -> bool:
    """No rebase, a clean index and every file owned, then HEAD read last, so no probe can hide an owner's commit."""
    if not operation_idle(shared) or _staged(shared, images) or not decision_batch.owned(shared.root, images):
        return False
    return head_commit(shared) == head


def _staged(shared: DataRepo, images: dict[Path, tuple[bytes | None, bytes]]) -> bool:
    """Whether the index differs from HEAD for any of the files, or Git cannot tell; the index is never reset here."""
    until = time.monotonic() + SAVE_SECONDS
    rels = [path.relative_to(shared.root).as_posix() for path in images]
    return any(shared.git("diff", "--cached", "--quiet", "--", rel, until=until).returncode for rel in rels)


def landed(shared: DataRepo, head: str, rows: Sequence[tuple[str, bytes | None, bytes]]) -> bool:
    """The one proof that a batch is published.

    HEAD descends from *head* and holds each file's after image, and each worktree file is exactly that after image.
    One HEAD commit is read for all of it and checked again at the end, so a commit moving mid-proof cannot pass. An
    active or unknown rebase is never published. The terminal rebase probe runs before the final HEAD read, so a HEAD
    move during that probe is caught too. Finish and every completion path use this same check.
    """
    if not operation_idle(shared):
        return False
    commit = head_commit(shared)
    if commit is None or shared.git("merge-base", "--is-ancestor", head, commit).returncode:
        return False
    if not all(in_head(shared, rel, after, commit) and worktree_holds(shared, rel, after) for rel, _, after in rows):
        return False
    if not decision_batch.still_plain(shared.root, [shared.root / rel for rel, _, _ in rows]):  # after every read
        return False
    return operation_idle(shared) and head_commit(shared) == commit


def operation_idle(shared: DataRepo) -> bool:
    """No rebase is active or unknown; read again after the blob and worktree proof, since a rebase can start in it."""
    try:
        return not shared.rebasing()
    except DataRepoError:
        return False


def head_commit(shared: DataRepo) -> str | None:
    """HEAD's commit, or None when Git cannot name it; a proof reads it once and checks it again last."""
    said = shared.git("rev-parse", "--verify", "-q", "HEAD")
    return None if said.returncode or not said.stdout.strip() else said.stdout.strip()


def in_head(shared: DataRepo, rel: str, after: bytes, commit: str) -> bool:
    """Whether *commit* holds *rel* as the after image."""
    said = shared.git("show", f"{commit}:{rel}")
    return not said.returncode and said.stdout.encode("utf-8") == after


def worktree_holds(shared: DataRepo, rel: str, after: bytes) -> bool:
    """Whether *rel* is a plain file under plain folders of the checkout, holding exactly the after image.

    The folders are checked before the file is read, so a linked project or `decisions` folder is never followed, and
    again after it, so one swapped for a link during the read cannot lend a foreign file's bytes.
    """
    path = shared.root / rel
    if not (decision_batch.plain_in_checkout(shared.root, path) and path.is_file()):
        return False
    return path.read_bytes() == after and decision_batch.still_plain(shared.root, [path])
