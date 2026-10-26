"""The owner's confirmed repair of an unreadable old profile in a shared folder (R15).

The replacement is staged under a private receipt before it is published, so a refused publication stays pending and
is retried without a new confirmation. The old profile is retired only after a published replacement, and only while it
still has the bytes the owner confirmed.
"""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from owlbear_delivery_next.change_contracts.profile_record import PROFILE_FORMAT, Profile
from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.state_store import profile_share, roles_move
from owlbear_delivery_next.state_store.profile_errors import Basis, SourceChangedError, TargetChangedError
from owlbear_delivery_next.state_store.profile_share import PROFILE, _present

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


class Receipt(BaseModel):
    """An owner-confirmed replacement staged before publication, bound to the old bytes and shared target it was for."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    format: Literal[1] = 1
    id: str = Field(pattern=r"^[0-9a-f]{32}$")
    scope: str  # the logical shared repository and project folder, or ``local``
    source: str  # the digest of the old unreadable profile the owner confirmed
    target: str  # the digest of the shared profile the owner confirmed against, or ``absent``
    profile: Profile

    @field_validator("profile")
    @classmethod
    def _current_and_confirmed(cls, prof: Profile) -> Profile:
        if prof.format != PROFILE_FORMAT:
            msg = f"the replacement is profile format {prof.format}, not {PROFILE_FORMAT}"
            raise ValueError(msg)
        if prof.confirmed_at is None:
            msg = "the replacement was never confirmed"
            raise ValueError(msg)
        return prof


def scope(store: Store) -> str:
    """The logical shared repository and project folder a replacement belongs to; a local store's scope otherwise."""
    return "local" if store.shared is None else f"{data_repo.identity(store.shared.root)}/{store.name}"


def _read(store: Store) -> Receipt | None:
    """The pending receipt, validated: malformed, future or unconfirmed evidence is refused, never replayed."""
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports this module

    receipt = store.root / RECEIPT
    try:
        text = receipt.read_text()
    except FileNotFoundError:
        return None
    except OSError as exc:
        msg = f"the pending profile repair cannot be read: {receipt}; check the file, then run setup again"
        raise StoreError(msg) from exc
    try:
        return Receipt.model_validate_json(text)
    except ValidationError as exc:
        msg = (
            f"the pending profile repair is malformed or from another version: {receipt}; "
            "remove it to confirm the replacement again"
        )
        raise StoreError(msg) from exc


def _own(store: Store, receipt_id: str) -> Receipt | None:
    """The pending receipt while it is still the one *receipt_id* names; another operation's receipt is not ours."""
    try:
        current = Receipt.model_validate_json((store.root / RECEIPT).read_text())
    except OSError, ValidationError:
        return None
    return current if current.id == receipt_id else None


def pending(store: Store) -> Receipt | None:
    """The confirmed replacement still awaiting publication; one staged for another shared repository is refused."""
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports this module

    receipt = _read(store)
    if receipt is not None and receipt.scope != scope(store):
        msg = (
            f"the pending profile repair was staged for another shared repository or folder: {store.root / RECEIPT}; "
            "remove it to discard the staged replacement, then run setup again"
        )
        raise StoreError(msg)
    return receipt


def stage(store: Store, prof: Profile, source: str, target: str) -> Receipt:
    """Stage the owner's confirmed replacement under a new id before it is published."""
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports this module

    with profile_share._writer(store):  # noqa: SLF001 - the writer lock serializes receipt ownership
        if _read(store) is not None:
            msg = f"a profile repair is already pending: {store.root / RECEIPT}; run setup again to publish it"
            raise StoreError(msg)
        receipt = Receipt(id=uuid.uuid4().hex, scope=scope(store), source=source, target=target, profile=prof)
        atomic_write(store.root / RECEIPT, receipt.model_dump_json())
    return receipt


def publish(store: Store, receipt: Receipt, *, resumed: bool) -> str:
    """Publish the staged replacement; a refused publication returns its notice and keeps the receipt, rebound to it."""
    basis = Basis(
        source=receipt.source,
        target=receipt.target,
        rebind=lambda target: _rebind(store, receipt.id, target),
    )
    try:
        notice = store.write_profile(receipt.profile, replace_unreadable=True, basis=basis)
    except TargetChangedError as exc:
        if resumed:  # the staged replacement stays visible; the owner decides whether to discard it
            msg = (
                f"{exc} The staged replacement is kept in {store.root / RECEIPT}; "
                "remove that file to discard it, then run setup again to review the current profile."
            )
            raise TargetChangedError(msg) from exc
        _drop(store, receipt.id)
        raise
    except SourceChangedError:
        _drop(store, receipt.id)  # the old bytes the owner confirmed are gone: nothing to publish
        raise
    if notice:
        return notice
    finish(store, receipt)
    return ""


def _rebind(store: Store, receipt_id: str, target: str) -> None:
    """Bind the receipt to the shared bytes now present, published or refused; the caller holds the writer lock."""
    current = _own(store, receipt_id)
    if current is not None and current.target != target:
        atomic_write(store.root / RECEIPT, current.model_copy(update={"target": target}).model_dump_json())


def finish(store: Store, receipt: Receipt) -> None:
    """Retire the old profile once its replacement is published, while it still has the confirmed bytes."""
    with profile_share._writer(store):  # noqa: SLF001 - the same writer lock the publication held
        if store.shared:
            if profile_share.config_digest(store.root / PROFILE) != receipt.source:
                msg = "the old profile changed after the replacement was published; run setup again to review it"
                raise SourceChangedError(msg)
            roles_move.retire_source(store)
        if _own(store, receipt.id) is not None:
            (store.root / RECEIPT).unlink(missing_ok=True)


def _drop(store: Store, receipt_id: str) -> None:
    """Drop the receipt only while it is still the one this operation staged; a newer receipt is left intact."""
    with profile_share._writer(store):  # noqa: SLF001 - the writer lock serializes receipt ownership
        if _own(store, receipt_id) is not None:
            (store.root / RECEIPT).unlink(missing_ok=True)
