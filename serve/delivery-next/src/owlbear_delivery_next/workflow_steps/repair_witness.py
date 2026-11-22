"""The commands that prove a stuck step's repair: its task's checks, and the installs that run before them (#1066)."""

from __future__ import annotations

import tomllib
from traceback import format_exception_only
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import check_hint
from owlbear_delivery_next.change_flow import curation_flow, rebuilds, worktree
from owlbear_delivery_next.settings import profile
from owlbear_delivery_next.workflow_steps import repair_copy
from owlbear_delivery_next.workflow_steps.repair_scope import in_scope

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.change_contracts.profile_record import Profile


def commands(change: Change, prof: Profile, source: Path) -> tuple[str, ...]:
    """The commands that must pass: the task's resolved checks, else the confirmed checks of the brief's packages."""
    try:
        return _resolved(change, prof, source)
    except (OSError, tomllib.TOMLDecodeError) as error:
        r = change.repairs.current
        if r is None:
            raise
        detail = "".join(format_exception_only(error)).strip()
        r.evidence += f"\nUnchanged runner ownership in {source}/serve/tools/pyproject.toml: {detail}"
        if change.tests is not None and r.task == curation_flow.CURATE:
            msg = f"cannot resolve the curator's unchanged measurement in {source}: {detail}"
            raise repair_copy.RepairError(msg) from error
        task = next((t for t in change.plan.tasks if t.id == r.task), None) if change.plan else None
        pairs = worktree.checks(profile.vouched(prof))
        selected = (
            check_hint.resolve(task.checks, pairs)
            if task and task.checks
            else [check_hint.qualified(p, c) for p, c in pairs if in_scope(change, p)]
        )
        target = worktree.git(
            source, "rev-parse", f"{worktree.tracking(source, change.names.target)}^{{commit}}"
        ).strip()
        base = task.base if task and task.base is not None else r.base
        return tuple(check_hint.task_command(command, base, target) for command in selected)


def _resolved(change: Change, prof: Profile, source: Path) -> tuple[str, ...]:
    tasks = change.plan.tasks if change.plan else []
    r = change.repairs.current
    task = next((t for t in tasks if r and t.id == r.task), None)
    if task:
        rebuilds.refresh(change, task)
    pairs = worktree.checks(profile.vouched(prof))
    if task and r is not None and (task.checks or (change.tests is not None and r.task == curation_flow.CURATE)):
        bound = task if task.base is not None else task.model_copy(update={"base": r.base})
        return tuple(worktree.build_checks(profile.vouched(prof), change, bound, source))
    selected = [check_hint.qualified(p, c) for p, c in pairs if in_scope(change, p)]
    if r is None or not worktree.owns_changed_runner(source):
        return tuple(selected)
    target = worktree.git(source, "rev-parse", f"{worktree.tracking(source, change.names.target)}^{{commit}}").strip()
    return tuple(check_hint.task_command(command, r.base, target) for command in selected)


def installs(change: Change, prof: Profile) -> tuple[str, ...]:
    """The confirmed install commands of the brief's packages, which run before the checks."""
    return tuple(check_hint.qualified(p, c) for p, c in worktree.installs(prof, change.brief.scope or ["."]))
