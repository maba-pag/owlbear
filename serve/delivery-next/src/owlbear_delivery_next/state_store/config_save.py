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

    from owlbear_delivery_next.settings.config import Layer
    from owlbear_delivery_next.state_store.store import Store


STALE = "the project config changed after this automatic change was prepared: nothing was written; review it"


class HeldByPendingError(Exception):
    """An automatic change held back, before any write, by another clone's pending intent or a changed basis."""


def locked_save[T: Layer](  # noqa: PLR0913, PLR0917
    store: Store, path: Path, model: type[T], change: Callable[[T], T], message: str, until: float, *, owner: bool
) -> str:
    """Change and publish one settings layer under the shared lock; a held automatic config change writes nothing."""
    from owlbear_delivery_next.state_store.store import update_layer  # noqa: PLC0415 - the store imports this module

    if path == store.config_path and not owner:
        change = _automatic(store, change)
    with store.shared.locked():
        try:
            update_layer(path, model, change)
        except HeldByPendingError as exc:
            return str(exc)
        return profile_share.publish_layer(store, path, message, until, owner=owner)


def unshared_save[T: Layer](store: Store, path: Path, model: type[T], change: Callable[[T], T], *, owner: bool) -> str:
    """Change one settings layer of an unshared clone, with the same automatic guard and no publication."""
    from owlbear_delivery_next.state_store.store import update_layer  # noqa: PLC0415 - the store imports this module

    if path == store.config_path and not owner:
        change = _automatic(store, change)
    try:
        update_layer(path, model, change)
    except HeldByPendingError as exc:
        return str(exc)
    return ""


class Prepared[T: Layer]:
    """An automatic change prepared against the project config whose digest was *basis* when the caller read it.

    The save applies it only while the config is still that basis, under the lock, so a payload built from an older
    config never replaces a newer one. The change computes its result from its input alone.
    """

    def __init__(self, basis: str, change: Callable[[T], T]) -> None:
        self.basis, self.change = basis, change

    def __call__(self, cur: T) -> T:
        """The change itself: the save checks the basis before any write."""
        return self.change(cur)


def _automatic[T: Layer](store: Store, change: Callable[[T], T]) -> Callable[[T], T]:
    """The automatic config change under the lock: nothing is written behind another clone's pending intent.

    A change whose output differs from its input may publish only if it is still the basis it was prepared against,
    or, when unprepared, only if a shared pending intent is waiting for it. Unchanged output may publish current facts.
    The input is snapshotted first, so a change that edits it in place cannot look unchanged.
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
        except DataRepoError as exc:
            raise HeldByPendingError(str(exc)) from exc
        return new

    return guarded
