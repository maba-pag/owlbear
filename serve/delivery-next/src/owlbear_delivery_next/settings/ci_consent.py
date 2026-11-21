"""Pure matching of a shared project CI snapshot against current observations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.settings import profile

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry


def required_names(entry: ProfileEntry | None) -> tuple[str, ...] | None:
    """Canonical case-sensitive required names, with unreadable distinct from empty."""
    return tuple(sorted(set(profile.listed(entry)))) if entry and entry.state == "known" else None


def project_ci(prof: Profile, target: str, observed: ProfileEntry) -> bool:
    """Only readable matching requirements and an empty head inventory confer project reuse."""
    entry = prof.entries.get(profile.DECLARED)
    consent = entry.ci_consent if entry else None
    required = required_names(prof.entries.get(profile.REQUIRED))
    return bool(
        consent
        and consent.basis
        and consent.repository == profile.value(prof, profile.REPO)
        and consent.target == target
        and consent.basis.declared == ()
        and consent.basis.required is not None
        and tuple(sorted(set(consent.basis.required))) == required
        and observed.value.strip() in {"", "none"}
    )
