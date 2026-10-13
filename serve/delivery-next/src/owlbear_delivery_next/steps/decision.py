"""The visual review's routing and the owner's decision (TD-78, TD-79; design skill research §3.5 slice 6).

A round ends in merge, back to the build, or the owner's decision, by the verdict matrix. A round is decided only on
two verified verdicts; a judge without one is run again. The owner decides on the Changes page with Pass or Fail,
the findings he ticks and a comment: a Fail goes back with them, and its comment becomes a criterion every later
review checks until he withdraws it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from owlbear_delivery_next.failures import cause_key
from owlbear_delivery_next.loop import StepResult
from owlbear_delivery_next.models import VISUAL, ErrorKind, Exit, Option, StepKind
from owlbear_delivery_next.steps import check, engine, review
from owlbear_delivery_next.visual_records import OwnerCriterion

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_delivery_next import tools
    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.visual_records import JudgeVerdict, VisualRound

CAUSE = cause_key(ErrorKind.REVIEW, StepKind.CHECK, "visual-decision")
AGAIN = cause_key(ErrorKind.REVIEW, StepKind.CHECK, "visual-judge")
type Route = Literal["merge", "back", "ask", "again"]


def route(
    kept: VisualRound | None, found: Sequence[str], verdict: tools.ReviewResult | None, *, broken: bool
) -> tuple[Route, list[str]]:
    """The verdict matrix: how the round ends, and the lines a fix task carries.

    A failed shot or a new browser error goes back on its own (R8), with the design findings when the setting sends
    design fails back. Otherwise both verdicts must be verified: a correctness fail goes back; pass and pass merge;
    a design fail goes back or to the owner by the setting; any unsure goes to the owner (N6).
    """
    design = kept.verdicts[1] if kept else None
    back = kept is not None and design is not None and kept.design_failures == "back" and design.verdict == "fail"
    sent = lines([design], [f.id for f in design.findings]) if back and design else []
    if broken:
        return "back", [*found, *sent]
    if verdict is None or design is None or design.verdict is None or kept is None:
        return "again", []
    if verdict.verdict == "fix":
        return "back", [*found, *sent]
    if (verdict.verdict, design.verdict) == ("pass", "pass"):
        return "merge", []
    return ("back", sent) if verdict.verdict == "pass" and back else ("ask", [])


def lines(verdicts: Sequence[JudgeVerdict | None], ticked: Sequence[str]) -> list[str]:
    """The ticked findings as fix-task lines, each with its judge, place and rule."""
    return [
        f"{f.state}{f' at {f.width}px' if f.width else ''} ({v.lens}{f', {f.rule}' if f.rule else ''}): {f.text}"
        for v in verdicts
        if v is not None
        for f in v.findings
        if f.id in ticked
    ]


def again(kept: VisualRound | None) -> StepResult:
    """A judge without a verified verdict runs again, with the capture, under the step's budget."""
    missing = (
        [f"{v.lens}: {v.reason or 'no verified verdict'}" for v in kept.verdicts if v.verdict is None] if kept else []
    )
    which = "; ".join(missing) or "its judges"
    reason = f"visual review round {kept.number if kept else '-'} has no verified verdict from {which}"
    return StepResult(exit=Exit.RETRY, cause=AGAIN, reason=reason[:500])


def ask(head: str, kept: VisualRound) -> StepResult:
    """The owner decides this round on the Changes page; his answer holds for its capture and pack only."""
    said = [f"{v.lens} {v.verdict}" + (f" ({v.reason[:300]})" if v.reason else "") for v in kept.verdicts]
    text = f"Decide the visual review of {head[:7]} (round {kept.number}): {'; '.join(said)}"
    options = [
        Option(id="pass", label="Pass", next="accept"),
        Option(id="fail", label="Fail", next="repair"),
        Option(id="pause", label="Pause", next="pause"),
    ]
    return engine.ask(StepKind.CHECK, text, CAUSE, options)


def repair(c: Change, title: str, found: Sequence[str]) -> StepResult:
    """Back to build with every line in repair tasks, packed, none cut."""
    parts = review.pack([f"- {f}" for f in found])
    fix = engine.task(c, title, "review", parts[0])
    more = [engine.task(c, title, "review", d, f"t{int(fix.id[1:]) + i}") for i, d in enumerate(parts[1:], 1)]
    cause = cause_key(ErrorKind.CHECKS, StepKind.CHECK, VISUAL)
    return StepResult(exit=Exit.BACK, back_to=StepKind.BUILD, cause=cause, reason=title, fix_task=fix, more_fixes=more)


def decided(c: Change, head: str, tree_id: str) -> tuple[Change, StepResult] | None:
    """The owner's decision, applied only to the exact capture of the round it was about."""
    kept, v = (c.visual_rounds[-1] if c.visual_rounds else None), c.visual
    if kept is None or kept.decision is None or kept.outcome != "ask" or v is None or v.passed:
        return None
    states, criteria = {s.name: s.version for s in c.brief.visual}, {k.id: k.version for k in c.brief.criteria}
    if (kept.head, kept.tree, kept.states, v.head, v.criteria) != (head, tree_id, states, head, criteria):
        return None  # the Change moved on; the capture is taken and judged again
    d = kept.decision
    if d.outcome == "pass":
        kept.outcome, c.visual = "merge", v.model_copy(update={"passed": True})
        reason = f"visual check of {head[:7]} passed by the owner: {len(v.files)} screenshots"
        return c, StepResult(exit=Exit.DONE, reason=reason, paths=check.declared(c))
    if d.comment:
        number = len(c.owner_criteria) + 1
        criterion = OwnerCriterion(
            id=f"owner-{number}", text=d.comment, round=kept.number, brief_version=c.brief.version, at=d.at
        )
        c.owner_criteria.append(criterion)
    kept.outcome = "back"
    found = [*lines(kept.verdicts, d.findings), *([f"owner: {d.comment}"] if d.comment else [])]
    c.visual = v.model_copy(update={"doubts": [], "findings": found})  # decided: nothing is open any more
    return c, repair(c, f"Fix: the owner failed the visual review of {head[:7]}", found)
