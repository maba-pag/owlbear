"""A configured read-only project auditor and its accepted result."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import project_audit_tools, tools
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.runtimes import sdk_adapter, session_result
from owlbear_delivery_next.settings import roles
from owlbear_delivery_next.workflow_steps import sessions as step_sessions

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.state_store.store import Store


def auditor(
    store: Store,
    root: Path,
    audit: str,
    note: str,
    *,
    helper: Callable[[tools.Args], str],
) -> sdk_adapter.Session:
    """Construct one session, outside the audited repo so its instruction files are only data."""
    job = f"{audit}-audit"
    settings = store.settings()
    role = roles.chosen(settings, job)
    message = (
        f"Run the {audit} audit. Read the pinned repository in repo/ and all host planning authority in context/. "
        "Do not edit or publish. Submit findings with submit_result. Ask no questions.\n\n"
        f"Owner's note (verbatim):\n{note}"
    )
    return sdk_adapter.Session(
        kind=StepKind.REVIEW,
        worktree=root,
        session_id=f"{job}-{uuid.uuid4().hex}",
        message=message,
        fresh=message,
        resume=False,
        policy=Policy(root, write=False),
        observe=lambda: tools.Worktree("", ""),
        checks=(),
        submit=project_audit_tools.SUBMIT,
        model=role.model,
        effort=role.effort,
        context=role.context,
        limit=roles.limit(settings, job),
        subagents=roles.subagents(settings, job),
        user=roles.user_config(settings),
        role="project-auditor",
        job=job,
        memory=step_sessions.memory(store),
        helpers=((project_audit_tools.SET_TARGET, helper),),
    )


def accepted(done: session_result.Run, root: Path) -> project_audit_tools.AuditFindings:
    """Require termination, verified model and the real checked result contract before publication."""
    if not (done.termination and done.termination.confirmed):
        msg = f"the audit's processes are not confirmed gone: {session_result.unverified(done.termination)}"
        raise RuntimeError(msg)
    if done.model_check != "verified":
        msg = f"the audit's model is {done.model_check}: {done.usage_unread or done.detail}"
        raise RuntimeError(msg)
    if done.ending != "result" or not isinstance(done.payload, project_audit_tools.AuditFindings):
        msg = f"the audit ended with {done.ending}: {done.detail or done.payload or 'no result'}"
        raise RuntimeError(msg)
    if why := project_audit_tools.check(done.payload, root):
        raise ValueError("\n".join(why))
    return done.payload
