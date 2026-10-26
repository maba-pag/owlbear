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
    step: Callable[[str], Step],
    head: str,
) -> str:
    """Run *step*, which writes and publishes *files*, as one journaled batch; the caller holds the lock.

    *head* is the one `decision_sync.prepare` proved on the remote before the caller planned *files*; the journal names
    it and *step* receives it for every publication. The journal completes once the files landed in HEAD, or when the
    producer's known refusal left HEAD unmoved and put them back as they were. An unknown publication, a partial
    commit, a bare notice without that refusal, or an exception stays interrupted for the owner: it is never completed
    on a guess. Nothing nests: a batch within it would be a second one.
    """
    store._interrupted(shared)  # noqa: SLF001 - same package; store helpers stay private to it
    rows = [(p.relative_to(shared.root).as_posix(), store._content(p), data) for p, data in files]  # noqa: SLF001
    generation = decision_batch.begin(shared, project, head, message, [p.stem for p, _ in files], rows)
    try:
        outcome = step(head)
    except BaseException:
        if landed(shared, head, rows):
            decision_batch.complete(shared, generation)
        raise
    if landed(shared, head, rows) and not outcome.unknown:
        decision_batch.complete(shared, generation)
        return outcome.notice
    images = {shared.root / rel: (before, after) for rel, before, after in rows}
    if outcome.refused and not outcome.unknown and settle(shared, images, head, generation):
        return outcome.notice
    text = f"interrupted batch {generation}: finish or abandon it in Decisions"
    return store._join(outcome.notice, text)[:300]  # noqa: SLF001


def settle(shared: DataRepo, images: dict[Path, tuple[bytes | None, bytes]], head: str, generation: str) -> bool:
    """Put a failed or refused batch's files back and complete it, only while HEAD is proved still *head* around it.

    Immediately before each file is put back, the owner's epoch is proved anew (`_owner_epoch`); the first failure stops
    the put-back, so a file the owner committed meanwhile is never touched. Nothing is put back while a rebase is active
    or unknown, once HEAD moved from *head* (an owner's commit is never reverted), while the index holds a change to
    any of the files, or when a file holds neither image. HEAD is proved again after the put-back. Returns whether the
    batch was completed; when not, it stays interrupted for the owner's finish or abandon.
    """
    try:
        for path, (text, _) in images.items():
            if not _owner_epoch(shared, images, head):
                return False
            store._put_back(path, text)  # noqa: SLF001 - same package; store helpers stay private to it
    except OSError:
        return False
    if not decision_batch.restored({path: text for path, (text, _) in images.items()}) or not _still(shared, head):
        return False
    decision_batch.complete(shared, generation)
    return True


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


def _still(shared: DataRepo, head: str) -> bool:
    """No rebase in flight, and HEAD read last is still *head*: the proof that a failed batch is unpublished."""
    return operation_idle(shared) and head_commit(shared) == head


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

    The folders are checked before the file is read, so a linked project or `decisions` folder is never followed.
    """
    path = shared.root / rel
    return decision_batch.plain_in_checkout(shared.root, path) and path.is_file() and path.read_bytes() == after
