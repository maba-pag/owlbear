"""A step that meets an unset setting stops for the owner to fill it in (the owner, 2026-10-23: no defaults in code)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.failures import ErrorKind, cause_key
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.workflow_steps import engine

if TYPE_CHECKING:
    from owlbear_delivery_next.settings.config import SettingsUnset
    from owlbear_delivery_next.state_store.store import Lock, Store


def asked(store: Store, lock: Lock, exc: SettingsUnset) -> None:
    """The step stops until the owner fills the unset settings in on the Settings page; nothing invents a value.

    The stop names no key: the Settings page marks every unset row by its own words. The activity log keeps the keys.
    """
    now = datetime.now(UTC)
    kind = store.read(lock.slug).step.kind
    cause = cause_key(ErrorKind.STATE, kind, "settings-unset")
    said = "This step needs settings that are not set. Fill them in on the Settings page, then run the step again"
    event = {"event": "settings-unset", "at": now.isoformat(timespec="seconds"), "reason": ", ".join(exc.keys)}
    store.log(lock, lock.slug, event)
    store.write(lock, loop.apply(store.read(lock.slug), engine.blocked(cause, said, "", now), now))
