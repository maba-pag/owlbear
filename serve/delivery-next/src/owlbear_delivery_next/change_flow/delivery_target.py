"""Proof of a Change's delivery, and the owner's disposition when its PR merged elsewhere."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, Option, Question, StepKind, Stop
from owlbear_delivery_next.change_flow.moves import ask, go

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.change_flow.loop import PrState, StepResult
    from owlbear_delivery_next.github.provider import PullRequest

ACTION = "Resolve the PR delivery discrepancy"
PREFIX = "delivery-mismatch:"


def mismatch(c: Change, pr: PullRequest, repository: str) -> str:
    """Why the PR is not the stored repository, number, branch and target; empty when they match."""
    if pr.repository.casefold() != repository.casefold():
        return f"PR #{pr.number} is in {pr.repository}, not {repository}"
    if pr.number != c.names.pr:
        return f"PR #{pr.number} is not this Change's PR #{c.names.pr}"
    if pr.head_branch != c.names.branch:
        return f"PR #{pr.number} came from {pr.head_branch}, not {c.names.branch}"
    if pr.base_branch != c.names.target:
        return f"PR #{pr.number} merged into {pr.base_branch}, not {c.names.target}"
    return ""


def delivered(c: Change, pr: PullRequest | None, repository: str) -> bool:
    """Whether the merged PR proves this Change's intended delivery."""
    return pr is not None and pr.merged and not mismatch(c, pr, repository)


def stop(c: Change, why: str, now: datetime) -> Stop:
    """The durable discrepancy marker until the owner chooses a disposition."""
    return Stop(kind=ErrorKind.STATE, reason=why, action=ACTION,
                resume=f"The owner decides how this undelivered Change ends for {c.names.target}", at=now)  # fmt: skip


def question(c: Change, why: str) -> Question:
    """Offer supported abandonment or a pause, never acceptance as the intended delivery."""
    text = (
        f"{why}. Delivery has not fulfilled the stored target {c.names.target}. "
        "Abandon ends this Change without delivery credit, preserving work the target does not contain; "
        "the already-merged PR is not undone. Pause keeps this Change and its work."
    )
    return Question(
        step=c.step.kind,
        text=text,
        cause=f"{PREFIX}{c.names.pr}:{c.names.target}:{c.names.branch}",
        options=[
            Option(id="abandon", label="Abandon without delivery credit", next="abandon"),
            Option(id="pause", label="Pause and keep the Change", next="pause"),
        ],
    )


def halt(c: Change, why: str, now: datetime) -> None:
    """Record the discrepancy and its owner question without starting a step."""
    c.stop = stop(c, why, now)
    ask(c, question(c, why), now)


def held(c: Change) -> bool:
    """Whether the Change retains this delivery discrepancy."""
    return c.stop is not None and c.stop.action == ACTION


def _owned_question(c: Change) -> Question | None:
    o = c.outcome
    if not held(c) or o is None or o.exit is not Exit.ASK:
        return None
    return next((q for q in c.questions if q.id == o.question and (q.cause or "").startswith(PREFIX)), None)


def waiting(c: Change) -> bool:
    """Whether the current outcome still presents the unanswered delivery disposition."""
    q = _owned_question(c)
    return q is not None and q.answer is None


def accounted(c: Change, result: StepResult, now: datetime) -> Change:
    """Charge an ended runner without displacing the terminal owner gate, including its paused hold."""
    from owlbear_delivery_next.change_flow.loop import apply  # noqa: PLC0415 - loop imports this module

    saved = (c.stop, c.outcome) if _owned_question(c) is not None else None
    after = apply(c, result, now)
    if saved is not None:
        after.stop, after.outcome = saved
    return after


def route(c: Change, observed: PrState | None, now: datetime) -> bool:
    """A terminal discrepancy is visible even while paused; only an explicit abandonment ends it."""
    if c.finished_at:
        return False
    if c.intent.abandoned_at and (observed == "misdelivered" or held(c)):
        if c.step.kind != StepKind.CLEANUP or c.step.mode != "abandon":
            go(c, StepKind.CLEANUP, mode="abandon")
            c.stop, c.outcome = None, None
        return True
    if observed != "misdelivered":
        return False
    if not held(c):
        halt(c, f"PR #{c.names.pr} merged, but not as {c.names.branch} into {c.names.target}", now)
    elif c.intent.paused_at is None and not waiting(c) and c.stop is not None:
        halt(c, c.stop.reason, now)
    return True
