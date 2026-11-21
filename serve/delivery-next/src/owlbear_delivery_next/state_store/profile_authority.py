"""Custody of DECLARED authority in the normal profile writer."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.local_system.data_repo import DataRepoError
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store.profile_errors import SharedSyncError, TargetChangedError

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.profile_record import Profile
    from owlbear_delivery_next.state_store.store import Store

ABSENT = "absent"


def config_digest(config: Path) -> str:
    """The digest of the project config's bytes, or ``absent``."""
    try:
        return hashlib.sha256(config.read_bytes()).hexdigest()
    except FileNotFoundError:
        return ABSENT


def sync(store: Store, notice: str = "") -> None:
    """Judge authority against current shared bytes; an unsuccessful pull leaves them unknown."""
    if not store.shared:
        return
    try:
        why = store.shared.pull()
    except (DataRepoError, OSError) as exc:
        why = failure(exc)
    if why:
        raise SharedSyncError("; ".join(part for part in (notice, why) if part))


def keep(prof: Profile, current: Profile | None, previous: Profile | None) -> Profile:
    """Reject stale authority updates; unrelated saves retain the current DECLARED entry."""
    offered = prof.entries.get(profile.DECLARED)
    before = previous.entries.get(profile.DECLARED) if previous else None
    saved = current.entries.get(profile.DECLARED) if current else None
    authority = offered.ci_consent if offered else None
    prior = before.ci_consent if before else None
    updating = previous is not None and authority != prior
    if updating and current is not None and saved != before:
        msg = (
            "The shared CI authority changed while you answered; nothing was saved. "
            "Run the step again from the current profile."
        )
        raise TargetChangedError(msg)
    if not updating and saved and saved.ci_consent and (previous is None or saved != before):
        return prof.model_copy(update={"entries": prof.entries | {profile.DECLARED: saved}})
    return prof
