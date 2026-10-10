"""Engine steps that arrive in later slices: publication is skipped locally, merging asks, the rest stop."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.loop import StepResult
from owlbear_delivery_next.models import ErrorKind, Exit, Option, Question, StepKind, Stop

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.models import Change


def result(change: Change, now: datetime) -> StepResult:
    """Return a defined exit for a step this slice cannot run, so no runner is relaunched for it."""
    kind = change.step.kind
    if kind in {StepKind.PUBLISH, StepKind.FOLLOW}:
        return StepResult(exit=Exit.DONE, reason="not published: publication is a later slice")
    if kind == StepKind.MERGE:
        text = f"Publishing and merging are a later slice; the checked work is on branch {change.names.branch}"
        options = [
            Option(id="keep", label="Keep the branch for now", next="pause"),
            Option(id="abandon", label="Abandon this Change", next="abandon"),
        ]
        return StepResult(exit=Exit.ASK, question=Question(step=kind, text=text, options=options))
    reason = f"step {kind} is a later slice"
    stop = Stop(kind=ErrorKind.TOOLING, reason=reason, action="Upgrade OwlBear", resume="The step is supported", at=now)
    return StepResult(exit=Exit.STOP, reason=reason, stop=stop)
