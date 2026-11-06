"""Delivery starts a missing brief challenge itself (D-01M6P1685N1R5W2PPV5SHKR2H0): when it waits, and Approve.

A brief version the shaper saved after its challenge loop ended waits for one more challenge round. The project host
starts it once the shaper's set wait since that save has passed, unless the shaper asked first. The owner's Approve
starts it at once and records that he approves that version if its verdict raises nothing (``Brief.approve_if_clean``);
the host then makes the approval, with every check the owner's own approval has.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, StepKind, Waiting
from owlbear_delivery_next.change_contracts.round_records import BRIEF

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change

REFUSED = cause_key(ErrorKind.REVIEW, StepKind.SHAPE, "approval")  # the wait after his asked-for approval was refused


def _shaped(c: Change) -> bool:
    return c.step.kind == StepKind.SHAPE and not c.finished_at and not c.intent.abandoned_at


def waiting(c: Change) -> bool:
    """Whether the current brief version waits for the challenge Delivery starts: saved after its loop ended.

    The save's own wait says it: a request reopens the loop before it marks the version requested, a loop's end marks
    the version challenged, and an ended loop holds no question of its own.
    """
    b, lp, o = c.brief, c.loops.get(BRIEF), c.outcome
    saved = o is not None and (o.exit, o.waiting, o.who) == (Exit.PENDING, Waiting.CHAT, "you")
    ended = lp is not None and bool(lp.ended)
    return _shaped(c) and ended and b.version not in {b.challenged, b.approved_version} and saved


def approving(c: Change) -> bool:
    """Whether the owner's recorded approval takes effect now: the loop ended on its version and nothing was raised."""
    b = c.brief
    return _shaped(c) and b.approve_if_clean == b.version == b.challenged != b.approved_version
