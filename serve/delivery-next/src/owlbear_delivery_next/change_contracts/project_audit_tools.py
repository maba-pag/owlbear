"""The project auditor's report and session-bound target request."""

from __future__ import annotations

import json
import re
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


class AuditPart(tools.Args):
    """Coverage of one requested lens part."""

    part: str = tools.bounded(200, "Lens part's name, 1-200 characters", "lean: dependencies")
    ran: bool = Field(description="Whether this part was inspected; true or false", examples=[True])
    note: str = tools.bounded(
        2000, "Inspection evidence or why the part did not run, 1-2000 characters", "Read manifests and imports."
    )


class AuditFindings(tools.Args):
    """``submit_result`` for a read-only project audit."""

    findings: list[AuditFinding] = tools.bounded(60, "Up to 60 findings; empty is valid", [], least=0)
    parts: list[AuditPart] = Field(
        default_factory=list,
        max_length=60,
        description="Up to 60 lens parts with coverage; empty when no lens parts were requested",
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
        description="Empty for the Backlog; otherwise github.com owner/name, at most 200 characters, named in the note",
        examples=["example/project"],
    )
    summary: str = tools.bounded(
        2000, "What you inspected and found, 1-2000 characters", "Read the setup guide against the CLI; one defect."
    )


class AuditVerdict(tools.Args):
    """The verifier's judgment of one host-numbered finding."""

    finding: int = Field(
        ge=1,
        le=60,
        strict=True,
        description="Finding's one-based number in context/run.json, 1-60",
        examples=[1],
    )
    verdict: Literal["accepted", "rejected", "unsure"] = Field(
        description="One judgment: accepted, rejected or unsure", examples=["accepted"]
    )
    reason: str = tools.bounded(
        2000, "Evidence and reason for this judgment, 1-2000 characters", "The caller drops the stored receipt."
    )
    decisions: list[Annotated[str, Field(min_length=1, max_length=200)]] = tools.bounded(
        200, "Up to 200 applicable decision IDs, each 1-200 characters; empty if none apply", [], least=0
    )
    duplicate_of: str = Field(
        max_length=500,
        description="Existing issue reference when this is a duplicate, otherwise empty; at most 500 characters",
        examples=["https://github.com/example/project/issues/42"],
    )


class AuditVerdicts(tools.Args):
    """``submit_result`` with exactly one judgment per numbered finding."""

    verdicts: list[AuditVerdict] = tools.bounded(
        60, "Exactly one verdict per finding in context/run.json, up to 60; empty for no findings", [], least=0
    )


class Target(tools.Args):
    """Ask the host to pin the ref the note requested, without changing it yourself."""

    ref: str = tools.bounded(200, "Git ref requested by the note, 1-200 characters", "v1.258")
    reason: str = tools.bounded(500, "Why the note requests this target, 1-500 characters", "The note names v1.258.")


SUBMIT = tools.Spec(
    "submit_result", "Submit the read-only audit's findings and coverage once.", AuditFindings, "result"
)
VERDICT = tools.Spec(
    "submit_result", "Submit exactly one checked verdict per host-numbered audit finding.", AuditVerdicts, "result"
)
SET_TARGET = tools.Spec(
    "set_target",
    "Ask the host to resolve and pin only a target requested by the note; continue after its reply.",
    Target,
    "result",
)


# OWNER: audit findings leave the Backlog only for a repository the note names literally as owner/name.
def check(args: AuditFindings | AuditVerdicts, root: Path) -> list[str]:
    """Check destination consent or exact finding coverage while the author can still correct it."""
    run = json.loads((root / "context" / "run.json").read_text(encoding="utf-8"))
    if isinstance(args, AuditVerdicts):
        numbers = [v.finding for v in args.verdicts]
        expected = set(range(1, len(run["findings"]) + 1))
        if len(numbers) != len(set(numbers)) or set(numbers) != expected:
            return [
                (
                    f"verdicts.finding: submit exactly one verdict for every finding 1..{len(expected)}, "
                    f"with no duplicates or other numbers; received {numbers}"
                )
            ]
        return []
    note = run["note"]
    named = re.search(
        rf"(?<![A-Za-z0-9_./:@-])(?i:https?://github\.com/)?{re.escape(args.destination)}"
        r"(?![A-Za-z0-9_-]|\.[A-Za-z0-9_.-])",
        note,
    )
    if args.destination and not named:
        return [
            (
                "destination: name a github.com owner/name from the note, or use an empty string for the Backlog; "
                "other hosts are unsupported"
            )
        ]
    return []
