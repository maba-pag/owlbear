"""The locked save of one settings layer; an automatic config change never replaces another clone's intent."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system.data_repo import DataRepoError
from owlbear_delivery_next.state_store import profile_share
from owlbear_delivery_next.state_store.pending_intents import pending_intents
from owlbear_delivery_next.state_store.profile_share import CONFIG_WAITING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.local_system.publication_hold import Requires
    from owlbear_delivery_next.settings.config import Layer
    from owlbear_delivery_next.state_store.store import Store


STALE = "the project config changed after this automatic change was prepared: nothing was written; review it"
REBASING = "the shared settings repository has a rebase in progress: finish or abort it, then save again"


class HeldByPendingError(Exception):
    """An automatic change held back, before any write, by another clone's pending intent or a changed basis."""


def locked_save[T: Layer](  # noqa: PLR0913, PLR0917
    store: Store,
    path: Path,
    model: type[T],
    change: Callable[[T], T],
    message: str,
    until: float,
    *,
    owner: bool,
    on_written: Callable[[], None] | None = None,
) -> str:
    """Change and publish one settings layer under the shared lock; a held automatic config change writes nothing."""
    from owlbear_delivery_next.state_store.store import update_layer  # noqa: PLC0415 - the store imports this module

    automatic = path == store.config_path and not owner
    requires = change.requires if automatic and isinstance(change, Prepared) else None
    if automatic:
        held = (lambda: store.shared.hold(path, requires, until)) if requires else None
        change = _automatic(store, change, held)
    with store.shared.locked():
        if automatic and (behind := _caught_up(store, until)):
            return behind
        if requires:
            on_written = _noting(store, path, on_written, until)
        try:
            update_layer(path, model, change, on_written)
        except HeldByPendingError as exc:
            return str(exc)
        return profile_share.publish_layer(store, path, message, until, owner=owner)


def _caught_up(store: Store, until: float) -> str:
    """Rebase on the remote before the guards read the claim and config; why not, else nothing.

    A fetch alone leaves this checkout's claim and config stale. An owner's rebase in progress is never aborted: the
    save is refused instead.
    """
    try:
        if store.shared.rebasing(until):
            return REBASING
    except DataRepoError as exc:
        return str(exc)
    return store.shared.pull(until)


def _noting(store: Store, path: Path, on_written: Callable[[], None] | None, until: float) -> Callable[[], None]:
    """The write hook that first notes in the held record what the automatic change wrote."""

    def written() -> None:
        store.shared.filled(path, until)
        if on_written:
            on_written()

    return written


def unshared_save[T: Layer](  # noqa: PLR0913 - the store, the layer, its change, owner and the write hook
    store: Store,
    path: Path,
    model: type[T],
    change: Callable[[T], T],
    *,
    owner: bool,
    on_written: Callable[[], None] | None = None,
) -> str:
    """Change one settings layer of an unshared clone, with the same automatic guard and no publication."""
    from owlbear_delivery_next.state_store.store import update_layer  # noqa: PLC0415 - the store imports this module

    if path == store.config_path and not owner:
        change = _automatic(store, change)
    try:
        update_layer(path, model, change, on_written)
    except HeldByPendingError as exc:
        return str(exc)
    return ""


class Prepared[T: Layer]:
    """An automatic change prepared against the project config whose digest was *basis* when the caller read it.

    The save applies it only while the config is still that basis, under the lock, so a payload built from an older
    config never replaces a newer one. The change computes its result from its input alone. A shared change that
    *requires* a remote state is held to it until the remote has the change (`publication_hold`): nothing of the
    checkout is pushed or rebased over a remote that no longer meets it.
    """

    def __init__(self, basis: str, change: Callable[[T], T], requires: Requires | None = None) -> None:
        self.basis, self.change, self.requires = basis, change, requires

    def __call__(self, cur: T) -> T:
        """The change itself: the save checks the basis before any write."""
        return self.change(cur)


def _automatic[T: Layer](
    store: Store, change: Callable[[T], T], held: Callable[[], None] | None = None
) -> Callable[[T], T]:
    """The automatic config change under the lock: nothing is written behind another clone's pending intent.

    A change whose output differs from its input may publish only if it is still the basis it was prepared against,
    or, when unprepared, only if a shared pending intent is waiting for it. Unchanged output may publish current facts.
    The input is snapshotted first, so a change that edits it in place cannot look unchanged. A changed output that
    passes is *held* to the remote's state before it is written.
    """
    basis = change.basis if isinstance(change, Prepared) else None

    def guarded(cur: T) -> T:
        before = cur.model_dump_json(indent=1)
        new = change(cur)
        data = new.model_dump_json(indent=1)
        changed = data != before
        try:
            if changed and basis is not None and profile_share.config_digest(store.config_path) != basis:
                raise HeldByPendingError(STALE)
            if store.shared and profile_share.held_by_pending(store, data.encode()):
                raise HeldByPendingError(CONFIG_WAITING)
            if changed and basis is None and not (store.shared and pending_intents(store)):
                raise HeldByPendingError(STALE)
            if changed and held:
                held()
        except DataRepoError as exc:
            raise HeldByPendingError(str(exc)) from exc
        return new

    return guarded
