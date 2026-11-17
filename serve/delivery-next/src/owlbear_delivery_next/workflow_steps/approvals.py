"""Host-authored configuration approval questions, without worker-question admission."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import approval_tools
from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, Option, Question
from owlbear_delivery_next.change_flow import loop, quality
from owlbear_delivery_next.workflow_steps import repair_copy

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.change_contracts.repair_records import Repair
    from owlbear_delivery_next.runtimes.session_result import Run


def requested(c: Change, run: Run, path: Path, commands: tuple[tuple[str, ...], ...], result: loop.StepResult) -> loop.StepResult:
    """Compose only after the runtime's process and model checks allowed the request to reach the engine."""
    marker = cause_key(ErrorKind.RESULT, c.step.kind, approval_tools.LABEL)
    if result.cause != marker or not isinstance(run.payload, approval_tools.RequestApproval):
        return result
    c.step.session = run.session_id
    base, head, found = quality.current(c, path, commands)
    if found is None or quality.approved(c, found.digest):
        return _refused(c, marker, "There is no unapproved protected configuration change to approve.")
    diff, cut = repair_copy.shown(path, base, head, list(found.paths))
    if cut:
        return _refused(c, marker, "The configuration change is too long or binary to show whole; approval was not asked.")
    text = (
        "Approve this Change's lint, format, CI or hook configuration change?\n\n"
        f"Changed files: {', '.join(found.paths)}\n\nWhy the worker needs it: {run.payload.why}"
        f"{approval_tools.DIFF}{diff}"
    )
    c.step.question_errors = []
    question = Question(
        step=c.step.kind,
        subject="reserved",
        text=text,
        cause=quality.cause(found.digest),
        options=[
            Option(id="approve", label="Approve: resume the step with this configuration change"),
            Option(id="decline", label="Decline: resume the step and take this configuration change back"),
            Option(id="pause", label="Pause", next="pause"),
        ],
    )
    return loop.StepResult(exit=Exit.ASK, reason="configuration change needs your approval", question=question)


def _refused(c: Change, cause: str, reason: str) -> loop.StepResult:
    c.step.question_errors = [f"request_approval: {reason}"]
    return loop.StepResult(exit=Exit.RETRY, cause=cause, reason=c.step.question_errors[0])


def presentation(q: Question, repair: Repair | None = None) -> dict[str, str]:
    """Expose the persisted, complete patch using the repair question's existing diff renderer."""
    if repair and repair.phase == "asked" and repair.question == q.id and repair.fix == "patch":
        return {"text": q.text.removesuffix(f"\n\nThe fix:\n{repair.diff}"), "diff": repair.diff}
    if not (q.cause or "").startswith(quality.cause("")):
        return {}
    text, separator, diff = q.text.partition(approval_tools.DIFF)
    return {"text": text, "diff": diff, "diff_label": "The configuration patch"} if separator else {}
