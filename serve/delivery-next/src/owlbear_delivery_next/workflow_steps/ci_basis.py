"""Approval of a CI inventory, independent of workflow churn when no names could be read (#1342)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.merge_records import CiBasis
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_flow import asking, loop
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store.store import StoreError

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.change_contracts.models import Change, Question
    from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
    from owlbear_delivery_next.state_store.store import Store

LEGACY_NONE = "for those it could read: none it could read. Merge on that basis?"


def inventory(q: Question) -> bool:
    """Only Delivery's merge-inventory questions, not another question answered yes."""
    return (q.cause or "").startswith(asking.DECLARED)


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
        required=(
            tuple(sorted(profile.names(prof, profile.REQUIRED))) if required and required.state == "known" else None
        ),
    )


def required_approved(c: Change, q: Question, basis: CiBasis, prof: Profile) -> bool:
    """A matching inventory, or a later yes to the current requirements actually shown."""
    if q.ci_basis is not None and q.ci_basis.required == basis.required:
        return True
    later = c.questions[c.questions.index(q) + 1 :]
    if any(
        other.ci_basis is not None
        and other.ci_basis.declared is None
        and other.ci_basis.required == basis.required
        and (other.cause or "").startswith(("gate:publish:rules-", "gate:follow:rules-", "gate:merge:rules-"))
        and other.answer is not None
        and other.answer.option == "yes"
        and other.answer.superseded_at is None
        for other in later
    ):
        return True
    required = prof.entries.get(profile.REQUIRED)
    return bool(q.ci_basis is None and required and required.observed)


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
        if q.ci_basis is None:
            old = "not recorded with the earlier answer"
        else:
            old = ", ".join(q.ci_basis.required) or "none" if q.ci_basis.required is not None else "not readable"
        now = ", ".join(basis.required) or "none" if basis.required is not None else "not readable"
        changes.append(f"Required checks were {old}; now {now}.")
    return " ".join(changes)


def settle(store: Store, c: Change, now: datetime) -> None:
    """Release only a redundant inventory hold; the runner still rereads GitHub and gates the actual head."""
    q = loop.open_question(c)
    if (
        q is None
        or not inventory(q)
        or c.step.kind not in {StepKind.FOLLOW, StepKind.MERGE}
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
    prof = store.read_profile()
    try:
        texts = profile.workflow_texts_at(Path(c.names.worktree), "HEAD")
    except OSError as exc:
        message = f"cannot read CI workflows at {c.names.worktree}: {failure(exc)}"
        raise StoreError(message) from exc
    if prof is None or texts is None:
        return
    entries = profile.ci_entries({n: profile.workflow(t) for n, t in texts.items()}, profile.flows_digest(texts))
    entry = entries[profile.DECLARED]
    basis = current(prof, entry)
    previous = latest(c)
    pending = q.ci_basis or CiBasis(declared=detected(q), required=basis.required)
    if pending == basis and covers(c, previous, basis, prof):
        q.effect_observed_at, c.outcome = now, None
