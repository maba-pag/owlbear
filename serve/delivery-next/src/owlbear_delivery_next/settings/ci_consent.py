"""Pure matching of a shared project CI snapshot against current observations."""

from __future__ import annotations

import csv
import io
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.profile_record import ProjectCiConsent
from owlbear_delivery_next.settings import profile

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
    from owlbear_delivery_next.github.provider import Provider, Repository, Rules


def confirm_ci(
    prof: Profile, value: str, now: datetime, consent: ProjectCiConsent | None, names: tuple[str, ...]
) -> Profile:
    """Keep explicitly selected checks separate from approval of detected names."""
    confirmed = profile.confirm(prof, profile.DECLARED, value, now, consent=consent)
    entry = confirmed.entries[profile.DECLARED].model_copy(update={"ci_named": names, "ci_checks": parse_names(value)})
    return confirmed.model_copy(update={"entries": confirmed.entries | {profile.DECLARED: entry}})


def raw_names(entry: ProfileEntry) -> tuple[str, ...]:
    """Names actually read, including the readable part of an unknown inventory."""
    return (
        entry.ci_checks
        if entry.ci_checks is not None
        else tuple(n.strip() for n in entry.value.split(",") if n.strip() and n.strip() != "none")
    )


def parse_names(value: str) -> tuple[str, ...]:
    """A legacy comma list, or quoted CSV names containing commas."""
    if value.strip() in {"", "none"}:
        return ()
    rows = list(csv.reader(io.StringIO(value), skipinitialspace=True, strict=True))
    if len(rows) != 1:
        message = "CI names need one CSV record; quote names containing newlines"
        raise ValueError(message)
    return tuple(n if '"' in value else n.strip() for n in rows[0] if n.strip())


def format_names(names: tuple[str, ...]) -> str:
    """Readable CSV that does not confuse a literal check named none with an empty set."""
    fields = []
    for name in names:
        out = io.StringIO()
        quoting = csv.QUOTE_ALL if name == "none" or name != name.strip() else csv.QUOTE_MINIMAL
        csv.writer(out, quoting=quoting).writerow((name,))
        fields.append(out.getvalue().removesuffix("\r\n"))
    return ", ".join(fields) or "none"


def confirmation(prof: Profile, old: ProfileEntry, now: datetime, consent: ProjectCiConsent | None) -> ProjectCiConsent:
    """The supplied project approval, or an explicit replacement of the declaration confirmation."""
    return consent or ProjectCiConsent.revoked(
        repository=profile.value(prof, profile.REPO),
        target=old.ci_consent.target if old.ci_consent else profile.value(prof, profile.DEFAULT),
        at=now,
    )


def redetected(
    prof: Profile, entries: dict[str, ProfileEntry], repo: Repository, rules: Rules, gh: Provider
) -> ProfileEntry:
    """Recheck shared CI authority without discarding explicitly selected names."""
    old = prof.entries.get(profile.DECLARED)
    found = entries[profile.DECLARED]
    if not old or not old.ci_consent:
        return found
    consent = old.ci_consent
    target = rules if consent.target == repo.default_branch else gh.read_rules(repo.repository, consent.target)
    candidate = prof.model_copy(
        update={
            "entries": entries
            | {
                profile.DECLARED: old,
                profile.REQUIRED: profile.rule_entries(target)[profile.REQUIRED],
            }
        }
    )
    if project_ci(candidate, consent.target, found):
        return confirm_ci(
            prof.model_copy(update={"entries": entries}),
            old.value,
            consent.at,
            consent,
            old.ci_named,
        ).entries[profile.DECLARED]
    return found.model_copy(
        update={
            "ci_consent": consent,
            "ci_named": old.ci_named if consent.repository == repo.repository else (),
        }
    )


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
        and not raw_names(observed)
    )
