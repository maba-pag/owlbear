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
    moved = store._head(shared) != head  # noqa: SLF001
    if outcome.refused and not outcome.unknown and not moved:
        images = {shared.root / rel: (before, after) for rel, before, after in rows}
        if store._refusal_settles(shared, images, time.monotonic() + SAVE_SECONDS):  # noqa: SLF001
            decision_batch.complete(shared, generation)
            return outcome.notice
    text = f"interrupted batch {generation}: finish or abandon it in Decisions"
    return store._join(outcome.notice, text)[:300]  # noqa: SLF001


def landed(shared: DataRepo, head: str, rows: Sequence[tuple[str, bytes | None, bytes]]) -> bool:
    """The one proof that a batch is published.

    HEAD descends from *head* and holds each file's after image, and each worktree file is exactly that after image.
    One HEAD commit is read for all of it and checked again at the end, so a commit moving mid-proof cannot pass. An
    active or unknown rebase is never published. Finish and every completion path use this same check.
    """
    if not operation_idle(shared):
        return False
    commit = head_commit(shared)
    if commit is None or shared.git("merge-base", "--is-ancestor", head, commit).returncode:
        return False
    if not all(in_head(shared, rel, after, commit) and worktree_holds(shared, rel, after) for rel, _, after in rows):
        return False
    return head_commit(shared) == commit and operation_idle(shared)


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
    """Whether *rel* is a plain file in the worktree holding exactly the after image."""
    path = shared.root / rel
    return not path.is_symlink() and path.is_file() and path.read_bytes() == after
