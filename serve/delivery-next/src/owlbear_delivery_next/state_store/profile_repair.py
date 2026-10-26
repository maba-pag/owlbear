"""The owner's confirmed repair of an unreadable old profile in a shared folder (R15).

The replacement is staged under a private receipt before it is published, so a refused publication stays pending and
is retried without a new confirmation. The old profile is retired only after a published replacement, and only while it
still has the bytes the owner confirmed.
"""

from __future__ import annotations

import contextlib
import dataclasses
import json
import os
import stat
import uuid
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from owlbear_delivery_next.change_contracts.profile_record import PROFILE_FORMAT, Profile
from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.local_system.storage_io import atomic_write, open_lock
from owlbear_delivery_next.settings import migrations
from owlbear_delivery_next.state_store import profile_share, roles_move
from owlbear_delivery_next.state_store.profile_errors import (
    Basis,
    OldProfileUnreadableError,
    SharedSyncError,
    SourceChangedError,
    TargetChangedError,
)
from owlbear_delivery_next.state_store.profile_share import PROFILE, _present

if TYPE_CHECKING:
    from collections.abc import Iterator
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

    format: Literal[1]  # the receipt's own wire version: required, so an unversioned receipt is never assumed current
    id: str = Field(pattern=r"^[0-9a-f]{32}$")
    scope: str = Field(min_length=1)  # the logical shared repository and project folder, or ``local``
    source: str = Field(pattern=r"^(absent|[0-9a-f]{64})$")  # the old unreadable clone profile's digest, or absent
    target: str = Field(pattern=r"^(absent|[0-9a-f]{64})$")  # the shared profile's digest the owner confirmed against
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


RECEIPT_LIMIT = 1 << 20  # a replacement profile is a few kilobytes; more is not a receipt


def _read_regular(fd: int, receipt: Path) -> bytes:
    """The receipt's bytes from an open descriptor; a FIFO, directory or unreadable file is refused, not waited on."""
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports this module

    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            msg = f"the pending profile repair is not a regular file: {receipt}; remove it, then run setup again"
            raise StoreError(msg)
        chunks: list[bytes] = []
        size = 0
        while size <= RECEIPT_LIMIT:
            chunk = os.read(fd, RECEIPT_LIMIT + 1 - size)
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
    except OSError as exc:
        msg = f"the pending profile repair cannot be read: {receipt}; check or remove the file, then run setup again"
        raise StoreError(msg) from exc
    return b"".join(chunks)


def _read(store: Store) -> Receipt | None:
    """The pending receipt, validated: malformed, future or unconfirmed evidence is refused, never replayed."""
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports this module

    receipt = store.root / RECEIPT
    try:
        fd = os.open(receipt, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    except OSError as exc:
        msg = f"the pending profile repair cannot be read: {receipt}; check or remove the file, then run setup again"
        raise StoreError(msg) from exc
    try:
        raw = _read_regular(fd, receipt)
    finally:
        os.close(fd)
    if len(raw) > RECEIPT_LIMIT:
        msg = f"the pending profile repair is too large to be a receipt: {receipt}; remove it, then run setup again"
        raise StoreError(msg)
    return _receipt(raw, receipt)


def _receipt(raw: bytes, receipt: Path) -> Receipt:
    """The receipt as written: its profile migrates forward like a saved profile, then the receipt is checked."""
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports this module

    try:
        data = json.loads(raw)
        if isinstance(data, dict) and isinstance(data.get("profile"), dict):
            data["profile"] = _embedded(data["profile"])
        return Receipt.model_validate(data)
    except (ValueError, StoreError) as exc:  # a ValidationError is a ValueError; a refused profile is a StoreError
        msg = (
            f"the pending profile repair is malformed or from another version: {receipt}; "
            "remove it to confirm the replacement again"
        )
        raise StoreError(msg) from exc


def _embedded(raw: dict[str, Any]) -> Profile:
    """The profile a receipt embeds, read as a saved profile is: migrated forward; newer or malformed is refused."""
    from owlbear_delivery_next.state_store.store import _parse  # noqa: PLC0415 - circular at import time

    return _parse(json.dumps(raw), "the embedded profile", Profile, PROFILE_FORMAT, migrations.PROFILE)


@dataclasses.dataclass
class _Held:
    """The receipt an operation holds under the private receipt lock; a rebind moves its expected revision forward."""

    receipt: Receipt


@contextlib.contextmanager
def _receipt_lock(store: Store) -> Iterator[None]:
    """The private receipt lock, taken before the shared writer lock; every receipt operation serializes on it."""
    store.root.mkdir(parents=True, exist_ok=True)
    directory = os.open(store.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = open_lock(directory, blocking=True, name=".profile-repair.lock")
    finally:
        os.close(directory)
    try:
        yield
    finally:
        os.close(fd)


def _assert_held(store: Store, held: _Held) -> None:
    """The pending receipt is still exactly the one held, for this logical repository; anything else is refused."""
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports this module

    current = _read(store)
    if current != held.receipt:
        msg = (
            f"the pending profile repair was replaced or removed while it was being published: {store.root / RECEIPT}; "
            "run setup again to review the current profile"
        )
        raise StoreError(msg)
    if current.scope != scope(store):
        msg = (
            f"the pending profile repair was staged for another shared repository or folder: {store.root / RECEIPT}; "
            "remove it to discard the staged replacement, then run setup again"
        )
        raise StoreError(msg)


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

    with _receipt_lock(store):
        if _read(store) is not None:
            msg = f"a profile repair is already pending: {store.root / RECEIPT}; run setup again to publish it"
            raise StoreError(msg)
        receipt = Receipt(format=1, id=uuid.uuid4().hex, scope=scope(store), source=source, target=target, profile=prof)
        atomic_write(store.root / RECEIPT, receipt.model_dump_json())
    return receipt


def publish(store: Store, receipt: Receipt, *, resumed: bool) -> str:
    """Publish the staged replacement; a refused publication returns its notice and keeps the receipt, rebound to it."""
    with _receipt_lock(store):
        held = _Held(receipt)
        basis = Basis(
            source=receipt.source,
            target=receipt.target,
            rebind=lambda target: _rebind(store, held, target),
            owned=lambda: _assert_held(store, held),
        )
        try:
            notice = store.write_profile(receipt.profile, replace_unreadable=True, basis=basis)
        except SharedSyncError as exc:  # nothing was decided about the shared bytes: the receipt is kept for a retry
            tail = f"The confirmed replacement is kept in {store.root / RECEIPT}; run setup again to publish it."
            raise SharedSyncError(exc.why, tail) from exc
        except TargetChangedError as exc:
            if resumed:  # the staged replacement stays visible; the owner decides whether to discard it
                msg = (
                    f"{exc} The staged replacement is kept in {store.root / RECEIPT}; "
                    "remove that file to discard it, then run setup again to review the current profile."
                )
                raise TargetChangedError(msg) from exc
            _drop(store, held)
            raise
        except SourceChangedError:
            _drop(store, held)  # the old bytes the owner confirmed are gone: nothing to publish
            raise
        if notice:
            return notice
        _finish(store, held)
    return ""


def _rebind(store: Store, held: _Held, target: str) -> None:
    """Bind the held receipt to the shared bytes now present; the expected revision is the one it was held at."""
    _assert_held(store, held)
    if held.receipt.target != target:
        held.receipt = held.receipt.model_copy(update={"target": target})
        atomic_write(store.root / RECEIPT, held.receipt.model_dump_json())


def _finish(store: Store, held: _Held) -> None:
    """Retire the old profile once its replacement is published, while it still has the confirmed bytes."""
    with profile_share._writer(store):  # noqa: SLF001 - the same writer lock the publication held
        _assert_held(store, held)  # a replaced receipt is not this publication's: its old source stays untouched
        if store.shared:
            _retire_old(store, held)
        (store.root / RECEIPT).unlink(missing_ok=True)


def _retire_old(store: Store, held: _Held) -> None:
    """Retire an uninspectable old profile from one observation of its bytes: the digest and the role eligibility."""
    digest, unreadable = roles_move.snapshot(store.root / PROFILE)
    if digest == "":
        msg = (
            f"could not read the old profile {store.root / PROFILE} to finish the repair; "
            "the approved repair is kept; run setup again"
        )
        raise OldProfileUnreadableError(msg)
    if digest != held.receipt.source:
        msg = "the old profile changed after the replacement was published; run setup again to review it"
        raise SourceChangedError(msg)
    if held.receipt.source != profile_share.ABSENT and unreadable is not None:
        roles_move.retire_source(store)  # only an uninspectable old profile; a readable one keeps its roles


def _drop(store: Store, held: _Held) -> None:
    """Drop the receipt only while it is still the one held; a newer receipt is left intact."""
    if _read(store) == held.receipt:
        (store.root / RECEIPT).unlink(missing_ok=True)
