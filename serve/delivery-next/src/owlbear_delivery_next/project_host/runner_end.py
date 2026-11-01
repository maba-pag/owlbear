"""How a project host judges a runner's end: gone without an exit, or processes left behind (D4 §3.2)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts import failures
from owlbear_delivery_next.change_contracts.models import VISUAL, ErrorKind, Exit, StepKind, Stop
from owlbear_delivery_next.change_flow import loop

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.project_host.host import RunnerRecord

type Found = dict[int, str]


def block(found: Found | str, now: datetime) -> Stop:
    """Why no writer starts: the processes of the last step still present, or why they could not be looked for."""
    if isinstance(found, str):
        reason, action = found, "Check that no process of this step remains"
    else:
        named = ", ".join(f"{p} ({n})" if n else str(p) for p, n in sorted(found.items()))
        reason, action = f"processes still present: {named}", f"End processes {', '.join(map(str, sorted(found)))}"
    return Stop(kind=ErrorKind.LIVENESS, reason=reason, action=action, resume="The host sees none of them", at=now)


def unverified(c: Change) -> bool:
    """Whether the Change stopped because the end of its last step could not be verified."""
    return bool(c.stop and c.stop.kind == ErrorKind.LIVENESS and c.outcome and c.outcome.exit == Exit.STOP)


def disappeared(prior: Change, rec: RunnerRecord, now: datetime) -> bool:
    """Whether the runner ended without committing an exit while its step was runnable.

    A person check's environment means its preparer already exited; the visual runner captures while one exists.
    A "before" capture the runner recorded counts as its exit (TD-24).
    """
    o, env, b = prior.outcome, prior.env, prior.before
    runner = env is None or env.check == VISUAL
    return not any(r and r.at >= rec.started_at for r in (o, b)) and runner and loop.next_step(prior, now) is not None


def gone(kind: StepKind) -> loop.StepResult:
    """One counted liveness retry for a runner that disappeared, so a repeating startup failure escalates."""
    cause = failures.cause_key(ErrorKind.LIVENESS, kind, "runner-gone")
    return loop.StepResult(exit=Exit.RETRY, cause=cause, reason="the runner ended without recording an exit")
