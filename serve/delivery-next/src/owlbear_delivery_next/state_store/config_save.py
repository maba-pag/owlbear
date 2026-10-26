"""The locked save of one settings layer; an automatic config change never replaces another clone's intent."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system.data_repo import DataRepoError
from owlbear_delivery_next.state_store import profile_share
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
        change = _held_while_pending(store, change)
    with store.shared.locked():
        try:
            update_layer(path, model, change)
        except HeldByPendingError as exc:
            return str(exc)
        return profile_share.publish_layer(store, path, message, until, owner=owner)


def based_on[T: Layer](store: Store, basis: str, change: Callable[[T], T]) -> Callable[[T], T]:
    """The automatic change, refused unless the project config is still the *basis* it was prepared against.

    *basis* is the config's digest read when the change was prepared; a payload built from an older config never
    replaces a newer one, whatever the current file holds. The caller reads the digest before preparing the change.
    """

    def guarded(cur: T) -> T:
        if profile_share.config_digest(store.config_path) != basis:
            raise HeldByPendingError(STALE)
        return change(cur)

    return guarded


def _held_while_pending[T: Layer](store: Store, change: Callable[[T], T]) -> Callable[[T], T]:
    def guarded(cur: T) -> T:
        new = change(cur)
        try:
            held = profile_share.held_by_pending(store, new.model_dump_json(indent=1).encode())
        except DataRepoError as exc:
            raise HeldByPendingError(str(exc)) from exc
        if held:
            raise HeldByPendingError(CONFIG_WAITING)
        return new

    return guarded
