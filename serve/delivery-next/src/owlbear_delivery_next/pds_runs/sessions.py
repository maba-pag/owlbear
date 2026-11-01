"""The PDS run's session configs (#777): the auditor's, which reads a copy of the pages and submits its reports."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import audit_tools, tools
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.settings import roles

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.settings.config import Settings

AUDIT = "pds-audit"  # the auditor's job, its settings label and its skills' (preload.JOBS)


def auditor(  # noqa: PLR0913 - the copy, its skills and the run's records
    settings: Settings,
    at: Path,
    skills: Path,
    message: str,
    *,
    memory: Path | None = None,
    journal: sdk_adapter.Journal | None = None,
) -> sdk_adapter.Session:
    """The auditor's session on the copy at *at*: confined, writing nothing, its audit skill preloaded from *skills*.

    Raises:
        SettingsUnset: The auditor's settings or the user-config switches are unset; no session starts.
    """
    role = roles.chosen(settings, AUDIT)
    return sdk_adapter.Session(
        kind=StepKind.REVIEW, worktree=at, session_id=f"{AUDIT}-{uuid.uuid4().hex[:8]}", message=message,
        fresh=message, resume=False, policy=Policy(at, write=False, confined=True),
        observe=lambda: tools.Worktree("", ""), checks=(), submit=audit_tools.SUBMIT, skills=skills,
        model=role.model, effort=role.effort, context=role.context, limit=roles.limit(settings, AUDIT),
        subagents=roles.subagents(settings, AUDIT), user=roles.user_config(settings), role=tools.AUDITOR, job=AUDIT,
        journal=journal or sdk_adapter.Journal(), memory=memory,
    )  # fmt: skip
