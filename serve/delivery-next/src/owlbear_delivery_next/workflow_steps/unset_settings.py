"""A step that meets an unset setting asks the owner to fill it in (the owner, 2026-10-23: code ships no defaults)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.failures import ErrorKind, cause_key
from owlbear_delivery_next.change_contracts.models import Option
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.workflow_steps import engine

if TYPE_CHECKING:
    from owlbear_delivery_next.settings.config import SettingsUnset
    from owlbear_delivery_next.state_store.store import Lock, Store


PAUSE = Option(id="pause", label="Pause", next="pause")


def asked(store: Store, lock: Lock, exc: SettingsUnset) -> None:
    """The step asks the owner to fill the unset settings in on the Settings page, then continue or pause."""
    kind = store.read(lock.slug).step.kind
    cause = cause_key(ErrorKind.STATE, kind, "settings-unset")
    text = f"This step needs settings no layer sets: {', '.join(exc.keys)}. Fill them in on the Settings page."
    options = [Option(id="done", label="Done, run the step again", next="retry"), PAUSE]  # keeps its task and mode
    question = engine.ask(kind, text, cause, options)
    store.write(lock, loop.apply(store.read(lock.slug), question, datetime.now(UTC)))
