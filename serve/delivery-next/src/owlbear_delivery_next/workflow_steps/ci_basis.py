"""Approval of a CI inventory, independent of workflow churn when no names could be read (#1342)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from subprocess import TimeoutExpired
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.merge_records import CiBasis
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.profile_record import ProjectCiConsent
from owlbear_delivery_next.change_flow import asking, loop
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store.profile_errors import SharedSyncError, TargetChangedError
from owlbear_delivery_next.state_store.store import StoreError
from owlbear_delivery_next.workflow_steps import engine

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change, Question
    from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
    from owlbear_delivery_next.state_store.store import Lock, Store

LEGACY_NONE = "for those it could read: none it could read. Merge on that basis?"


def inventory(q: Question) -> bool:
    """Only Delivery's merge-inventory questions, not another question answered yes."""
    return (q.cause or "").startswith(asking.DECLARED)


def requirements(q: Question) -> bool:
    """The existing branch-rule proposals that can explicitly renew required names."""
    return (q.cause or "").startswith(("gate:publish:rules-", "gate:follow:rules-", "gate:merge:rules-"))


def latest(c: Change) -> Question | None:
    """The latest answered inventory question, including an answer that does not authorize reuse."""
    return next((q for q in reversed(c.questions) if inventory(q) and q.answer), None)


def detected(q: Question) -> tuple[str, ...] | None:
    """A saved observation, or the narrowly recognized empty observation in pre-snapshot questions."""
    if q.ci_basis is not None:
        return q.ci_basis.declared
    return () if inventory(q) and q.text.endswith(LEGACY_NONE) else None


def current(prof: Profile, entry: ProfileEntry) -> CiBasis:
    """Canonical observed names; a refreshed profile's raw facts are not owner consent."""
    required = prof.entries.get(profile.REQUIRED)
    return CiBasis(
        declared=tuple(sorted(n.strip() for n in entry.value.split(",") if n.strip() and n.strip() != "none")),
        required=(profile.required_names(required)),
    )


def _approval(c: Change) -> Question | None:
    return next(
        (
            q
            for q in reversed(c.questions)
            if q.ci_basis
            and ((inventory(q) and q.ci_basis.declared == ()) or _project_renewal(q))
            and q.answer
            and q.answer.option == "yes"
            and q.answer.superseded_at is None
        ),
        None,
    )


def _project_renewal(q: Question) -> bool:
    return bool(requirements(q) and ":rules-ci-" in (q.cause or "") and q.ci_basis and q.ci_basis.required is not None)


def effective(c: Change, prof: Profile) -> ProjectCiConsent | None:
    """The latest structured empty-inventory yes, with its later explicit requirements renewal."""
    q = _approval(c)
    if q is None:
        return None
    basis, at = q.ci_basis, q.answer.at
    for other in c.questions[c.questions.index(q) + 1 :]:
        if not (inventory(other) or requirements(other)) or not other.answer:
            continue
        if other.answer.option != "yes" or other.answer.superseded_at:
            return None
        if (
            requirements(other)
            and other.ci_basis
            and (other.ci_basis.declared is None or _project_renewal(other))
            and other.ci_basis.required is not None
        ):
            candidate = CiBasis(declared=(), required=tuple(sorted(set(other.ci_basis.required))))
            if required_approved(c, q, candidate, prof):
                basis, at = candidate, other.answer.at
    if basis.required is None:
        return None
    return ProjectCiConsent.approved(profile.value(prof, profile.REPO), c.names.target, at, basis.required)


def save(store: Store, lock: Lock, c: Change, old: Profile, new: Profile) -> Profile:
    """Publish normal profile intent and reload its actual shared winner; keep the whole failure diagnostic."""
    if old != new and store.shared and store.shared.pending():
        current = save(store, lock, c, old, old)
        if current != old:
            return current
    notice = ""
    try:
        notice = store.write_profile(new, previous=old)
    except (StoreError, SharedSyncError, TargetChangedError) as exc:
        notice = failure(exc)
        raise
    finally:
        if notice:
            store.log(
                lock,
                c.slug,
                {
                    "event": "profile-not-saved",
                    "key": profile.DECLARED,
                    "at": datetime.now(UTC).isoformat(),
                    "reason": notice,
                },
            )
    saved = store.read_profile()
    if saved is None:
        msg = "The project profile is absent after its save; run the step again from the current profile."
        raise StoreError(msg)
    return saved


def acquire(store: Store, lock: Lock, c: Change, prof: Profile) -> Profile:
    """Seed completed or active structured approvals without altering their historical questions."""
    prof = _stored_consent(store, prof)
    consent = effective(c, prof)
    entry = prof.entries.get(profile.DECLARED)
    if not consent or not entry or not consent.repository:
        return prof
    primary = _approval(c)
    if entry.ci_consent and entry.ci_consent.basis is None and primary.answer.at <= entry.ci_consent.at:
        return prof
    if entry.ci_consent and entry.ci_consent.at >= consent.at:
        return prof
    names = (
        *(profile.listed(entry) if profile.is_confirmed(entry) else ()),
        *((primary.ci_basis.declared or ()) if _project_renewal(primary) else ()),
    )
    value = ", ".join(dict.fromkeys(names)) or "none"
    confirmed = profile.confirm(prof, profile.DECLARED, value, consent.at, consent=consent)
    return save(store, lock, c, prof, confirmed)


def _stored_consent(store: Store, prof: Profile) -> Profile:
    current = store.read_profile()
    entry = current.entries.get(profile.DECLARED) if current else None
    old = prof.entries.get(profile.DECLARED)
    if entry and entry.ci_consent and (not old or not old.ci_consent or entry.ci_consent.at > old.ci_consent.at):
        return prof.model_copy(
            update={"entries": prof.entries | {profile.DECLARED: entry}, "version": max(prof.version, current.version)}
        )
    return prof


def compatible(c: Change, consent: ProjectCiConsent) -> bool:
    """Project consent never overrides a refusal or newer incompatible per-Change approval."""
    answered = _answers(c)
    if not answered:
        return True
    q = answered[-1]
    previous = latest(c)
    if previous and (previous.answer.option != "yes" or previous.answer.superseded_at):
        return False
    if q.answer.option != "yes" or q.answer.superseded_at:
        return False
    saved = q.ci_basis or q.ci_observation
    return bool(
        q.answer.at <= consent.at
        or (
            saved
            and saved.declared in {(), None}
            and saved.required is not None
            and tuple(sorted(set(saved.required))) == consent.basis.required
        )
    )


def head_approved(c: Change, basis: CiBasis) -> bool:
    """A rules renewal can also approve exactly the newly detected head names it displayed."""
    q = next(iter(reversed(_answers(c))), None)
    return bool(
        q and requirements(q) and q.ci_basis == basis and q.answer.option == "yes" and q.answer.superseded_at is None
    )


def _answers(c: Change) -> list[Question]:
    return [
        q
        for q in c.questions
        if q.answer
        and (
            inventory(q)
            or (requirements(q) and (q.ci_basis is not None or q.answer.option != "yes" or q.answer.superseded_at))
        )
    ]


def required_delta(before: tuple[str, ...] | None, after: tuple[str, ...] | None) -> str:
    """The readable required-name difference, independent of rule evidence and ordering."""
    was = ", ".join(before) or "none" if before is not None else "not readable"
    now = ", ".join(after) or "none" if after is not None else "not readable"
    parts = [f"Required checks were {was}; now {now}."]
    if before is not None and after is not None:
        added, removed = sorted(set(after) - set(before)), sorted(set(before) - set(after))
        if added:
            parts.append(f"Added: {', '.join(added)}.")
        if removed:
            parts.append(f"Removed: {', '.join(removed)}.")
    return " ".join(parts)


def project_delta(prof: Profile, c: Change, basis: CiBasis) -> str:
    """A shared empty baseline does not approve new head names or a different target."""
    entry = prof.entries.get(profile.DECLARED)
    consent = entry.ci_consent if entry else None
    if not consent or not consent.basis or consent.repository != profile.value(prof, profile.REPO):
        return ""
    q = latest(c)
    if q and q.ci_basis == basis and q.answer.option == "yes" and not q.answer.superseded_at:
        return ""
    if consent.target != c.names.target:
        return f"The project CI consent covers {consent.target}, not {c.names.target}."
    if basis.declared:
        return f"Detected checks changed from none to {', '.join(basis.declared)}."
    return required_delta(consent.basis.required, basis.required) if consent.basis.required != basis.required else ""


def named_after(c: Change, entry: ProfileEntry | None) -> tuple[str, ...]:
    """An explicit named replacement after this Change's yes remains an additional gate."""
    q = latest(c)
    consent = entry.ci_consent if entry else None
    return (
        profile.listed(entry)
        if q and consent and consent.basis is None and consent.at > q.answer.at and profile.is_confirmed(entry)
        else ()
    )


def required_approved(c: Change, q: Question, basis: CiBasis, prof: Profile) -> bool:
    """A matching inventory, or a later yes to the current requirements actually shown."""
    recorded = q.ci_basis or q.ci_observation
    if recorded is not None and recorded.required == basis.required:
        return True
    later = c.questions[c.questions.index(q) + 1 :]
    if any(
        other.ci_basis is not None
        and (other.ci_basis.declared is None or _project_renewal(other))
        and other.ci_basis.required == basis.required
        and (other.cause or "").startswith(("gate:publish:rules-", "gate:follow:rules-", "gate:merge:rules-"))
        and other.answer is not None
        and other.answer.option == "yes"
        and other.answer.superseded_at is None
        for other in later
    ):
        return True
    if recorded is not None:
        return False
    if asking.legacy_inventory(q) and basis.required is not None:
        earlier = c.questions[: c.questions.index(q)]
        previous = next(
            (
                saved
                for other in reversed(earlier)
                if (saved := other.ci_basis or other.ci_observation) is not None
                and saved.required is not None
                and other.answer is not None
                and other.answer.option == "yes"
                and other.answer.superseded_at is None
            ),
            None,
        )
        return previous is None or previous.required == basis.required
    required = prof.entries.get(profile.REQUIRED)
    return bool(required and required.observed and q.answer and prof.confirmed_at and prof.confirmed_at <= q.answer.at)


def covers(c: Change, q: Question | None, basis: CiBasis, prof: Profile) -> bool:
    """An empty-inventory yes covers workflow-only changes, never newly read names or a later refusal."""
    return bool(
        q is not None
        and q.answer is not None
        and q.answer.option == "yes"
        and q.answer.superseded_at is None
        and detected(q) == basis.declared == ()
        and required_approved(c, q, basis, prof)
    )


def retain(c: Change, q: Question | None, basis: CiBasis, prof: Profile) -> None:
    """Keep a current observation separately from the legacy proposal's historical evidence."""
    if q is not None and q.ci_basis is None and q.ci_observation is None and covers(c, q, basis, prof):
        q.ci_observation = basis


def delta(c: Change, q: Question | None, basis: CiBasis, prof: Profile, cause: str) -> str:
    """Name what needs new consent, independently of a workflow digest."""
    if q is None:
        return ""
    changes = []
    before = detected(q)
    if before is None and q.cause != cause and basis.declared:
        changes.append(f"The earlier answer did not record detected check names; now {', '.join(basis.declared)}.")
    elif before is not None and before != basis.declared:
        was, now = ", ".join(before) or "none", ", ".join(basis.declared or ()) or "none"
        changes.append(f"Detected checks changed from {was} to {now}.")
    if not required_approved(c, q, basis, prof):
        recorded = q.ci_basis or q.ci_observation
        if recorded is None:
            old = "not recorded with the earlier answer"
        else:
            old = ", ".join(recorded.required) or "none" if recorded.required is not None else "not readable"
        now = ", ".join(basis.required) or "none" if basis.required is not None else "not readable"
        changes.append(f"Required checks were {old}; now {now}.")
    return " ".join(changes)


def settle(store: Store, lock: Lock, c: Change, now: datetime) -> None:
    """Release only a redundant inventory hold; the runner still rereads GitHub and gates the actual head."""
    q = loop.open_question(c)
    if _approval(c) is None and (q is None or not (inventory(q) or requirements(q))):
        return
    prof = store.read_profile()
    if prof is None:
        return
    try:
        prof = acquire(store, lock, c, prof)
    except (SharedSyncError, TargetChangedError) as exc:
        raise StoreError(str(exc)) from exc
    if (
        q is None
        or not (inventory(q) or requirements(q))
        or c.step.kind not in {StepKind.PUBLISH, StepKind.FOLLOW, StepKind.MERGE}
        or c.stop
        or c.blocked
        or c.amending
        or c.queue
        or c.intent.paused_at
        or c.intent.abandoned_at
        or c.intent.hold
        or not c.names.worktree
    ):
        return
    try:
        texts = profile.workflow_texts_at(Path(c.names.worktree), "HEAD")
    except (OSError, TimeoutExpired) as exc:
        message = f"cannot read CI workflows at {c.names.worktree}: {failure(exc)}"
        store.log(lock, c.slug, {"event": "ci-inventory-unread", "at": now.isoformat(), "reason": message})
        raise StoreError(message) from exc
    if texts is None:
        return
    entries = profile.ci_entries({n: profile.workflow(t) for n, t in texts.items()}, profile.flows_digest(texts))
    entry = entries[profile.DECLARED]
    basis = current(prof, entry)
    previous = latest(c)
    pending = q.ci_basis or CiBasis(declared=detected(q), required=basis.required)
    saved_entry = prof.entries.get(profile.DECLARED)
    consent = saved_entry.ci_consent if saved_entry else None
    shared = bool(consent and profile.project_ci(prof, c.names.target, entry) and compatible(c, consent))
    covered = inventory(q) and pending == basis and covers(c, previous, basis, prof)
    shared_hold = shared and ((inventory(q) and pending.declared == ()) or engine.required_only(q, c.names.target))
    if covered or shared_hold:
        retain(c, previous, basis, prof)
        q.effect_observed_at, c.outcome = now, None
