"""What one worker session produced, and its mapping to the loop's step result (D4 §3.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from owlbear_delivery_next import tools
from owlbear_delivery_next.failures import QUOTA, cause_key, quota, transient
from owlbear_delivery_next.loop import StepResult
from owlbear_delivery_next.models import ErrorKind, Exit, Option, Plan, Question, StepKind, Stop, Task, Waiting
from owlbear_delivery_next.processes import Termination

type Ending = Literal["result", "ask", "premise", "invalid", "no-result", "deadline", "missing", "unread", "error"]


@dataclass
class Run:
    """What one session produced and how it ended; ``head`` is the worktree HEAD of the accepted result."""

    session_id: str
    ending: Ending = "error"
    payload: tools.Args | None = None
    detail: str = ""
    head: str | None = None
    runtime_pid: int | None = None
    pids: dict[int, float | None] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)
    termination: Termination | None = None
    denials: list[str] = field(default_factory=list)
    invalid: int = 0
    quota: bool = False  # the runtime reported the Copilot quota exhausted
    quota_reset: datetime | None = None  # when it said the quota resets


def missing_cause(kind: StepKind) -> str:
    """Cause key counted each time a resumed session is reported absent."""
    return cause_key(ErrorKind.STATE, kind, "session-missing")


def effect_seen(run: Run) -> bool:
    """An answer's effect is observed only when the step ends with an accepted result or a new question."""
    return run.ending in {"result", "ask"} and run.payload is not None


def note_quota(run: Run, kind: str, data: Any) -> None:  # noqa: ANN401 - SDK event data
    """Record an exhausted Copilot quota and its reset time from a quota observation or a session error."""
    if kind == "session.error":
        text = " ".join(str(getattr(data, f, "") or "") for f in ("error_type", "error_code", "message"))
        run.quota = run.quota or (transient(text) == ErrorKind.CAPACITY and quota(text))
        return
    seen = getattr(data, "observation", None)
    if getattr(seen, "capacity_state", None) != "exhausted":
        return
    run.quota = True
    ms = getattr(getattr(seen, "budget_metadata", None), "reset_at_epoch_ms", None)
    if isinstance(ms, int | float) and ms > 0:
        run.quota_reset = datetime.fromtimestamp(ms / 1000, UTC)


def to_result(run: Run, kind: StepKind, now: datetime) -> StepResult:
    """Map one session's ending to the loop's step result, carrying the last permission denial."""
    result = _exit(run, kind, now)
    return result.model_copy(update={"denial": run.denials[-1][:300]}) if run.denials else result


def _exit(run: Run, kind: StepKind, now: datetime) -> StepResult:  # noqa: C901, PLR0911, PLR0912 - one case per ending
    """One exit per ending; unverified termination stops whatever the session reported; the host scans after."""
    t = run.termination or Termination(confirmed=False, problems=("termination did not run",))
    if not t.confirmed:
        pids = ", ".join(str(p) for p in sorted({*t.survivors, *t.unknown}))
        found = [f"processes {pids} still present"] if pids else []
        stop = Stop(
            kind=ErrorKind.LIVENESS,
            reason="termination unverified: " + "; ".join([*found, *t.problems]),
            action=f"End processes {pids}" if pids else "Check that no process of this step remains",
            resume="No process of this step remains",
            at=now,
        )
        return StepResult(exit=Exit.STOP, reason=stop.reason, stop=stop)
    p = run.payload
    if run.quota and run.ending not in {"result", "ask", "premise"}:  # the quota ended it, whatever it reported
        reason = run.detail or "Copilot quota exhausted"
        return StepResult(
            exit=Exit.RETRY, cause=cause_key(ErrorKind.CAPACITY, kind, QUOTA), reason=reason, wake_at=run.quota_reset
        )
    match run.ending:
        case "result" if isinstance(p, tools.BuildResult):
            return StepResult(exit=Exit.DONE, reason=p.summary[:200])
        case "result" if isinstance(p, tools.ReviewResult):
            found = "; ".join(f"{f.place}: {f.problem} - fix: {f.fix}" for f in p.findings)[:1500]
            return StepResult(exit=Exit.DONE if p.verdict == "pass" else Exit.RETRY, reason=found or "review passed")
        case "result" if isinstance(p, tools.CheckRecipe):
            reason = f"starting `{p.command}` for the check"
            return StepResult(exit=Exit.PENDING, waiting=Waiting.PERSON_CHECK, reason=reason)
        case "result" if isinstance(p, tools.PlanResult):
            tasks = [
                Task(id=f"t{i}", title=t.title, scope=t.scope, checks=t.checks, detail=t.goal)
                for i, t in enumerate(p.tasks, 1)
            ]
            return StepResult(exit=Exit.DONE, reason=f"{len(tasks)} task(s) planned", plan=Plan(tasks=tasks))
        case "ask" if isinstance(p, tools.AskQuestion):
            options = [Option(id=f"o{i}", label=f"{o.label}: {o.effect}") for i, o in enumerate(p.options, 1)]
            question = Question(step=kind, text=f"{p.question} (why: {p.why})", options=options)
            return StepResult(exit=Exit.ASK, question=question)
        case "premise" if isinstance(p, tools.WrongPremise):
            cause = cause_key(ErrorKind.SCOPE, kind, p.stage)
            back = {StepKind.CHECK: StepKind.BUILD, StepKind.PLAN: StepKind.SHAPE}.get(kind, StepKind.PLAN)
            return StepResult(exit=Exit.BACK, back_to=back, cause=cause, reason=p.reason[:200])
        case "deadline":  # an unanswered runtime start is the environment's; the step's own deadline is liveness
            env = transient(run.detail) if run.detail != "step deadline" else None
            cause = cause_key(env, kind, "sdk") if env else cause_key(ErrorKind.LIVENESS, kind, "deadline")
            return StepResult(exit=Exit.RETRY, cause=cause, reason=run.detail or "deadline")
        case "missing":
            return StepResult(exit=Exit.RETRY, cause=missing_cause(kind), reason=run.detail)
        case "unread":
            return StepResult(
                exit=Exit.RETRY, cause=cause_key(ErrorKind.LIVENESS, kind, "transcript"), reason=run.detail
            )
        case "error":
            if transient(run.detail) == ErrorKind.CAPACITY and quota(run.detail):
                cause = cause_key(ErrorKind.CAPACITY, kind, QUOTA)
                return StepResult(exit=Exit.RETRY, cause=cause, reason=run.detail, wake_at=run.quota_reset)
            error = transient(run.detail) or ErrorKind.TOOLING
            return StepResult(exit=Exit.RETRY, cause=cause_key(error, kind, "sdk"), reason=run.detail)
        case _:
            reason = f"no valid result: {run.detail}"
            return StepResult(exit=Exit.RETRY, cause=cause_key(ErrorKind.RESULT, kind), reason=reason)
