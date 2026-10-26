"""The owner's confirmed repair of an unreadable old profile in a shared folder (R15).

The replacement is staged under a private receipt before it is published, so a refused publication stays pending and
is retried without a new confirmation. The old profile is retired only after a published replacement, and only while it
still has the bytes the owner confirmed.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pydantic import ValidationError

from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.state_store import profile_share, roles_move
from owlbear_delivery_next.state_store.profile_share import PROFILE, SourceChangedError, _present

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.state_store.store import Store

RECEIPT = "profile-repair.json"


def unreadable_guard(source: Path) -> Profile | None:
    """The legacy import guard of a saved profile that cannot be read: kept when valid, malformed evidence raises."""
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports this module

    if not _present(source):
        return None
    try:
        data = json.loads(source.read_text())
    except (OSError, ValueError) as exc:
        msg = f"the saved profile's legacy import guard cannot be read: {source}"
        raise StoreError(msg) from exc
    if not isinstance(data, dict):
        msg = f"the saved profile's legacy import guard is malformed: {source}"
        raise StoreError(msg)
    try:
        return Profile(
            prefs_import=data.get("prefs_import", ""),
            prefs_basis=data.get("prefs_basis", ""),
            prefs_claim=data.get("prefs_claim"),
        )
    except ValidationError as exc:
        msg = f"the saved profile's legacy import guard is malformed: {source}"
        raise StoreError(msg) from exc


def pending(store: Store) -> tuple[str, Profile] | None:
    """The confirmed replacement still awaiting publication, with the old profile's digest it was confirmed against."""
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports this module

    receipt = store.root / RECEIPT
    try:
        text = receipt.read_text()
    except FileNotFoundError:
        return None
    try:
        data = json.loads(text)
        return str(data["source"]), Profile.model_validate_json(data["profile"])
    except (KeyError, TypeError, ValueError) as exc:  # a ValidationError is a ValueError
        msg = f"the pending profile repair cannot be read: {receipt}; remove it to confirm the replacement again"
        raise StoreError(msg) from exc


def publish(store: Store, prof: Profile, source: str) -> str:
    """Publish the confirmed replacement; a refused publication returns its notice and keeps the receipt."""
    atomic_write(store.root / RECEIPT, json.dumps({"source": source, "profile": prof.model_dump_json()}))
    try:
        notice = store.write_profile(prof, replace_unreadable=True, source=source)
    except SourceChangedError:
        clear(store)  # nothing was written: the receipt named bytes that are gone
        raise
    if notice:
        return notice
    finish(store, source)
    return ""


def finish(store: Store, source: str) -> None:
    """Retire the old profile once its replacement is published, while it still has the confirmed bytes."""
    if store.shared:
        with profile_share._writer(store):  # noqa: SLF001 - the same writer lock the publication held
            if profile_share.config_digest(store.root / PROFILE) != source:
                msg = "the old profile changed after the replacement was published; run setup again to review it"
                raise SourceChangedError(msg)
            roles_move.retire_source(store)
    clear(store)


def clear(store: Store) -> None:
    """Drop the pending receipt."""
    (store.root / RECEIPT).unlink(missing_ok=True)
