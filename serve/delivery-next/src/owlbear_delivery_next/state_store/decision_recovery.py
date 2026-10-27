"""The owner's explicit finish or abandon of an interrupted decision batch, by the generation the owner saw.

Finish writes the batch's files as they were written, reloads the decisions and publishes them as one commit when
none of the reloaded findings involves the batch's decisions. Abandon puts each file back as it was before the batch.
Neither undoes Git history or the index. Both refuse when Git's head is not the one the batch began at, and abandon
refuses a batch already in that head: only finish completes such a batch.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from owlbear_decisions.snapshot import CONFLICT
from owlbear_delivery_next.local_system import storage_io
from owlbear_delivery_next.local_system.data_repo import SAVE_SECONDS, DataRepoError
from owlbear_delivery_next.state_store import decision_batch, decision_store, decision_sync, decision_transaction
from owlbear_delivery_next.state_store.decision_store import RECOVER, DecisionsUnavailable

if TYPE_CHECKING:
    from owlbear_decisions import Entry, Finding
    from owlbear_delivery_next.local_system.data_repo import DataRepo


@dataclass(frozen=True)
class Recovery:
    """What became of the owner's choice: done, or refused with the reason it stays interrupted."""

    generation: str
    done: bool
    notice: str


def _current(shared: DataRepo, generation: str) -> decision_batch.Batch:
    try:
        batch = decision_batch.pending(shared)
    except decision_batch.JournalError as exc:
        raise DecisionsUnavailable(str(exc)[:600], RECOVER) from exc
    if batch is None or batch.generation != generation:
        msg = f"no interrupted decision batch has generation {generation}; it may be finished or changed"
        raise DecisionsUnavailable(msg, RECOVER)
    return batch


def _committed(shared: DataRepo, batch: decision_batch.Batch) -> str | None:
    """HEAD's commit, when it descends from the batch's head and holds every file's after image; else None."""
    commit = decision_transaction.head_commit(shared)
    if commit is None or shared.git("merge-base", "--is-ancestor", batch.head, commit).returncode:
        return None
    if all(decision_transaction.in_head(shared, rel, after, commit) for rel, _, after in batch.files):
        return commit
    return None


def _written(root: DataRepo, batch: decision_batch.Batch) -> None:
    """Refuse unless each file is a plain file in the checkout holding exactly its after image, as committed in Git."""
    for rel, _, after in batch.files:
        if not decision_transaction.worktree_holds(root, rel, after):
            msg = (
                f"{rel} is committed for batch {batch.generation}, but its worktree differs from it, so nothing "
                "is changed; resolve it by hand"
            )
            raise DecisionsUnavailable(msg, RECOVER)
    _still_plain(root, batch)


def _idle(shared: DataRepo, batch: decision_batch.Batch) -> None:
    """Refuse while a rebase is active or unknown: it is read before any other Git read, restore or remote proof."""
    if not decision_transaction.operation_idle(shared):
        msg = f"a rebase is active or unknown, so batch {batch.generation} is not recovered; resolve it in Git first"
        raise DecisionsUnavailable(msg, RECOVER)


def _fenced(shared: DataRepo, batch: decision_batch.Batch) -> None:
    """The owner's epoch, proved immediately before each file is written: idle Git, every file owned, HEAD read last.

    A refusal stops the remaining writes, so a file the owner committed or edited meanwhile is never touched.
    """
    _idle(shared, batch)
    _preflight(shared, batch)
    _same_head(shared, batch)


def _same_head(shared: DataRepo, batch: decision_batch.Batch) -> None:
    if decision_transaction.head_commit(shared) != batch.head:
        msg = f"Git's head moved while batch {batch.generation} was recovered, so it stays interrupted; check Git"
        raise DecisionsUnavailable(msg, RECOVER)


def _all_before(root: DataRepo, batch: decision_batch.Batch) -> None:
    """Refuse unless every file of the batch is plain and exactly its before image, absent where it had none."""
    if not decision_batch.restored(root.root, {root.root / rel: before for rel, before, _ in batch.files}):
        msg = f"a file of batch {batch.generation} changed while it was put back, so it stays interrupted; check it"
        raise DecisionsUnavailable(msg, RECOVER)


def _still_before(root: DataRepo, batch: decision_batch.Batch) -> None:
    """`_all_before` read again, with no fsync, after the blocking probes that follow it."""
    if not decision_batch.holds_before(root.root, {root.root / rel: before for rel, before, _ in batch.files}):
        msg = f"a file of batch {batch.generation} changed while it was put back, so it stays interrupted; check it"
        raise DecisionsUnavailable(msg, RECOVER)


def _at_head(shared: DataRepo, batch: decision_batch.Batch) -> None:
    if decision_store.head(shared) != batch.head:
        msg = f"Git's head moved since batch {batch.generation} began, so it is not recovered here; resolve it by hand"
        raise DecisionsUnavailable(msg, RECOVER)


def _preflight(root: DataRepo, batch: decision_batch.Batch) -> None:
    """Refuse before any write unless every file still holds its before or its after image, under plain folders."""
    for rel, before, after in batch.files:
        path = root.root / rel
        if path.is_symlink():
            msg = f"{rel} is a symlink, so batch {batch.generation} is not changed; resolve it by hand"
            raise DecisionsUnavailable(msg, RECOVER)
        for folder in path.parents:
            if folder == root.root:
                break
            if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
                msg = (
                    f"{rel} lies under {folder.name}, which is not a plain folder; "
                    f"batch {batch.generation} is not changed"
                )
                raise DecisionsUnavailable(msg, RECOVER)
        try:
            current = storage_io.read_regular(path)
        except OSError as exc:  # a pipe, a link or an unreadable file: refused before any write, the batch kept
            msg = f"{rel} cannot be read as a plain file ({exc}), so batch {batch.generation} is not changed"
            raise DecisionsUnavailable(msg, RECOVER) from exc
        if current not in (before, after):
            msg = f"{rel} was edited since batch {batch.generation} began, so nothing is changed; resolve it by hand"
            raise DecisionsUnavailable(msg, RECOVER)
    _still_plain(root, batch)


def _still_plain(root: DataRepo, batch: decision_batch.Batch) -> None:
    """Refuse unless every path still lies under plain folders, checked after all the reads it guards."""
    if not decision_batch.still_plain(root.root, [root.root / rel for rel, _, _ in batch.files]):
        msg = f"a folder of batch {batch.generation} changed while it was read, so nothing is changed; check it"
        raise DecisionsUnavailable(msg, RECOVER)


def finish(shared: DataRepo, generation: str) -> Recovery:
    """Publish the interrupted batch as it was written, if it validates; the marker completes only with the commit."""
    root = decision_store.checkout(shared)
    try:
        with root.locked():
            batch = _current(root, generation)
            _idle(root, batch)
            if _committed(root, batch) is not None:
                _written(root, batch)
                if not decision_transaction.landed(root, batch.head, batch.files):  # the last proof, before completion
                    msg = (
                        f"batch {generation} is committed but not proved now (Git or a file changed); it stays for you"
                    )
                    raise DecisionsUnavailable(msg, RECOVER)
                decision_batch.complete(root, generation)
                notice = "committed locally; no push/rebase retried: its marker is completed"
                return Recovery(generation=generation, done=True, notice=notice)
            _at_head(root, batch)
            if decision_sync.behind_unproved(root, batch.head, time.monotonic() + SAVE_SECONDS):
                msg = f"the remote moved past {batch.head[:12]}, so batch {generation} is not republished here"
                raise DecisionsUnavailable(msg, RECOVER)
            _preflight(root, batch)
            for rel, _, after in batch.files:
                _fenced(root, batch)  # after the remote proof, before this file's folder is made
                storage_io.make_dirs((root.root / rel).parent)
                # proved again after the folder and the new bytes are durable, immediately before the rename
                decision_batch.replace_file(root.root / rel, after, lambda: _fenced(root, batch), root.root)
            _validate(root, batch)
            paths = [root.root / rel for rel, _, _ in batch.files]
            sent = decision_sync.publish(root, paths, batch.message, time.monotonic() + SAVE_SECONDS, batch.head)
            landed = decision_transaction.landed(root, batch.head, batch.files)
            if sent.uncommitted or sent.stale or sent.ambiguous or not landed:
                why = sent.notice[:300] or "Git does not hold the batch as written"
                return Recovery(generation=generation, done=False, notice=f"not published, so it stays: {why}")
            _written(root, batch)
            if not decision_transaction.landed(root, batch.head, batch.files):  # the last proof, before completion
                msg = f"batch {generation} was published but not proved now (Git or a file changed); it stays for you"
                raise DecisionsUnavailable(msg, RECOVER)
            decision_batch.complete(root, generation)
            said = "finished: the batch is published as one commit"
            if sent.notice:  # committed and proved here, but its push did not go through: the owner still needs to know
                said = f"finished here, but not yet on the remote: {sent.notice}"[:300]
            return Recovery(generation=generation, done=True, notice=said)
    except (DataRepoError, OSError) as exc:
        raise DecisionsUnavailable(str(exc)[:600], RECOVER) from exc


def _validate(root: DataRepo, batch: decision_batch.Batch) -> None:
    seen = decision_store.files(root, batch.project)
    decision_store.usable(seen, batch.project)
    by_id, findings = decision_store.whole(root)
    involved = [f for f in findings if set(f.involves) & set(batch.ids)]
    if involved and not _rivals_flagged(by_id, findings, batch.ids):
        named = "; ".join(f"{f.path}: {f.message}" for f in involved[:3])
        msg = f"the interrupted batch {batch.generation} does not validate, so it is not published: {named}"[:600]
        raise DecisionsUnavailable(msg, RECOVER)


def _rivals_flagged(by_id: dict[str, Entry], findings: list[Finding], ids: tuple[str, ...]) -> bool:
    """Whether a flag batch flagged every rival its findings touch, leaving only the expected two-successors findings.

    Every decision of the batch and every rival the findings name must be flagged `conflict`, and each finding touched
    must be a two-successors finding; an unflagged rival of any of them refuses the batch.
    """

    def flagged(decision_id: str) -> bool:
        entry = by_id.get(decision_id)
        return entry is not None and entry.decision.conflict

    if not ids or not all(flagged(i) for i in ids):
        return False
    touched = [f for f in findings if set(f.involves) & set(ids)]
    targets = {f.involves[-1] for f in touched}
    named = [f for f in findings if set(f.involves) & (set(ids) | targets)]
    if any(f.rule != CONFLICT for f in named):
        return False
    return all(flagged(f.involves[0]) for f in named)


def abandon(shared: DataRepo, generation: str) -> Recovery:
    """Put each file of the interrupted batch back as it was before; Git and the index stay as they are."""
    root = decision_store.checkout(shared)
    try:
        with root.locked():
            batch = _current(root, generation)
            _idle(root, batch)
            if _committed(root, batch) is not None:
                msg = f"batch {generation} is already committed in Git: finish it, which completes its marker, instead"
                raise DecisionsUnavailable(msg, RECOVER)
            _at_head(root, batch)
            _preflight(root, batch)
            for rel, before, _ in batch.files:  # proved inside each put-back, immediately before its rename or unlink
                decision_batch.replace_file(root.root / rel, before, lambda: _fenced(root, batch), root.root)
            _all_before(root, batch)  # every file exactly as before and durable
            _idle(root, batch)
            _still_before(root, batch)  # read again after the rebase probe, with no fsync; then HEAD is read last
            _same_head(root, batch)
            decision_batch.complete(root, generation)
            notice = "abandoned: the files are as they were; Git is unchanged"
            return Recovery(generation=generation, done=True, notice=notice)
    except (DataRepoError, OSError) as exc:
        raise DecisionsUnavailable(str(exc)[:600], RECOVER) from exc
