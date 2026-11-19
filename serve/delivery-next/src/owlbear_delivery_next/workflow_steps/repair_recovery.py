"""Refresh a recovered CI task's evidence before its fresh builder can consume an obsolete check log."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.change_flow.repair_recovery import pending_ci
from owlbear_delivery_next.git.remote_git import RemoteGitError
from owlbear_delivery_next.github.provider import ProviderError
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.state_store import github_writer
from owlbear_delivery_next.workflow_steps import engine, follow

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.state_store.store import Lock, Store


def _refresh(ctx: engine.Ctx, c: Change) -> tuple[Change, loop.StepResult | None]:
    r = pending_ci(c)
    if r is None:
        return c, None
    if c.names.pr is None:
        msg = f"{c.slug}: recovered CI task {r.task} has no pull request"
        raise ValueError(msg)
    pr = ctx.gh.read_pull_request(ctx.repository, c.names.pr)
    names, gate = follow.declared(ctx, c, pr, c.step.kind)
    if gate:
        return c, gate
    state = follow.ci(ctx, pr, names)
    c = follow.episode(ctx, c, pr.head_sha, state)
    if state.missing:
        return follow.missing(ctx, c, pr, state)
    if state.running:
        return c, follow.waiting(state, ctx)
    task = next(t for t in c.plan.tasks if t.id == r.task) if c.plan else None
    if task is None:
        msg = f"{c.slug}: recovered CI task {r.task} is missing from the plan"
        raise ValueError(msg)
    if state.failed:
        fix = follow.fix_ci(ctx, c, state, c.step.kind).fix_task
        if fix is None:
            msg = f"{c.slug}: CI failure produced no fix task"
            raise ValueError(msg)
        task.title, task.detail = fix.title, fix.detail
    else:
        task.detail = (
            f"CI checks now pass at PR #{pr.number}, head {pr.head_sha}. "
            "The cancelled-run evidence was superseded. Verify the task against the current head."
        )
    r.refreshed_at = ctx.now
    return c, None


def ready(store: Store, lock: Lock, c: Change, repo: Path) -> Change | None:
    """The refreshed Change, or None after durably recording its engine-owned wait or failure."""
    if pending_ci(c) is None:
        return c
    now = datetime.now(UTC)
    prof = store.read_profile() or Profile()
    writer = github_writer.of(store, repo)
    ctx = engine.Ctx(store, lock, repo, prof, profile.provider(prof, repo, writer), now, writer)
    try:
        c, result = _refresh(ctx, c)
    except (ProviderError, RemoteGitError) as exc:
        result = engine.failed(c, exc, now)
    store.write(lock, loop.apply(c, result, now) if result else c)
    return None if result else c
