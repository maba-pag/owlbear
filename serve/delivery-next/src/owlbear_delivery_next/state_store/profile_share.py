"""The confirmed project profile: kept in the project's shared folder, re-checked once in each clone (TD-147).

Without a shared repository it stays in the clone's store. A clone's own profile moves to the shared folder once; the
old file stays as the recovery copy. A clone that found its profile in the shared folder detects its facts once at its
first host start, so confirmations that still hold carry over. Push permission, hooks and install facts stay in this
clone's overlay; another clone's shared copy of those facts never counts.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.profile_record import PROFILE_FORMAT, Profile
from owlbear_delivery_next.design_packs.detector import DetectorError
from owlbear_delivery_next.github.provider import ProviderError
from owlbear_delivery_next.local_system.data_repo import DataRepoError
from owlbear_delivery_next.local_system.storage_io import atomic_write, open_lock
from owlbear_delivery_next.settings import migrations, profile
from owlbear_delivery_next.state_store.pending_intents import (
    pending_file as _pending_file,
)
from owlbear_delivery_next.state_store.pending_intents import (
    pending_intents,
)
from owlbear_delivery_next.state_store.pending_intents import (
    shared_pending as _shared_pending,
)
from owlbear_delivery_next.state_store.profile_errors import (
    Basis,
    SharedSyncError,
    SourceChangedError,
    TargetChangedError,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.profile_record import ProfileEntry
    from owlbear_delivery_next.local_system.data_repo import DataRepo
    from owlbear_delivery_next.state_store.store import Store

PROFILE = "profile.json"
LOCAL = "profile.local.json"
DETECTED = "profile.detected"  # a new marker forces the old unbound observations to be checked once
ROLES_MOVED = "roles-moved"  # marks that a format-1 profile's role overrides were merged into the settings
UNPUBLISHED = "prefs-import.unpublished"  # the legacy import is done here but its completion was not published yet
ABSENT = "absent"
CONFIG_WAITING = "the project settings change is not published yet; the legacy preference import completes after it"


def path(store: Store) -> Path:
    """Where the project's profile is: in its shared folder, else in the clone's store."""
    return store.shared.root / store.name / PROFILE if store.shared else store.root / PROFILE


def write(store: Store, prof: Profile, *, replace_unreadable: bool = False, basis: Basis | None = None) -> str:
    """Write the profile; in the shared folder also commit and push it: what the owner should know, else nothing.

    An ordinary save refuses an unreadable saved profile; only the explicit repair (*replace_unreadable*) replaces
    it, and only while the old profile and the shared profile still have the digests in *basis* (under the lock).
    """
    with _writer(store):
        if basis and basis.owned:
            basis.owned()  # a newer or missing replacement is refused before anything is pulled or written
        # the target is judged against the remote's current bytes, not a stale clone; a failed sync says nothing of them
        if basis and store.shared:
            try:
                why = store.shared.pull()
            except (DataRepoError, OSError) as exc:
                why = str(exc) or type(exc).__name__
            if why:
                raise SharedSyncError(why)
        if basis and basis.source and config_digest(store.root / PROFILE) != basis.source:
            msg = "The old profile changed while you answered; nothing was saved. Run setup again to review it."
            raise SourceChangedError(msg)
        if basis and basis.target and config_digest(path(store)) != basis.target:
            msg = "The shared profile changed while you answered; nothing was saved. Run setup again to review it."
            raise TargetChangedError(msg)
        try:
            current = _current_for_write(store, replace_unreadable=replace_unreadable)
            if current is not None:  # only mark() moves the legacy import marker; a snapshot never rewinds it
                prof = prof.model_copy(
                    update={
                        "prefs_import": current.prefs_import,
                        "prefs_basis": current.prefs_basis,
                        "prefs_claim": current.prefs_claim,
                    }
                )
            _keep_local(store, prof)
            return _publish_locked(store, prof, f"settings: {store.name}: project profile")
        finally:
            if basis and basis.rebind and store.shared:
                basis.rebind(config_digest(path(store)))


def _publish_locked(store: Store, prof: Profile, message: str) -> str:
    """Publish a profile under the shared lock; DONE goes out only after the config's edit or removal.

    A refused config publication keeps the new facts staged and the completion pending here; a raised refusal of the
    profile is recorded the same way before it propagates.
    """
    done = prof.prefs_import == "done"
    if done:
        _unpublished(store, failed=True)  # the retry flag is durable before DONE is staged; if it cannot be, nothing is
        notice = publish_config_unlocked(store)
        if notice or _shared_pending(store):
            _stage(store, prof)
            return notice or CONFIG_WAITING
    notice = _publish(store, store.shared, prof, message)
    if done:
        _unpublished(store, failed=bool(notice))  # a raised publication leaves the flag set, as a refused one does
    return notice


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def config_digest(config: Path) -> str:
    """The digest of the project config's bytes, or ``absent``."""
    try:
        return _digest(config.read_bytes())
    except FileNotFoundError:
        return ABSENT


def held_by_pending(store: Store, data: bytes) -> bool:
    """Whether an automatic config write of *data* would replace another clone's different pending intent."""
    digest = _digest(data)
    return any(pending != digest for pending in pending_intents(store))


def publish_config_unlocked(store: Store) -> str:
    """Publish the project config as it is now: an edit, or its removal; the caller holds the shared lock.

    Every completed import publishes it first, whichever clone writes the marker. A DONE never reaches the shared
    profile while another clone's config change is unpublished: the shared pending record decides, not one clone's flag.
    A different config than the pending intent waits unpublished, so a stale local value or removal never goes out.
    """
    if not store.shared:
        return ""
    try:
        intents = pending_intents(store)
    except DataRepoError:
        return CONFIG_WAITING  # the shared record cannot be read, so the config is not published
    current = config_digest(store.config_path)
    if any(pending != current for pending in intents):
        return CONFIG_WAITING
    try:
        notice = store.shared.publish(
            store.config_path,
            f"settings: {store.name}: {'project layer' if store.config_path.exists() else 'project layer removed'}",
        )
    except DataRepoError as exc:
        notice = str(exc)
    return settle_config(store, notice)


def settle_config(store: Store, notice: str, *, owner: bool = False) -> str:
    """Record in the shared repository whether this clone's project config change reached it.

    The caller holds the shared lock and has just attempted the config's publication; *notice* is its refusal, if any.
    A refused change is recorded by its digest, and only the publication of the same bytes clears it, unless an *owner*
    save (its revision validated under the lock) published: that supersedes any earlier pending digest. An automatic
    refusal never replaces a different pending digest. The record is a file of its own, so recording a refused change
    never publishes the profile's unpublished completion.
    """
    if not store.shared:
        return notice
    digest = config_digest(store.config_path)
    pending = _shared_pending(store)
    if notice:
        if pending and pending != digest and not owner:
            return notice  # an automatic refusal never replaces another clone's or an owner's pending intent
        want = digest
    elif pending == digest or owner:
        want = ""
    else:
        return notice
    if want == pending:
        return notice
    target = _pending_file(store)
    if want:
        target.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(target, want)
    else:
        target.unlink(missing_ok=True)
    try:
        extra = store.shared.publish(
            target, f"settings: {store.name}: project config {'pending' if want else 'published'}"
        )
    except DataRepoError as exc:
        extra = str(exc)
    return "; ".join(dict.fromkeys(part for part in (notice, extra) if part))


def publish_layer(store: Store, path: Path, message: str, until: float, *, owner: bool = False) -> str:
    """Publish a changed settings layer under the held lock.

    A raised project config refusal is recorded as pending before it propagates, as a returned refusal is, so another
    clone cannot publish a completed import over it. The raised error is re-raised with that record in its message.
    """
    from owlbear_delivery_next.state_store.store import SharedError  # noqa: PLC0415 - the store imports this module

    try:
        notice = store.shared.publish(path, message, until)
    except DataRepoError as exc:
        if path != store.config_path:
            raise
        raise SharedError(settle_config(store, str(exc), owner=owner)) from exc
    return settle_config(store, notice, owner=owner) if path == store.config_path else notice


def mark(store: Store, expect: str, to: str, basis: str = "", claim: str = "") -> tuple[str, str, bool]:
    """Move the legacy import marker from *expect* to *to*; returns (state after, notice, applied).

    *applied* is False when the marker was not at *expect*. A pending claim records its *basis* and *claim* nonce;
    for a claim, *applied* is True only when the published, freshly read profile carries this nonce.
    """
    with _writer(store):
        prof = _read_unlocked(store)
        if prof is None or prof.prefs_import != expect:
            return (prof.prefs_import if prof else "", "", False)
        if to == "pending":
            marked = prof.model_copy(update={"prefs_import": to, "prefs_basis": basis, "prefs_claim": claim})
        else:
            marked = prof.model_copy(update={"prefs_import": to, "prefs_basis": ""})
        _keep_local(store, marked)
        claimed = to == "pending"
        notice = _publish_mark(store, marked, f"settings: {store.name}: legacy preference import {to}", claimed=claimed)
        return to, notice, not claimed or _settle_claim(store, notice, claim)


UNCONFIRMED = "prefs-claim.unconfirmed"


def _settle_claim(store: Store, notice: str, claim: str) -> bool:
    flag = store.root / UNCONFIRMED
    if notice:
        store.root.mkdir(parents=True, exist_ok=True)
        flag.write_text(claim)
        return False
    flag.unlink(missing_ok=True)
    prof = _read_unlocked(store)
    return prof is not None and prof.prefs_import == "pending" and prof.prefs_claim == claim


def _publish_mark(store: Store, prof: Profile, message: str, *, claimed: bool) -> str:
    from owlbear_delivery_next.state_store.store import SharedError  # noqa: PLC0415 - the store imports this module

    try:
        return _publish_locked(store, prof, message)
    except DataRepoError as exc:
        if claimed:
            _settle_claim(store, str(exc), prof.prefs_claim or "")
        raise SharedError(str(exc)) from exc


def claim_unconfirmed(store: Store, prof: Profile) -> bool:
    """Whether this pending claim was never confirmed as published, so it must be published again before a fill."""
    flag = store.root / UNCONFIRMED
    return prof.prefs_import == "pending" and flag.exists() and flag.read_text() == prof.prefs_claim


def confirm_claim(store: Store) -> tuple[str, bool]:
    """Publish an unconfirmed pending claim again; returns (publication notice, whether it won)."""
    with _writer(store):
        prof = _read_unlocked(store)
        if prof is None or not claim_unconfirmed(store, prof):
            return "", False
        notice = _publish_mark(store, prof, f"settings: {store.name}: legacy preference import pending", claimed=True)
        return notice, _settle_claim(store, notice, prof.prefs_claim or "")


def unpublished(store: Store) -> bool:
    """Whether a completed legacy import is marked done here but its publication was refused, so it still needs one."""
    return (store.root / UNPUBLISHED).exists()


def _unpublished(store: Store, *, failed: bool) -> None:
    flag = store.root / UNPUBLISHED
    if failed:
        store.root.mkdir(parents=True, exist_ok=True)
        flag.touch()
    else:
        flag.unlink(missing_ok=True)


def retry(store: Store) -> str:
    """Publish the current completed marker again after a refusal; the publication notice when it is still refused."""
    if not unpublished(store):
        return ""
    with _writer(store):
        prof = _read_unlocked(store)
        if prof is None or prof.prefs_import != "done":
            _unpublished(store, failed=False)
            return ""
        try:
            return _publish_locked(store, prof, f"settings: {store.name}: legacy preference import done")
        except DataRepoError as exc:
            return str(exc)


@contextlib.contextmanager
def _writer(store: Store, *, create: bool = True, shared: bool = True) -> Iterator[None]:
    if store.shared and shared:
        with store.shared.locked():
            yield
        return
    if create:
        store.root.mkdir(parents=True, exist_ok=True)
    directory = os.open(store.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = open_lock(directory, blocking=True, name=".profile.lock")
    finally:
        os.close(directory)
    try:
        yield
    finally:
        os.close(fd)


def read(store: Store) -> Profile | None:
    """Read both profile halves under their writer lock; absence alone returns None."""
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports this module

    if not _present(path(store)):
        return None
    try:
        with _writer(store, create=False):
            return _read_unlocked(store)
    except FileNotFoundError:
        return None
    except (DataRepoError, OSError, ValueError) as exc:
        msg = f"the profile could not be read: {exc}"
        raise StoreError(msg) from exc


def _read_unlocked(store: Store) -> Profile | None:
    """The coherent reader for a caller already holding the profile's writer lock."""
    source = path(store)
    return merged(store, _read(source)) if _present(source) else None


def _current_for_write(store: Store, *, replace_unreadable: bool) -> Profile | None:
    """The saved profile whose legacy guard an ordinary save keeps, or, for the explicit repair, only that guard."""
    from owlbear_delivery_next.state_store.profile_repair import unreadable_guard  # noqa: PLC0415 - circular
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports this module

    if not replace_unreadable:
        return _read_unlocked(store)
    try:  # an absent shared target keeps the clone's own valid legacy guard, a malformed one refuses
        current = _read_unlocked(store)
    except StoreError:
        return unreadable_guard(path(store))
    return current or (unreadable_guard(store.root / PROFILE) if store.shared else None)


def _present(source: Path) -> bool:
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports this module

    try:
        source.stat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        msg = f"the profile is unreadable: {source}"
        raise StoreError(msg) from exc
    return True


def merged(store: Store, prof: Profile) -> Profile:
    """Only this clone's own local source or overlay supplies its detected capabilities."""
    base = profile.shared_entries(prof.entries) if store.shared else prof.entries
    return prof.model_copy(update={"entries": {**base, **_local(store)}})


def _shared_part(prof: Profile) -> Profile:
    return prof.model_copy(update={"entries": profile.shared_entries(prof.entries)})


def _local_part(prof: Profile) -> dict[str, ProfileEntry]:
    return {key: entry for key, entry in prof.entries.items() if profile.local_key(key)}


def _keep_local(store: Store, prof: Profile) -> None:
    local = _local_part(prof)
    store.root.mkdir(parents=True, exist_ok=True)
    overlay = store.root / LOCAL
    if local:
        atomic_write(overlay, Profile(entries=local).model_dump_json(indent=1))
    else:
        overlay.unlink(missing_ok=True)


def _read(source: Path) -> Profile:
    from owlbear_delivery_next.state_store.store import _load  # noqa: PLC0415 - the store imports this module

    return _load(source, Profile, PROFILE_FORMAT, migrations.PROFILE)


def _local(store: Store) -> dict[str, ProfileEntry]:
    from owlbear_delivery_next.state_store.store import StoreError, _parse  # noqa: PLC0415 - circular at import time

    overlay = store.root / LOCAL
    try:
        fd = os.open(overlay, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return {}
    except OSError as exc:
        msg = f"this clone's profile facts are unreadable: {overlay}"
        raise StoreError(msg) from exc
    try:
        with os.fdopen(fd, encoding="utf-8") as source:
            local = _parse(source.read(), "profile.local", Profile, PROFILE_FORMAT, migrations.PROFILE)
    except (OSError, UnicodeError) as exc:
        msg = f"this clone's profile facts are unreadable: {overlay}"
        raise StoreError(msg) from exc
    if any(not profile.local_key(key) for key in local.entries):
        msg = "the clone's profile overlay contains non-local facts"
        raise StoreError(msg)
    return local.entries


def _stage(store: Store, prof: Profile) -> Path:
    target = path(store)
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(target, _shared_part(prof).model_dump_json(indent=1))
    return target


def _publish(store: Store, shared: DataRepo | None, prof: Profile, message: str) -> str:
    target = _stage(store, prof)
    return shared.publish(target, message) if shared else ""


def adopt(store: Store) -> None:
    """Move the clone's own profile to the project's shared folder once, after its roles moved; the old file stays."""
    local = store.root / PROFILE
    if not store.shared or not local.exists() or path(store).exists() or not (store.root / ROLES_MOVED).exists():
        return
    with store.shared.locked():
        if path(store).exists():  # another clone moved its profile while this one waited
            return
        path(store).parent.mkdir(parents=True, exist_ok=True)
        own = _read(local)
        own = own.model_copy(update={"entries": {**own.entries, **_local(store)}})
        _keep_local(store, own)
        _publish_locked(store, own, f"settings: {store.name}: project profile moved from its clone")
        local.replace(local.with_name(f"{PROFILE}.moved"))


def checked(store: Store, repo: Path) -> Profile | None:
    """Observe shared or unbound legacy facts once in this clone; only a saved success gets its marker."""
    from owlbear_delivery_next.state_store.store import StoreError  # noqa: PLC0415 - the store imports this module

    prof, mark, shared = store.read_profile(), store.root / DETECTED, store.shared
    if prof is None or mark.exists():
        return prof
    if shared is None and not profile.unbound(prof):
        return prof
    try:
        fresh = profile.detect(repo, profile.provider(prof, repo), prof)
    except DetectorError, ProviderError:
        return prof
    try:
        kept = _replaced(store, prof, fresh)
        if kept is None:
            return store.read_profile()  # a changed snapshot must be reconciled before detection is acknowledged
        fresh = kept
    except DataRepoError as exc:
        msg = f"the detected profile could not be published: {exc}"
        raise StoreError(msg) from exc
    atomic_write(mark, f"profile v{fresh.version} detected in this clone\n")
    return fresh


def _replaced(store: Store, old: Profile, new: Profile) -> Profile | None:
    """Keep concurrent local intent; publish fresh shared facts only against the snapshot they observed."""
    with _writer(store):
        current = _read_unlocked(store)
        before, now = _local_part(old), _local_part(current) if current is not None else _local(store)
        found = _local_part(new)
        local: dict[str, ProfileEntry] = {}
        for key in sorted(before.keys() | now.keys() | found.keys()):
            entry = now.get(key) if now.get(key) != before.get(key) else found.get(key)
            if entry is not None:
                local[key] = entry
        kept = new.model_copy(update={"entries": {**profile.shared_entries(new.entries), **local}})
        _keep_local(store, kept)
        if current is None or _shared_part(current) != _shared_part(old):
            return None
        notice = _publish_locked(store, kept, f"settings: {store.name}: project profile detected in a clone")
        if notice:
            raise DataRepoError(notice)
    return None if now != before else kept
