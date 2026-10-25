"""The fresh read-only challenge of a worker's proposed amendment, run after the step that proposed it (TD-179).

The candidate is recorded with the proposing step's effects, accounting and own result before its challenge starts,
so a restart judges that candidate without running its proposer again (RUN-04). The proposer's result routes the
step unless the challenger stops the Change.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.models import Exit, StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_flow import loop, worktree
from owlbear_delivery_next.local_system.git_files import git_common_dir
from owlbear_delivery_next.runtimes import amendments, sdk_adapter
from owlbear_delivery_next.workflow_steps import held_writes, pending_child, sessions

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.change_flow.loop import StepResult
    from owlbear_delivery_next.runtimes.session_result import Run
    from owlbear_delivery_next.settings.config import Settings
    from owlbear_delivery_next.state_store.store import Lock, Store


def proposed(change: Change, run: Run, result: StepResult) -> str | None:
    """Record the exact candidate a proposing run made; its id when it is to be judged, else None.

    Nothing starts while the proposer's processes are not confirmed gone (its result is then a stop).
    """
    if result.exit == Exit.STOP or not (run.termination and run.termination.confirmed):
        return None
    made = amendments.prepared(change, run, datetime.now(UTC))
    return made.id if made is not None else None


def challenge(  # noqa: PLR0913 - the proposer's writes, its candidate and its own result
    post: Store | held_writes.Deferred,
    lock: Lock,
    change: Change,
    path: Path,
    made: str,
    *,
    route: StepResult,
    settings: Settings | None = None,
) -> None:
    """Make the proposing step durable with its candidate and its own result *route*, then judge and settle it.

    *settings* is the snapshot the proposer started with, which checked the challenger's (``review.started``).
    """
    change.pending_child = pending_child.awaited(amendments.LABEL, made, route)
    store = held_writes.checkpoint(post, lock, change)  # a lost challenge leaves the candidate unjudged, its step kept
    _settled(store, lock, change, path, settings)


def resumed(store: Store, lock: Lock, change: Change, repo: Path) -> bool:
    """Settle a proposing step whose challenge did not: from the challenger's kept run, else a new challenger.

    Its proposer never runs again. A step the Change has left is not this one's (``pending_child.retired``).
    """
    pending = change.pending_child
    if pending is None or pending.label != amendments.LABEL or not pending_child.fits(change):
        return False
    path = worktree.ensure(repo, git_common_dir(repo), change.slug, change.names.branch, change.names.target)
    change.names.worktree = str(path)
    _settled(store, lock, change, path, None)
    return True


def _settled(store: Store, lock: Lock, change: Change, path: Path, settings: Settings | None) -> None:
    """Judge the candidate, then write its verdict, the challenger's spend and the step's route together, once.

    A challenger whose own processes are not confirmed gone stops the Change instead, its proposal left unjudged.
    """
    pending = change.pending_child
    made = pending_child.candidate(change, pending) if pending is not None else None
    if pending is None or made is None:
        msg = "an amendment challenge needs its recorded candidate"
        raise ValueError(msg)
    route = pending_child.route_of(pending)

    def config(at: Path) -> sdk_adapter.Session:
        return sdk_adapter.Session(
            kind=StepKind.REVIEW,
            worktree=at,
            session_id="",
            message=amendments.prompt(change, made, at),
            resume=False,
            policy=Policy(at, write=False),
            observe=lambda: worktree.observe(at, change.names.target),
            checks=(),
            journal=sdk_adapter.Journal(lambda e: store.log(lock, change.slug, e)),
            memory=sessions.memory(store),
        )

    def start() -> pending_child.Judged:
        return sessions.review_run(
            store, lock, change, path, config, amendments.LABEL, submit=amendments.SUBMIT, settings=settings, defer=True
        )

    verdict, done = pending_child.child(store, lock, change, (amendments.LABEL, made.id), start)
    step = pending_child.booked(change, done, {"exit": verdict.exit})
    amendments.judged(made, done)
    store.write(lock, loop.apply(change, verdict if verdict.exit == Exit.STOP else route, datetime.now(UTC)))
    if step is not None:  # logged once the verdict and its spend are durable
        sessions.announce(store, lock, change.slug, step)
