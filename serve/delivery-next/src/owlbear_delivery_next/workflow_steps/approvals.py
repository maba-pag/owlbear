"""Host-authored configuration approval and refused-suppression appeal questions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import approval_tools
from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, Option, Question
from owlbear_delivery_next.change_flow import exception_gate, loop, quality, worktree
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.state_store.store import Lock, StoreError
from owlbear_delivery_next.workflow_steps import exception_advice, repair_copy

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_quality.inspect import Protected

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.change_contracts.repair_records import Repair
    from owlbear_delivery_next.runtimes.session_result import Run
    from owlbear_delivery_next.state_store.store import Store


class Requests:
    """Bind project storage and confirmed lint commands for owner-composed approval requests."""

    def __init__(self, store: Store, commands: tuple[tuple[str, ...], ...]) -> None:
        """Use host-owned project identity and lint commands."""
        self.store, self.commands = store, commands

    def requested(self, c: Change, run: Run, path: Path, result: loop.StepResult) -> loop.StepResult:
        """Compose after process and model checks; unknown suppressions never reach the owner."""
        marker = cause_key(ErrorKind.RESULT, c.step.kind, approval_tools.LABEL)
        if result.cause != marker or not isinstance(run.payload, approval_tools.RequestApproval):
            return result
        c.step.session = run.session_id
        base, head, found = quality.current(c, path, self.commands)
        items = exception_gate.pending(c, path, self.store.root, (base, head))
        items = exception_gate.approved(c, self.store.root, head, items)
        if any(not item["refusal"] for item in items):
            return _refused(c, marker, "A suppression has not been judged. Commit, then call judge_exceptions first.")
        configuration = found if found and not quality.approved(c, found.digest) else None
        if not configuration and not items:
            return _refused(
                c, marker, "There is no unapproved protected configuration or refused suppression to approve."
            )
        if worktree.git(path, "status", "--porcelain").strip():
            return _refused(c, marker, "Commit first: approval shows committed changes, not dirty working edits.")
        paths = list(configuration.paths) if configuration else []
        diff, cut = repair_copy.shown(path, base, head, paths) if paths else ("", False)
        shown = "\n\n".join(
            f"{item['place']}: {item['directive']}\nCovered code:\n{item['code']}\n"
            f"Judge refused: {item['refusal']['reason']}"
            for item in items
        )
        if cut or len(diff) + len(shown) > repair_copy.SHOWN or "\0" in shown:
            return _refused(c, marker, "The change is too long or binary to show whole; approval was not asked.")
        advice = self._advice(c, path, configuration, head) if configuration else ""
        text = (
            "Approve this Change's lint, format, CI or hook configuration change or refused suppressions?\n\n"
            f"Changed files: {', '.join(paths) or 'suppressions only'}\n\nWhy the worker needs it: {run.payload.why}"
            + (f"\n\nRefused suppressions:\n{shown}" if shown else "")
            + advice
            + (f"{approval_tools.DIFF}{diff}" if diff else "")
        )
        c.step.question_errors = []
        question = Question(
            step=c.step.kind,
            subject="reserved",
            text=text,
            cause=quality.cause(configuration.digest if configuration else "", exception_gate.digest(items)),
            options=[
                Option(id="approve", label="Approve: resume the step with this change"),
                Option(id="decline", label="Decline: resume the step and take this change back"),
                Option(id="pause", label="Pause", next="pause"),
            ],
        )
        return loop.StepResult(exit=Exit.ASK, reason="quality exceptions need your approval", question=question)

    def _advice(self, c: Change, path: Path, found: Protected, head: str) -> str:
        try:
            said = exception_advice.Advice(self.store, Lock(c.slug)).run(c, path, found, head, self.commands)
        except (OSError, ValueError, RuntimeError, StoreError) as exc:
            said = f"\n\nThe quality judge failed: {failure(exc)}"
        return said


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
