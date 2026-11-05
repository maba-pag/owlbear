"""Setup's profile steps, shared by ``owlbear setup`` and the Add project dialog: detect, confirm and save."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store import profile_repair, profile_share, roles_move
from owlbear_delivery_next.state_store.profile_errors import (
    OldProfileUnreadableError,
    SharedSyncError,
    SourceChangedError,
)
from owlbear_delivery_next.state_store.store import RoleSourceError, StoreError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.github.account import Writer
    from owlbear_delivery_next.state_store.store import Store

type Ask = Callable[[str], str]
type Saved = tuple[Profile | None, bool, str, str]


def recommendations(prof: Profile) -> list[str]:
    """Branch rules worth turning on for automatic merging; advice only, never blocking."""
    tips = {
        profile.STRICT: "turn on 'Require branches to be up to date before merging' for the target branch",
        profile.RESOLUTION: "turn on 'Require conversation resolution before merging' for the target branch",
    }
    return [tip for key, tip in tips.items() if profile.value(prof, key) == "no"]


def render(prof: Profile) -> str:
    """The profile grouped by known, unknown and unsupported, with evidence."""
    lines = [f"Project profile v{prof.version}"]
    for state in ("known", "unknown", "unsupported"):
        found = [(k, e) for k, e in sorted(prof.entries.items()) if e.state == state]
        lines += [f"  {state}:"] * bool(found)
        lines += [f"    {k} = {e.value!r} ({e.evidence})" for k, e in found]
    return "\n".join(lines)


def confirm(prof: Profile, ask: Ask, *, yes: bool) -> tuple[Profile, list[str]]:
    """Ask for unknown entries and record the owner's confirmation; ``--yes`` never confirms an unknown entry."""
    now = datetime.now(UTC)
    for key, e in sorted(prof.entries.items()):
        if (
            e.state == "unknown"
            and key not in profile.SETTINGS
            and not yes
            and (value := ask(f"{key} is unknown ({e.evidence}). Value you confirm: "))
        ):
            prof = profile.confirm(prof, key, value, now)
    unknown = [k for k, e in prof.entries.items() if e.state == "unknown" and k not in profile.SETTINGS]
    if not (yes or ask("Confirm this profile? [y/N] ").lower().startswith("y")):
        return prof.model_copy(update={"confirmed_at": None}), unknown
    return confirmed(prof, {}, by="--yes" if yes else "prompt"), unknown


def confirmed(prof: Profile, values: dict[str, str], *, by: str) -> Profile:
    """*prof* with the owner's *values* for unknown entries and his confirmation, recorded as given *by*."""
    now = datetime.now(UTC)
    for key, value in sorted(values.items()):
        prof = profile.confirm(prof, key, value, now)
    mark = ProfileEntry(state="known", value=by, evidence=f"owner confirmed {now:%Y-%m-%d}")
    entries = {**prof.entries, "setup:confirmed-by": mark}
    return prof.model_copy(update={"entries": entries, "confirmed_at": now, "version": prof.version + 1})


def saved(store: Store, say: Callable[[str], object]) -> Saved:
    """The saved profile setup may replace, as ``(prev, unreadable, source, target)``.

    *source* is the digest of this clone's old profile file when its role overrides cannot be inspected, or ``absent``
    when only the shared profile is unreadable; *target* is the digest of the shared profile it is confirmed against.
    Readability and those digests come from one observation of the same bytes, taken now, so a stale open-time error
    never offers a replacement for a file that reads. A readable profile is never replaced for its old roles.
    """
    reason: StoreError | None = None
    try:
        prev = store.read_profile()
    except StoreError as exc:  # setup replaces a profile it cannot read; confirming saves the new one
        prev, reason = None, exc
    digest, now = roles_move.snapshot(store.root / profile_share.PROFILE)
    # unshared: the shared profile is this same local file, so its target is the bytes just observed
    target, target_now = roles_move.snapshot(profile_share.path(store)) if store.shared else (digest, now)
    if now is None:
        if store.deferred_roles is not None:
            msg = "the old profile can be read now; run setup again to review it"
            raise StoreError(msg)
        if reason is None:
            return prev, False, "", ""
        if store.shared and digest == profile_share.ABSENT:  # the shared profile alone is unreadable
            return _shared_only(target, target_now, reason, say)
        if target_now is None:  # the destination reads now: the error came from elsewhere, so nothing is replaced
            why = failure(reason)
            msg = f"the saved profile could not be read ({why}) and reads now; nothing was replaced; run setup again"
            raise StoreError(msg)
        if not target:
            raise target_now
        _announce(reason, say)
        return None, True, digest, target
    if prev is not None or not digest:  # a readable shared profile with an unreadable clone file: open refuses it
        raise now
    if not target:  # the shared profile cannot be read to a digest: its own error is the explanation
        raise target_now or now
    _announce(reason or now, say)
    return None, True, digest, target


def _shared_only(
    target: str, target_now: RoleSourceError | None, reason: StoreError, say: Callable[[str], object]
) -> tuple[Profile | None, bool, str, str]:
    """The replacement of a shared profile that is unreadable while the clone has no profile to bind."""
    if target_now is None:  # it reads now: the new bytes were not what the owner was shown, so nothing is replaced
        if target == profile_share.ABSENT:
            raise reason
        why = failure(reason)
        msg = f"the shared profile could not be read ({why}) and can be read now; run setup again to review it"
        raise StoreError(msg)
    if not target:
        raise target_now
    _announce(reason, say)
    return None, True, profile_share.ABSENT, target


def _announce(cause: Exception, say: Callable[[str], object]) -> None:
    say(f"The saved profile cannot be read ({failure(cause)}); detecting a new one.")
    say(
        "Confirming replacement discards the unreadable profile, including any unrecoverable legacy role "
        "overrides; declining keeps it."
    )


def detect(repo: Path, prev: Profile | None, writer: Writer) -> Profile:
    """The profile detected in *repo*, starting from the saved one *prev*."""
    return profile.detect(repo, profile.provider(prev or Profile(), repo, writer), prev)


def keep(store: Store, prof: Profile, found: Saved, say: Callable[[str], object]) -> bool:
    """Save the confirmed *prof* over what ``saved`` found; False after saying why it was kept for the next setup."""
    _, unreadable, source, target = found
    if source:
        return publish_repair(store, profile_repair.stage(store, prof, source, target), say, resumed=False)
    store.write_profile(prof, replace_unreadable=unreadable)
    return True


def publish_repair(
    store: Store, receipt: profile_repair.Receipt, say: Callable[[str], object], *, resumed: bool
) -> bool:
    """Publish the owner's confirmed replacement of an unreadable old profile; False after saying why it did not."""
    try:
        notice = profile_repair.publish(store, receipt, resumed=resumed)
    except (SourceChangedError, SharedSyncError, OldProfileUnreadableError) as exc:
        say(str(exc))
        return False
    if notice:  # the replacement is staged and kept for the next setup: nothing is retired yet
        say(notice)
        say("The replacement is kept; run setup again to publish it.")
        return False
    return True
