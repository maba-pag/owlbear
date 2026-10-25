"""Journaled writes and publications of decision files: one batch, completed only on proof (DEC-01)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system.data_repo import SAVE_SECONDS
from owlbear_delivery_next.state_store import decision_batch
from owlbear_delivery_next.state_store import decision_store as store

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    from owlbear_delivery_next.local_system.data_repo import DataRepo


def transaction(
    shared: DataRepo,
    project: str,
    message: str,
    files: Sequence[tuple[Path, bytes]],
    step: Callable[[], tuple[str, bool]],
) -> str:
    """Run *step*, which writes and publishes *files*, as one journaled batch; the caller holds the lock.

    *step* returns its notice and whether its publication is unknown. The journal completes once the files landed in
    HEAD, or when a known refusal left HEAD unmoved and put them back as they were. An unknown publication, a
    partial commit, or an exception stays interrupted for the owner: it is never completed on a guess. Nothing nests: a
    batch within it would be a second one.
    """
    store._interrupted(shared)  # noqa: SLF001 - same package; store helpers stay private to it
    rows = [(p.relative_to(shared.root).as_posix(), store._content(p), data) for p, data in files]  # noqa: SLF001
    head = store._head(shared)  # noqa: SLF001
    generation = decision_batch.begin(shared, project, head, message, [p.stem for p, _ in files], rows)
    try:
        notice, unknown = step()
    except BaseException:
        if landed(shared, head, rows):
            decision_batch.complete(shared, generation)
        raise
    if landed(shared, head, rows) and not unknown:
        decision_batch.complete(shared, generation)
        return notice
    undo = {shared.root / rel: before for rel, before, _ in rows}
    moved = store._head(shared) != head  # noqa: SLF001
    deadline = time.monotonic() + SAVE_SECONDS
    if not unknown and not moved and store._refusal_settles(shared, undo, deadline):  # noqa: SLF001
        decision_batch.complete(shared, generation)
        return notice
    text = f"interrupted batch {generation}: finish or abandon it in Decisions"
    return store._join(notice, text)[:300]  # noqa: SLF001


def landed(shared: DataRepo, head: str, rows: Sequence[tuple[str, bytes | None, bytes]]) -> bool:
    """The one proof that a batch is published.

    HEAD descends from *head* and holds each file's after image, and each worktree file is exactly that after image.
    Finish and every completion path use this same check.
    """
    if shared.git("merge-base", "--is-ancestor", head, "HEAD").returncode:
        return False
    return all(in_head(shared, rel, after) and worktree_holds(shared, rel, after) for rel, _, after in rows)


def in_head(shared: DataRepo, rel: str, after: bytes) -> bool:
    """Whether HEAD holds *rel* as the after image."""
    said = shared.git("show", f"HEAD:{rel}")
    return not said.returncode and said.stdout.encode("utf-8") == after


def worktree_holds(shared: DataRepo, rel: str, after: bytes) -> bool:
    """Whether *rel* is a plain file in the worktree holding exactly the after image."""
    path = shared.root / rel
    return not path.is_symlink() and path.is_file() and path.read_bytes() == after
