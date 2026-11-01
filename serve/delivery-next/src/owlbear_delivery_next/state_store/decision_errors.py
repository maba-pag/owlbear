"""Why the decisions cannot be read, with what to do about it; and how a read tells a save in flight from a crash.

A read can meet a decision batch's unsettled state: its journal, its rebase, its files changing while they are read.
While a writer holds the repository-wide lock, that is a save in progress, and the read says so at once: it neither
waits nor sends the owner to recovery (#846). Once no writer holds it, the read is made again under a shared hold
that keeps every writer out, and what it meets then is settled: a journal left then is an interrupted batch.
"""

from __future__ import annotations

from contextlib import ExitStack
from typing import TYPE_CHECKING

from owlbear_delivery_next.state_store.database import StoreError

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.local_system.data_repo import DataRepo

SET_UP = "Set the shared data repository: `owlbear-next data PATH`"
SET_UP_PROJECT = "Set up the project so the shared data repository holds its folder: `owlbear-next setup`"
REPAIR = "Repair the shared data repository's checkout so Git can read it"
READ = "Make the decision folders and files in the shared data repository readable and valid"
RECOVER = "Finish or abandon the interrupted decision batch by its generation (owner's explicit choice)"
SAVING = "Wait for the decision save in progress to finish, then read again"
IN_PROGRESS = "a decision save is in progress, so the decisions are not settled; read them again shortly"


class DecisionsUnavailable(StoreError):  # noqa: N818 - the design's name for it
    """The decisions cannot be read, so no work may run as if there were none."""

    action = REPAIR
    resume = "The decisions load"

    def __init__(self, reason: str, action: str = REPAIR) -> None:
        super().__init__(reason)
        self.action = action


class Unsettled(DecisionsUnavailable):
    """A read met a batch's unsettled state: a save in progress while a writer holds the lock, else what it says."""


def settled[T](shared: DataRepo, read: Callable[[], T]) -> T:
    """*read*, or, when it met unsettled state, why: a save in progress while a writer holds the lock, else read again.

    The second read runs while no writer can start, so its outcome stands, a crash's recovery included.
    """
    try:
        return read()
    except Unsettled as first:
        with ExitStack() as stack:
            try:
                quiet = stack.enter_context(shared.quiet())
            except OSError, ValueError:  # the lock cannot be probed (`DataRepoError` included): the read's own error
                raise first from None
            if not quiet:
                raise DecisionsUnavailable(IN_PROGRESS, SAVING) from first
            return read()
