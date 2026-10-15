"""The visual review's routing and the owner's decision (TD-78, TD-79; design skill research §3.5 slice 6).

A round ends in merge, back to the build, or the owner's decision, by the verdict matrix. A round is decided only on
two verified verdicts; a judge without one is run again. The owner decides on the Changes page with Pass or Fail,
the findings he ticks and a comment: a Fail goes back with them, and its comment becomes a criterion every later
review checks until he withdraws it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from owlbear_delivery_next import design_pack, tools
from owlbear_delivery_next.failures import VISUAL_MODEL, cause_key
from owlbear_delivery_next.loop import StepResult
from owlbear_delivery_next.models import VISUAL, ErrorKind, Exit, Option, StepKind
from owlbear_delivery_next.steps import check, engine, review
from owlbear_delivery_next.visual_records import OwnerCriterion

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_delivery_next.models import Change
    from owlbear_delivery_next.visual_records import JudgeVerdict, VisualRound

CAUSE = cause_key(ErrorKind.REVIEW, StepKind.CHECK, "visual-decision")
AGAIN = cause_key(ErrorKind.REVIEW, StepKind.CHECK, "visual-judge")
MODEL = cause_key(ErrorKind.LIVENESS, StepKind.CHECK, VISUAL_MODEL)
REVIEW_OF = {"pass": "pass", "fail": "fix", "unsure": "unsure"}  # a recorded correctness verdict as the review's
FIX = frozenset({"P0", "P1", "P2"})  # severities worth a fix; P3 is polish
OWNER = "owner-"  # an owner criterion's id, which a finding cites as its rule
type Route = Literal["merge", "back", "ask", "again", "model"]


def proposed(kept: VisualRound) -> list[str]:
    """What a fail sends back unless the owner unticks it: what a failing judge found the Change introduced, P0-P2.

    A missed owner criterion is always sent, whatever its severity.
    """
    return [
        f.id
        for v in kept.verdicts
        if v.verdict != "pass"
        for f in v.findings
        if f.introduced is not False and (not f.severity or f.severity in FIX or f.rule.startswith(OWNER))
    ]


def route(
    kept: VisualRound | None, found: Sequence[str], verdict: tools.ReviewResult | None, *, broken: bool
) -> tuple[Route, list[str]]:
    """The verdict matrix: how the round ends, and the lines a fix task carries.

    A failed shot or a new browser error goes back on its own (R8), with the design findings when the setting sends
    design fails back. Otherwise both verdicts must exist: a correctness fail goes back; pass and pass merge;
    a design fail goes back or to the owner by the setting; any unsure goes to the owner (N6). A verdict whose
    judge's model is unknown sends the round to the owner first, unless he already waived the check (TD-94).
    """
    design = kept.verdicts[1] if kept else None
    by_setting = kept is not None and design is not None and kept.design_failures == "back" and design.verdict == "fail"
    sent = lines([design], proposed(kept)) if by_setting and kept else []
    if broken:
        return "back", [*found, *sent]
    if verdict is None or design is None or design.verdict is None or kept is None:
        return "again", []
    ends = _matrix(verdict.verdict, design.verdict, found, sent)
    if not kept.model_waived and not all(v.usage_verified for v in kept.verdicts):
        kept.waivable = ends[0]
        return "model", []
    return ends


def _matrix(said: str, design: str, found: Sequence[str], sent: list[str]) -> tuple[Route, list[str]]:
    """Both verdicts exist: a correctness fail goes back; a design fail with nothing to fix goes to the owner."""
    if said == "fix":
        return "back", [*found, *sent]
    if (said, design) == ("pass", "pass"):
        return "merge", []
    return ("back", sent) if said == "pass" and sent else ("ask", [])


def doubts(ends: Route, verdict: tools.ReviewResult | None, kept: VisualRound | None) -> list[str]:
    """What the owner is asked about: the judges' open questions, or why a judge's model is unknown."""
    if ends == "model" and kept:
        return [f"{v.lens}: {v.reason}" for v in kept.verdicts if not v.usage_verified]
    if ends != "ask":
        return []
    said = [f"{d.place}: {d.question}" for d in getattr(verdict, "doubts", [])]
    return said + [f"{v.lens}: {v.reason}" for v in kept.verdicts if v.reason and v.lens == "design"] if kept else said


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


def unknown(head: str, kept: VisualRound) -> StepResult:
    """A judge's model is unknown: the owner accepts the whole round without the model check, or runs it again."""
    said = [f"{v.lens} {v.verdict}" + (f" ({v.reason[:200]})" if v.reason else "") for v in kept.verdicts]
    text = (
        f"A judge's model is unknown in the visual review of {head[:7]} (round {kept.number}): {'; '.join(said)}. "
        "Accepting takes the whole round without the model check; its verdicts still decide."
    )
    options = [
        Option(id="accept", label="Accept the round without the model check", next="accept"),
        Option(id="retry", label="Run the round again", next="retry"),
    ]
    return engine.ask(StepKind.CHECK, text, MODEL, options)


def matches(c: Change, kept: VisualRound, head: str | None, widths: Sequence[int]) -> bool:
    """Everything the round's verdicts depend on is still the Change's: capture, brief, owner criteria, pack, widths."""
    states, criteria = {s.name: s.version for s in c.brief.visual}, {k.id: k.version for k in c.brief.criteria}
    owner = [k.id for k in c.owner_criteria if k.withdrawn_at is None]
    before, pack = c.before.identity() if c.before else "", design_pack.identity()
    now = (head, c.brief.version, states, criteria, owner, before, pack, list(widths))
    return now == (kept.head, kept.brief, kept.states, kept.criteria, kept.owner, kept.before, kept.pack, kept.widths)


def waived(c: Change, head: str, tree_id: str, widths: Sequence[int]) -> tuple[Change, StepResult] | None:
    """The round the owner accepted without the model check, routed by its verdicts; none once anything moved."""
    kept, v = (c.visual_rounds[-1] if c.visual_rounds else None), c.visual
    if kept is None or kept.outcome != "model" or not kept.model_waived or v is None:
        return None
    if not matches(c, kept, head, widths) or kept.tree != tree_id:
        return None  # the Change moved on; the capture is taken and judged again
    correct = kept.verdicts[0]
    said = REVIEW_OF[correct.verdict or "unsure"]
    found = [f"{f.image}: {f.text}" for f in correct.findings] if said == "fix" else []
    found = found or (["the reviewer did not accept the screenshots"] if said == "fix" else [])
    ends, sent = route(kept, found, tools.ReviewResult.model_construct(verdict=said), broken=False)
    if ends == "again":
        return None
    kept.outcome = ends
    if ends == "merge":
        c.visual = v.model_copy(update={"passed": True, "doubts": []})
        reason = f"visual check of {head[:7]} passed, the model check waived by the owner: {len(v.files)} screenshots"
        return c, StepResult(exit=Exit.DONE, reason=reason, paths=check.declared(c))
    if ends == "ask":
        c.visual = v.model_copy(update={"doubts": [f"{x.lens}: {x.reason}" for x in kept.verdicts if x.reason]})
        return c, ask(head, kept)
    out = sent or found
    c.visual = v.model_copy(update={"findings": out, "doubts": []})
    return c, repair(c, f"Fix: the visual check of {head[:7]} failed: {out[0][:200]}", out)


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
            id=f"{OWNER}{number}", text=d.comment, round=kept.number, brief_version=c.brief.version, at=d.at
        )
        c.owner_criteria.append(criterion)
    kept.outcome = "back"
    found = [*lines(kept.verdicts, d.findings), *([f"owner: {d.comment}"] if d.comment else [])]
    c.visual = v.model_copy(update={"doubts": [], "findings": found})  # decided: nothing is open any more
    return c, repair(c, f"Fix: the owner failed the visual review of {head[:7]}", found)
