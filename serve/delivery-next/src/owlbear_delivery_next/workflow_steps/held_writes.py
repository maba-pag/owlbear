"""An accepted hold's writes (RUN-04): kept in memory until its receipted result, or its checkpoint, is durable.

Processing an accepted hold writes as a session's processing does. Those writes wait, so a failed final write leaves
the stored Change as it was and a restart processes the hold once. A step that starts a paid child session after it
(a plan challenge, an amendment challenge) first writes its checkpoint with the receipt, so a restart never processes
the hold or starts its child again for a write the child's settlement lost.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.workflow_steps import held

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.runtimes.session_result import Run
    from owlbear_delivery_next.state_store.store import Lock, Store


class Deferred:
    """An accepted hold's post-session writes, kept in memory until its receipted result is written (RUN-04).

    A failed final write then leaves the stored Change as it was before those writes, so a restart runs them once.
    Other slugs and reads pass through to the store; after the checkpoint, so do this slug's.
    """

    def __init__(self, store: Store, slug: str) -> None:
        self._store = store
        self._slug = slug
        self._change: Change | None = None
        self._events: list[tuple[Lock, str, dict[str, Any]]] = []
        self.checkpointed = False

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401 - the store's other methods pass through
        return getattr(self._store, name)

    def read(self, slug: str) -> Change:
        """The slug's Change as last written here, else as the store has it."""
        if slug == self._slug and self._change is not None:
            return self._change.model_copy(deep=True)
        return self._store.read(slug)

    def write(self, lock: Lock, change: Change) -> None:
        """Hold this slug's Change in memory until the checkpoint; other slugs are written through."""
        if change.slug != self._slug or self.checkpointed:
            return self._store.write(lock, change)
        self._change = change.model_copy(deep=True)
        return None

    def log(self, lock: Lock, slug: str, event: dict[str, Any]) -> None:
        """Hold this slug's events in memory until the checkpoint; other slugs are logged through."""
        if slug != self._slug or self.checkpointed:
            return self._store.log(lock, slug, event)
        self._events.append((lock, slug, event))
        return None

    def flush(self) -> None:
        """The buffered events, once the receipted result is durable."""
        for lock, slug, event in self._events:
            self._store.log(lock, slug, event)
        self._events.clear()

    def checkpoint(self, lock: Lock, change: Change) -> Store:
        """Write the parent's checkpoint with the hold's receipt, then its buffered events, then remove the hold.

        Returns:
            The store itself, which the paid child and its settlement write to directly.
        """
        receipted(self._store, change, accepted=True)
        self._store.write(lock, change)
        self._change, self.checkpointed = None, True
        self.flush()
        receipt = change.accepted_holds[-1]
        held.consume(self._store, lock, self._slug)
        held.forget(change, receipt)  # consume cleared it from the stored Change; the settlement must not restore it
        return self._store


def checkpoint(post: Store | Deferred, lock: Lock, change: Change) -> Store:
    """Make a parent step durable before its paid child session starts; returns the store the child writes to."""
    if isinstance(post, Deferred):
        return post.checkpoint(lock, change)
    post.write(lock, change)
    return post


def receipted(store: Store, change: Change, *, accepted: bool) -> Change:
    """The Change with an accepted hold's identity recorded, so its result is written with the receipt."""
    if not accepted:
        return change
    found = held.read(store, change.slug)
    if found is None:
        msg = "the accepted held result is unreadable; the step stays for a restart"
        raise OSError(msg)
    change.accepted_holds = [*change.accepted_holds, held.gen(found)]
    return change


def write_result(  # noqa: PLR0913, PLR0917 - the receipt needs the store, lock, change, hold and deferred writes
    store: Store,
    lock: Lock,
    change: Change,
    accepted: Run | None,
    final: Change,
    post: Store | Deferred,
) -> None:
    """Write a step's result with an accepted hold's receipt, then remove the hold once that write is durable.

    A checkpointed hold's receipt is durable already, and the hold is removed.
    """
    receipt = accepted is not None and not (isinstance(post, Deferred) and post.checkpointed)
    store.write(lock, receipted(store, final, accepted=receipt))
    if isinstance(post, Deferred):  # the logs its writes deferred follow the receipted result
        post.flush()
    if receipt:  # a failed write, or a failed cleanup, leaves the hold: the receipt stops it running again
        held.consume(store, lock, change.slug)
