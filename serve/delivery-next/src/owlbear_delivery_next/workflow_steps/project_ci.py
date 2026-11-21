"""One displayed project-wide renewal when the target's required check names change."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.merge_records import CiBasis
from owlbear_delivery_next.change_contracts.models import Option
from owlbear_delivery_next.change_contracts.profile_record import ProjectCiConsent
from owlbear_delivery_next.change_flow import asking
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store.profile_errors import SharedSyncError, TargetChangedError
from owlbear_delivery_next.state_store.store import StoreError
from owlbear_delivery_next.workflow_steps import ci_basis, engine

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change, StepKind
    from owlbear_delivery_next.change_contracts.profile_record import ProfileEntry
    from owlbear_delivery_next.change_flow.loop import StepResult
    from owlbear_delivery_next.github.provider import Rules
    from owlbear_delivery_next.workflow_steps.engine import Ctx


def admit(
    ctx: Ctx, c: Change, observed: ProfileEntry, step: StepKind
) -> tuple[tuple[str, ...], StepResult | None] | None:
    """Acquire, recheck the actual target and publish matching empty-head authority before reusing it."""
    try:
        ctx.profile = ci_basis.acquire(ctx.store, ctx.lock, c, ctx.profile)
        return _reuse(ctx, c, observed, step)
    except (SharedSyncError, TargetChangedError) as exc:
        return (), engine.blocked("state:follow:profile", str(exc), failure(exc), ctx.now)


def _reuse(
    ctx: Ctx, c: Change, observed: ProfileEntry, step: StepKind
) -> tuple[tuple[str, ...], StepResult | None] | None:
    entry = ctx.profile.entries.get(profile.DECLARED)
    confirmed = profile.listed(entry) if entry and profile.is_confirmed(entry) else ()
    consent = entry.ci_consent if entry else None
    if consent and consent.basis and consent.repository == ctx.repository and consent.target == c.names.target:
        rules = ctx.gh.read_rules(ctx.repository, c.names.target)
        if rules.state != "known":
            return (), engine.blocked(
                f"gate:{step.value}:rules-unread",
                f"Delivery could not read the merge rules of {c.names.target} on GitHub",
                rules.evidence,
                ctx.now,
            )
        if consent.basis.required != tuple(sorted(set(rules.required_checks))):
            return (), renew(ctx, c, rules)
        ctx.profile = ctx.profile.model_copy(
            update={"entries": ctx.profile.entries | {profile.REQUIRED: profile.rule_entries(rules)[profile.REQUIRED]}}
        )
    if ci_basis.head_approved(c, ci_basis.current(ctx.profile, observed)):
        return tuple(dict.fromkeys((*confirmed, *(ci_basis.current(ctx.profile, observed).declared or ())))), None
    if not (consent and profile.project_ci(ctx.profile, c.names.target, observed) and ci_basis.compatible(c, consent)):
        return None
    raw = ctx.profile.model_copy(update={"entries": ctx.profile.entries | {profile.DECLARED: observed}})
    bound = (
        ctx.profile
        if profile.holds(entry, observed)
        else profile.confirm(raw, profile.DECLARED, ", ".join(confirmed) or "none", consent.at, consent=consent)
    )
    ctx.profile = ci_basis.save(ctx.store, ctx.lock, c, ctx.profile, bound)
    actual = ctx.profile.entries.get(profile.DECLARED)
    if not actual or not actual.ci_consent or not profile.project_ci(ctx.profile, c.names.target, observed):
        return admit(ctx, c, observed, step)
    return tuple(dict.fromkeys((*confirmed, *profile.listed(actual)))), None


def confirm_value(ctx: Ctx, c: Change, value: str) -> StepResult | None:
    """Keep exact-digest Change-local answers effective when their profile save fails visibly."""
    before = ctx.profile
    confirmed = profile.confirm(before, profile.DECLARED, value, ctx.now)
    try:
        ctx.profile = ci_basis.save(ctx.store, ctx.lock, c, before, confirmed)
    except (SharedSyncError, TargetChangedError) as exc:
        return engine.blocked("state:follow:profile", str(exc), failure(exc), ctx.now)
    except StoreError:
        ctx.profile = before
    else:
        ctx.log(c.slug, "profile-confirmed", key=profile.DECLARED, value=value)
    return None


def renew(ctx: Ctx, c: Change, rules: Rules) -> StepResult | None:
    """Renew only required-plus-started authority; unrelated branch rules keep their own explicit approval."""
    entry = ctx.profile.entries.get(profile.DECLARED)
    consent = entry.ci_consent if entry else None
    if not (
        consent
        and consent.basis
        and consent.basis.declared == ()
        and consent.basis.required is not None
        and consent.repository == ctx.repository
        and consent.target == c.names.target
    ):
        return None
    if rules.state != "known":
        return engine.blocked(
            "gate:follow:rules-unread",
            f"Delivery could not read the merge rules of {c.names.target} on GitHub",
            rules.evidence,
            ctx.now,
        )
    names = tuple(sorted(set(rules.required_checks)))
    if tuple(sorted(set(consent.basis.required))) == names:
        if profile.required_names(ctx.profile.entries.get(profile.REQUIRED)) != names:
            before = ctx.profile
            raw = before.model_copy(
                update={"entries": before.entries | {profile.REQUIRED: profile.rule_entries(rules)[profile.REQUIRED]}}
            )
            ctx.profile = profile.confirm(raw, profile.REQUIRED, ", ".join(names) or "none", consent.at)
            ctx.profile = ci_basis.save(ctx.store, ctx.lock, c, before, ctx.profile)
        return None
    texts = profile.workflow_texts_at(Path(c.names.worktree), "HEAD") if c.names.worktree else None
    observed = (
        profile.ci_entries({n: profile.workflow(t) for n, t in texts.items()}, profile.flows_digest(texts))[
            profile.DECLARED
        ]
        if texts is not None
        else None
    )
    detected = tuple(sorted(set(ci_basis.current(ctx.profile, observed).declared or ()))) if observed else ()
    basis = CiBasis(declared=detected or None, required=names)
    shown = hashlib.sha256(json.dumps([ctx.repository, c.names.target, basis.model_dump()]).encode()).hexdigest()[:12]
    cause = f"gate:{c.step.kind.value}:rules-ci-{shown}"
    agreed = next(
        (
            q
            for q in reversed(c.questions)
            if q.cause == cause
            and q.answer
            and q.answer.option == "yes"
            and not q.answer.superseded_at
            and not q.effect_observed_at
        ),
        None,
    )
    if agreed:
        latest = ctx.store.read_profile()
        if latest is not None and latest.entries.get(profile.DECLARED) != entry:
            ctx.profile = latest
            return renew(ctx, c, rules)
        approved = ProjectCiConsent.approved(ctx.repository, c.names.target, agreed.answer.at, names)
        before = ctx.profile
        entries = before.entries | {profile.REQUIRED: profile.rule_entries(rules)[profile.REQUIRED]}
        if observed is not None:
            entries[profile.DECLARED] = observed
        named = tuple(dict.fromkeys((*(profile.listed(entry) if profile.is_confirmed(entry) else ()), *detected)))
        updated = profile.confirm(
            before.model_copy(update={"entries": entries}),
            profile.DECLARED,
            ", ".join(named) or "none",
            approved.at,
            consent=approved,
        )
        ctx.profile = ci_basis.save(ctx.store, ctx.lock, c, before, updated)
        agreed.effect_observed_at = ctx.now
        return None
    delta = ci_basis.required_delta(consent.basis.required, names)
    head = f" Also approve the detected head checks: {', '.join(detected)}." if detected else ""
    text = (
        f"{ctx.repository}/{c.names.target}: {delta} "
        "Merge on GitHub's required checks plus every check that starts on the pull request for all Changes "
        "of this project into this target until its required check names change?"
        f"{head} Existing confirmed named checks and pauses still hold."
    )
    result = engine.ask(
        c.step.kind,
        text,
        cause,
        [Option(id="yes", label="Yes: record them and go on", next=c.step.kind), engine.PAUSE],
        subject="reserved",
    )
    result.question.ci_basis = basis
    result.question.follows = asking.DECLARED.rstrip("-")
    return result
