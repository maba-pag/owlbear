"""Runs the one-time legacy preference import against the store (R15, FND-01).

The profile marker moves ``"" -> "pending" -> "done"``. The claim (``pending``) records the project config's digest
before the fill, and the fill runs only while the config still matches it, under the config lock. A pending claim is
never released, so an owner's clear, a config deletion, or a crash between claim and fill cannot refill the layer. A
crash that left the fill unknown stays pending and is reported for review through Settings. A publication notice is a
failure, like a raised error.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from owlbear_delivery_next.settings.prefs_import import plan
from owlbear_delivery_next.state_store import profile_share
from owlbear_delivery_next.state_store.config_save import Prepared

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.profile_record import Profile
    from owlbear_delivery_next.settings.config import Layer
    from owlbear_delivery_next.state_store.store import Store

ABSENT = profile_share.ABSENT
REVIEW = (
    "the legacy preference import is incomplete: the project settings changed or were removed after it was claimed; "
    "review the Merge and cleanup preferences on the Settings page"
)


def _fill(store: Store, prof: Profile, basis: str, *, resumed: bool) -> None:
    """Carry the legacy values into the project layer under its lock, if the layer is still the claimed one."""
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports its helpers

    def change(cur: Layer) -> Layer:
        if cur.prefs_imported:
            return cur  # landed earlier (a crash before done): republish only
        if (resumed and basis in ("", ABSENT)) or profile_share.config_digest(store.config_path) != basis:
            raise StoreError(REVIEW)  # raised before any write: a deleted or changed config is not recreated
        return plan(cur, prof)

    notice = store.update_config(Prepared(basis, change), "legacy preferences carried")
    if notice:
        msg = f"the legacy preferences were not published: {notice}"
        raise StoreError(msg)


def _publish_config(store: Store) -> str:
    """Publish the project config as it is now: an edit when present, else its removal, never a rewrite."""
    if store.config_path.exists():
        return store.update_config(lambda cur: cur, "legacy preferences carried")
    if not store.shared:
        return ""
    with store.shared.locked():
        return profile_share.publish_config_unlocked(store)


def republish(store: Store) -> None:
    """Publish a completion that a refused publication left local: the current config first, then the marker."""
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports its helpers

    if not profile_share.unpublished(store):
        return
    notice = _publish_config(store) or store.retry_prefs_import()
    if notice:
        msg = f"the legacy import completion was not published: {notice}"
        raise StoreError(msg)


def run(store: Store) -> None:
    """Carry the owner's confirmed legacy preferences into the project layer once; raises on an unpublished step.

    A claim is acquired only when the marker reads ``""``: it gets a fresh nonce, and it is the winner only when its
    publication is confirmed by a fresh read that carries that nonce. Any other pending claim resumes only from its own
    durable basis. A claim whose publication was not confirmed is published again before any fill. A completed import
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
        _, notice, won = store.mark_prefs_import(
            "", "pending", profile_share.config_digest(store.config_path), uuid4().hex
        )
        if notice:
            msg = f"the legacy import claim was not published: {notice}"
            raise StoreError(msg)
        prof = store.read_profile()
        if prof is None or prof.prefs_import != "pending":
            return
        _fill(store, prof, prof.prefs_basis, resumed=not won)  # a lost claim never creates the config
    elif profile_share.claim_unconfirmed(store, prof):
        notice, won = profile_share.confirm_claim(store)
        if notice:
            msg = f"the legacy import claim was not published: {notice}"
            raise StoreError(msg)
        prof = store.read_profile()
        if prof is None or prof.prefs_import != "pending":
            return
        _fill(store, prof, prof.prefs_basis, resumed=not won)
    else:
        _fill(store, prof, prof.prefs_basis, resumed=True)
    _, notice, _ = store.mark_prefs_import("pending", "done")
    if notice:
        msg = f"the legacy import completion was not published: {notice}"
        raise StoreError(msg)
