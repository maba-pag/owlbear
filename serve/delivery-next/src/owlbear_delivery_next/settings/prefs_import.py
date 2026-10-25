"""The one-time carry of stored legacy profile preferences into the project layer (R15, FND-01).

Every usable value the profile holds is carried, whatever its evidence: a confirmed value, a default, or an allowed
choice. A project field the owner already set wins, and a field nothing sets is filled once. Nothing is carried into
Global.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.github.provider import MergeMethod
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.settings.config import Layer, Prefs

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry


def _owned(entry: ProfileEntry | None) -> str | None:
    """The stored legacy value for an entry, or None when it is absent or has no usable value."""
    if entry is None or entry.state != "known" or not entry.value:
        return None
    return entry.value


def _bool(value: str | None) -> bool | None:
    return {"yes": True, "no": False}.get(value or "")


def _int(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def _method(value: str | None) -> MergeMethod | None:
    try:
        return MergeMethod(value) if value is not None else None
    except ValueError:
        return None


def legacy_values(prof: Profile) -> Prefs:
    """The owner-confirmed legacy values that map onto a preference; anything unusable is left out."""
    get = {k: _owned(prof.entries.get(k)) for k in profile.SETTINGS}
    return Prefs(
        merge_method=_method(get[profile.METHOD]),
        delete_remote_branch=_bool(get[profile.DELETE]),
        ci_poll_seconds=_int(get[profile.POLL]),
        ci_start_window_seconds=_int(get[profile.WINDOW]),
        ask_before_merge=_bool(get[profile.ASK]),
    )


def plan(layer: Layer, prof: Profile) -> Layer:
    """Fill unset preferences from the legacy values once; an already imported layer is kept."""
    if layer.prefs_imported:
        return layer
    legacy = legacy_values(prof).model_dump(exclude_none=True)
    current = (layer.prefs or Prefs()).model_dump(exclude_none=True)
    merged = Prefs.model_validate(legacy | current)  # the layer's own values win
    return layer.model_copy(update={"prefs": merged, "prefs_imported": True})
