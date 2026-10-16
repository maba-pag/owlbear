"""The reconsideration of findings the owner sent back to a fresh reviewer with a note (TD-193)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from owlbear_delivery_next import tools

LABEL = "dispute-reconsider"


class Reconsidered(tools.Args):
    """Your judgement of one finding listed under Reconsider."""

    finding: str = tools.bounded(10, "The finding's key as Reconsider lists it", "F2")
    verdict: Literal["withdrawn", "clarified", "unsure"] = Field(
        description="withdrawn if it does not hold; clarified to restate it within its extent; unsure otherwise"
    )
    text: str = Field(
        default="",
        max_length=1000,
        description="Only for clarified: the finding restated, never larger than before",
        examples=["a.txt:1: AC-1 greets in English - fix: use Hallo"],
    )
    reason: str = tools.bounded(1000, "Why, with evidence", "a.txt:1 already says Hallo")


class ReconsiderResult(tools.Args):
    """``submit_result`` for a reconsideration: one verdict per listed finding."""

    reconsidered: list[Reconsidered] = Field(
        min_length=1,
        max_length=20,
        description="Your verdict on each finding listed under Reconsider",
        examples=[[{"finding": "F2", "verdict": "withdrawn", "reason": "a.txt:1 already says Hallo"}]],
    )


SUBMIT = tools.Spec("submit_result", "Submit your verdict on each finding once.", ReconsiderResult, "result")
