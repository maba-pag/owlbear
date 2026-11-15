"""The project auditor's report and session-bound target request."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import Field

from owlbear_delivery_next.change_contracts import tools

if TYPE_CHECKING:
    from pathlib import Path


class AuditFinding(tools.Args):
    """One evidence-backed observation, published by the host, never by the auditor."""

    title: str = tools.bounded(200, "Finding title, 1-200 characters", "Setup names a removed command")
    type: Literal["defect", "improvement", "idea", "question"] = Field(
        description="One Backlog finding class: defect, improvement, idea or question", examples=["defect"]
    )
    severity: Literal["high", "medium", "low"] = Field(
        description="One severity: high, medium or low", examples=["medium"]
    )
    where: str = tools.bounded(500, "Paths and lines, 1-500 characters", "setup/setup-guide.md:42")
    evidence: str = tools.bounded(
        1400, "Exact evidence and its consequence, 1-1400 characters", "'owlbear old' is absent from cli.py."
    )
    recommendation: str = tools.bounded(
        1000, "Recommended correction, not an edit, 1-1000 characters", "Document the current setup command."
    )


class ChangedDefault(tools.Args):
    """A default the owner's note changed for this run."""

    default: str = tools.bounded(200, "Default's name, 1-200 characters", "scope")
    to: str = tools.bounded(500, "Value requested in the note, 1-500 characters", "Only setup/")
    reason: str = tools.bounded(500, "Why the note changes it, 1-500 characters", "The note limits the audit to setup.")


class AuditFindings(tools.Args):
    """``submit_result`` for a documentation or agent audit."""

    findings: list[AuditFinding] = tools.bounded(60, "Up to 60 findings; empty is valid", [], least=0)
    parts: list[str] = Field(
        default_factory=list,
        max_length=0,
        description="Empty list for documentation and agent audits; no lens parts run",
        examples=[[]],
    )
    not_covered: list[Annotated[str, Field(min_length=1, max_length=2000)]] = tools.bounded(
        60, "Up to 60 coverage limits, each 1-2000 characters", ["External links could not be reached."], least=0
    )
    changed_defaults: list[ChangedDefault] = tools.bounded(
        20, "Up to 20 defaults changed by the note; empty when none changed", [], least=0
    )
    destination: str = Field(
        max_length=200,
        pattern=r"^(?:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)?$",
        description="Empty for the Backlog; otherwise owner/name, at most 200 characters, literally in the note",
        examples=["example/project"],
    )
    summary: str = tools.bounded(
        2000, "What you inspected and found, 1-2000 characters", "Read the setup guide against the CLI; one defect."
    )


class Target(tools.Args):
    """Ask the host to pin the ref the note requested, without changing it yourself."""

    ref: str = tools.bounded(200, "Git ref requested by the note, 1-200 characters", "v1.258")
    reason: str = tools.bounded(500, "Why the note requests this target, 1-500 characters", "The note names v1.258.")


SUBMIT = tools.Spec(
    "submit_result", "Submit the read-only audit's findings and coverage once.", AuditFindings, "result"
)
SET_TARGET = tools.Spec(
    "set_target",
    "Ask the host to resolve and pin only a target requested by the note; continue after its reply.",
    Target,
    "result",
)


def check(args: AuditFindings, root: Path) -> list[str]:
    """Refuse an invented publication destination while the report's author can still correct it."""
    note = json.loads((root / "context" / "run.json").read_text(encoding="utf-8"))["note"]
    if args.destination and (not note.strip() or args.destination not in note):
        return ["destination: use an empty string for the Backlog, or owner/name occurring literally in the run's note"]
    return []
