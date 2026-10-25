"""Runs the one-time legacy preference import against the store (R15, FND-01).

The profile marker moves ``"" -> "pending" -> "done"``. The claim (``pending``) records the project config's digest
before the fill, and the fill runs only while the config still matches it, under the config lock. A pending claim is
never released, so an owner's clear, a config deletion, or a crash between claim and fill cannot refill the layer. A
crash that left the fill unknown stays pending and is reported for review through Settings. A publication notice is a
failure, like a raised error.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from owlbear_delivery_next.settings.prefs_import import plan
from owlbear_delivery_next.state_store import profile_share

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.profile_record import Profile
    from owlbear_delivery_next.settings.config import Layer
    from owlbear_delivery_next.state_store.store import Store

ABSENT = "absent"
REVIEW = (
    "the legacy preference import is incomplete: the project settings changed or were removed after it was claimed; "
    "review the Merge and cleanup preferences on the Settings page"
)


def _digest(path: Path) -> str:
    """The digest of the config file's bytes, or ``absent``."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return ABSENT


def _fill(store: Store, prof: Profile, basis: str, *, resumed: bool) -> None:
    """Carry the legacy values into the project layer under its lock, if the layer is still the claimed one."""
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports its helpers

    def change(cur: Layer) -> Layer:
        if cur.prefs_imported:
            return cur  # landed earlier (a crash before done): republish only
        if (resumed and basis in ("", ABSENT)) or _digest(store.config_path) != basis:
            raise StoreError(REVIEW)  # raised before any write: a deleted or changed config is not recreated
        return plan(cur, prof)

    notice = store.update_config(change, "legacy preferences carried")
    if notice:
        msg = f"the legacy preferences were not published: {notice}"
        raise StoreError(msg)


def republish(store: Store) -> None:
    """Publish a completion that a refused publication left local: the current config first, then the marker."""
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports its helpers

    if not profile_share.unpublished(store):
        return
    notice = store.update_config(lambda cur: cur, "legacy preferences carried") if store.config_path.exists() else ""
    notice = notice or store.retry_prefs_import()
    if notice:
        msg = f"the legacy import completion was not published: {notice}"
        raise StoreError(msg)


def run(store: Store) -> None:
    """Carry the owner's confirmed legacy preferences into the project layer once; raises on an unpublished step.

    A claim is acquired only when the marker reads ``""`` and the durable claim then carries this run's basis. Any other
    pending claim, including one a concurrent run made, resumes only from its own durable basis. A completed import
    whose publication was refused is published again here.
    """
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports its helpers

    prof = store.read_profile()
    if prof is None:
        return
    if prof.prefs_import == "done":
        republish(store)
        return
    if prof.prefs_import == "":
        _, notice, claimed = store.mark_prefs_import("", "pending", _digest(store.config_path))
        if notice:
            msg = f"the legacy import claim was not published: {notice}"
            raise StoreError(msg)
        prof = store.read_profile()
        if prof is None or prof.prefs_import != "pending":
            return
        _fill(store, prof, prof.prefs_basis, resumed=not claimed)  # a lost claim never creates the config
    else:
        _fill(store, prof, prof.prefs_basis, resumed=True)
    _, notice, _ = store.mark_prefs_import("pending", "done")
    if notice:
        msg = f"the legacy import completion was not published: {notice}"
        raise StoreError(msg)
