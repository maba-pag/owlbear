"""Runs the one-time legacy preference import against the store (R15, FND-01).

The profile marker moves ``"" -> "pending" -> "done"``. The claim (``pending``) records the project config's digest
before the fill, and the fill runs only while the config still matches it, under the config lock. A pending claim is
never released, so an owner's clear, a config deletion, or a crash between claim and fill cannot refill the layer. A
crash that left the fill unknown stays pending and is reported for review through Settings. A publication notice is a
failure, like a raised error.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING
from uuid import uuid4

from owlbear_delivery_next.local_system.publication_hold import Requires
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


class _SupersededError(Exception):
    """The claim was settled, cleared or replaced before the fill: the fill writes nothing."""


def _claim_held(store: Store, claim: str, basis: str) -> None:
    """Raise _SupersededError unless the profile still holds this pending claim; the caller holds the private lock."""
    held = profile_share._read_unlocked(store)  # noqa: SLF001 - the claim is read under the private lock
    if held is None or (held.prefs_import, held.prefs_claim, held.prefs_basis) != ("pending", claim, basis):
        raise _SupersededError


def _fill(store: Store, prof: Profile, basis: str, *, resumed: bool) -> bool:
    """Carry the legacy values into the project layer under its lock, if the layer is still the claimed one.

    The claim is checked under the private lock. An unshared clone keeps that lock through the write, so a mark or
    clear that waits for it cannot land between the check and the write. Returns False when the claim is no longer
    held: nothing is written, so nothing is recreated.
    """
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports its helpers

    claim = prof.prefs_claim
    held_through_write = contextlib.ExitStack()

    def change(cur: Layer) -> Layer:
        # a shared clone's shared lock already orders marks, and its publication takes the private lock itself
        if store.shared:
            with profile_share._writer(store, create=False, shared=False):  # noqa: SLF001 - the claim's own lock
                _claim_held(store, claim, basis)
        else:
            held_through_write.enter_context(profile_share._writer(store, create=False, shared=False))  # noqa: SLF001
            _claim_held(store, claim, basis)
        if cur.prefs_imported:
            return cur  # landed earlier (a crash before done): republish only
        if (resumed and basis in ("", ABSENT)) or profile_share.config_digest(store.config_path) != basis:
            raise StoreError(REVIEW)  # raised before any write: a deleted or changed config is not recreated
        return plan(cur, prof)

    # held until published: a remote that settled, cleared or replaced the claim meanwhile never gets this fill
    fields = {"prefs_import": "pending", "prefs_claim": claim, "prefs_basis": basis}
    requires = Requires("the legacy preference import claim this checkout filled", profile_share.path(store), fields)
    try:
        notice = store.update_config(Prepared(basis, change, requires), "legacy preferences carried")
    except _SupersededError:
        return False
    finally:
        held_through_write.close()
    if notice:
        msg = f"the legacy preferences were not published: {notice}"
        raise StoreError(msg)
    return True


def _publish_config(store: Store) -> str:
    """Publish the project config as it is now under the shared lock: an edit when present, else its removal."""
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


def _claimed(store: Store, prof: Profile) -> tuple[Profile, bool] | None:
    """The pending claim this run may fill, with whether this run won it; None when there is nothing to fill.

    The fresh read is the one the fill checks its claim against, so a claim replaced after this read is refused there.
    """
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports its helpers

    if prof.prefs_import == "":
        _, notice, won = store.mark_prefs_import(
            "", "pending", profile_share.config_digest(store.config_path), uuid4().hex
        )
    elif profile_share.claim_unconfirmed(store, prof):
        notice, won = profile_share.confirm_claim(store)
    else:
        return prof, False  # resumed from its own durable basis
    if notice:
        msg = f"the legacy import claim was not published: {notice}"
        raise StoreError(msg)
    fresh = store.read_profile()
    if fresh is None or fresh.prefs_import != "pending":
        return None
    return fresh, won


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
    claimed = _claimed(store, prof)
    if claimed is None:
        return
    fresh, won = claimed
    if not _fill(store, fresh, fresh.prefs_basis, resumed=not won):  # a lost or superseded claim creates nothing
        return
    _, notice, _ = store.mark_prefs_import("pending", "done")
    if notice:
        msg = f"the legacy import completion was not published: {notice}"
        raise StoreError(msg)
