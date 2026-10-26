"""What one worker session produced, and its mapping to the loop's step result (D4 §3.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from owlbear_delivery_next.change_contracts import curation_tools, dispute_tools, tools
from owlbear_delivery_next.change_contracts.failures import (
    QUOTA,
    READ_ONLY,
    RO_WORKTREE,
    UNREAD,
    WRONG_MODEL,
    cause_key,
    quota,
    transient,
)
from owlbear_delivery_next.change_contracts.models import (
    ErrorKind,
    Exit,
    Option,
    Plan,
    Question,
    StepKind,
    Stop,
    Task,
    Waiting,
)
from owlbear_delivery_next.change_flow.loop import StepResult
from owlbear_delivery_next.design_packs import design_tools
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes import missing

type Ending = Literal[
    "result",
    "ask",
    "premise",
    "missing-tool",
    "invalid",
    "no-result",
    "deadline",
    "missing",
    "unread",
    "error",
    "read-only-write",
    "read-only-refused",
    "shared-git-changed",
    "credit-limit",
]
type ModelCheck = Literal["verified", "mismatch", "unknown"]
PROVEN: frozenset[str] = frozenset({"result", "ask", "premise", "missing-tool"})  # endings whose model must be proven
WRONG_MODEL_WAIT = timedelta(minutes=5)  # owner decision 2026-10-15: one rerun of a wrong model, after a fixed wait


@dataclass
class Run:
    """What one session produced and how it ended; ``head`` is the worktree HEAD of the accepted result."""

    session_id: str
    ending: Ending = "error"
    payload: tools.Args | None = None
    first: tools.Args | None = None  # a judge's first look, before its final result (design judge, slice 5)
    detail: str = ""
    head: str | None = None
    changed: list[str] = field(default_factory=list)  # the paths the commits change at ``head``, as Delivery read them
    runtime_pid: int | None = None
    pids: dict[int, float | None] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)
    termination: Termination | None = None
    denials: list[str] = field(default_factory=list)
    denied: dict[str, str] = field(default_factory=dict)  # each denied tool or program, lower case: its last denial
    runtime: str = "sdk"  # the catalogue's runtime the session ran in
    invalid: int = 0
    quota: bool = False  # the runtime reported the Copilot quota exhausted
    quota_reset: datetime | None = None  # when it said the quota resets
    usage_unread: str = ""  # why the usage does not prove the model; such a run is never processed (TD-54, TD-94)
    subagents: list[dict[str, Any]] = field(default_factory=list)  # each subagent's record, a breakdown (TD-129)
    model_check: ModelCheck = "unknown"  # only usage metrics prove the model; a mismatch reruns once after a wait
    tool_calls: dict[str, dict[str, int]] = field(default_factory=dict)  # each tool's tally fields (C-28 T8)


class ReturnedRunError(Exception):
    """An error raised about a session that did return its Run: whatever the error, that Run says how it ended.

    Its owner records the Run's termination, so processes confirmed gone release their reservation, and re-raises.
    """

    run: Run


def usage_gate(run: Run, kind: StepKind, *, accept: bool = False) -> StepResult:
    """TD-94: an unknown model stops the Change until the owner runs the step again or accepts its held result.

    TD-56: a held result may be accepted while the step, brief version and commit it depends on match.
    """
    text = f"The step's model is unknown: {run.usage_unread}. The step's result was not accepted"
    text += "; it is held, so you can accept it without the model check." if accept else "."
    retry = Option(id="retry", label="Run this step again", next="retry")
    take = Option(id="accept", label="Accept the held result without the model check", next="accept")
    question = Question(
        step=kind,
        text=text,
        options=[take, retry] if accept else [retry],
        cause=cause_key(ErrorKind.LIVENESS, kind, UNREAD),
    )
    return StepResult(exit=Exit.ASK, reason=text, question=question)


def missing_cause(kind: StepKind) -> str:
    """Cause key counted each time a resumed session is reported absent."""
    return cause_key(ErrorKind.STATE, kind, "session-missing")


def effect_seen(run: Run) -> bool:
    """An answer's effect is observed only when the step ends with an accepted result or a new question."""
    return run.ending in {"result", "ask"} and run.payload is not None


def limit_reached(run: Run, limit: float | None) -> None:
    """A step without its result whose credits reached its hard limit ended there (TD-178, proven live).

    The runtime allows one last call without tools at the limit and refuses every call after it, so the session
    goes quiet and a reminder costs nothing; the usage, not the runtime's message text, shows the limit was reached,
    and the original ending stays in the detail.
    """
    used = run.usage.get("credits")
    if limit and used is not None and used >= limit and run.ending in {"no-result", "deadline"}:
        was = f"{run.ending}: {run.detail}" if run.detail else run.ending
        run.ending, run.detail = "credit-limit", f"credit limit reached: {used:.2f} of {limit:g} (ended {was})"


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


def to_result(run: Run, kind: StepKind, now: datetime, enclosing: StepKind | None = None) -> StepResult:
    """Map one session's ending to the loop's step result, carrying the last permission denial.

    *enclosing* is the step a reviewer session ran for; a missing-tool report is that step's to handle.
    """
    result = _exit(run, kind, now, enclosing or kind)
    return result.model_copy(update={"denial": run.denials[-1][:300]}) if run.denials and not result.denial else result


def _exit(  # noqa: C901, PLR0911, PLR0912, PLR0915 - one case per ending
    run: Run, kind: StepKind, now: datetime, enclosing: StepKind
) -> StepResult:
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
    if run.ending == "shared-git-changed":  # never restored: the owner may have made the change himself (TD-146)
        stop = Stop(
            kind=ErrorKind.POLICY,
            reason=run.detail,
            action="Check the repository's shared Git config and hooks folder; undo any change you did not make",
            resume="The shared Git config and hooks are as you want them",
            at=now,
        )
        return StepResult(exit=Exit.STOP, reason=stop.reason, stop=stop)
    if run.ending == "credit-limit":  # the owner's spending bound: never retried, nor waited out as a quota
        stop = Stop(
            kind=ErrorKind.POLICY,
            reason=run.detail,
            action="Raise the step's credit limit, or run it without one",
            resume="The step's credit limit allows it to finish",
            at=now,
        )
        return StepResult(exit=Exit.STOP, reason=stop.reason, stop=stop)
    if run.ending == "read-only-write":  # voided whatever it submitted; the quota does not excuse it
        return StepResult(exit=Exit.RETRY, cause=cause_key(ErrorKind.POLICY, enclosing, READ_ONLY), reason=run.detail)
    if run.ending == "read-only-refused":  # no session ran
        return StepResult(exit=Exit.RETRY, cause=cause_key(ErrorKind.STATE, enclosing, RO_WORKTREE), reason=run.detail)
    if run.model_check == "mismatch":  # void whatever it submitted; the budget allows one rerun after the wait
        # Until the host schedules sessions (TD-104/105), the wait stands in for queueing behind other ready work.
        cause, wake = cause_key(ErrorKind.TOOLING, kind, WRONG_MODEL), now + WRONG_MODEL_WAIT
        return StepResult(exit=Exit.RETRY, cause=cause, reason=run.detail, wake_at=wake)
    if run.quota and run.ending not in {"result", "ask", "premise", "missing-tool"}:  # the quota ended it
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
        case "result" if isinstance(p, design_tools.DesignResult):  # the round's verdict matrix decides what follows
            found = "; ".join(f"{f.image}: {f.problem}" for f in p.findings)[:1500]
            return StepResult(exit=Exit.DONE, reason=f"design {p.verdict}: {found or p.doubt or 'no findings'}")
        case "result" if isinstance(p, dispute_tools.ReconsiderResult):  # the disputes record each verdict
            return StepResult(exit=Exit.DONE, reason=f"{len(p.reconsidered)} finding(s) reconsidered")
        case "result" if isinstance(p, curation_tools.TestReviewResult):  # the share records its verdicts
            return StepResult(exit=Exit.DONE, reason=f"{len(p.verdicts)} verdict(s), {p.kept} test(s) kept")
        case "result" if isinstance(p, curation_tools.TestCurationResult):
            return StepResult(exit=Exit.DONE, reason=p.summary[:200])
        case "premise" | "missing-tool" if kind == StepKind.TESTS:  # a share retries; its plan is fixed (TD-390)
            said = p.reason if isinstance(p, tools.WrongPremise) else run.detail
            said = f"missing {p.tool}: {p.error}" if isinstance(p, tools.MissingTool) else said
            return StepResult(exit=Exit.RETRY, cause=cause_key(ErrorKind.SCOPE, kind, run.ending), reason=said[:200])
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
        case "missing-tool" if isinstance(p, tools.MissingTool):
            return missing.classify(run, p, enclosing, now)
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
