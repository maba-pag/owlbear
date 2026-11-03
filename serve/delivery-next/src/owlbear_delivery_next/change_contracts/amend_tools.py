"""The amendment path's session results (TD-185): the shaper's exact candidate and the challenger's verdict on it."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.amendment_records import AmendField  # noqa: TC001 - pydantic reads it

PREPARE, REVISE, CHALLENGE = "amendment-prepare", "amendment-revise", "amendment-challenge"


class CandidateItem(tools.Args):
    """One item of the exact candidate: the whole new wording of one brief item, or its removal."""

    field: AmendField = Field(description="The brief field the item belongs to", examples=["criterion"])
    key: str = Field(
        default="",
        max_length=300,
        description="The item as the brief names it: a criterion id, a visual state's name, a person check's id, a "
        "scope line as written, a decision's id; empty to add one, and for ui",
        examples=["AC-2"],
    )
    text: str = Field(
        default="",
        max_length=2000,
        description="The whole new wording: a criterion, a state's or check's expectation, a scope line, a "
        "decision's answer; for ui `true` or `false`; empty with remove",
        examples=["greet() trims surrounding spaces from the name"],
    )
    question: str = Field(default="", max_length=500, description="Only for a new decision: the question it settles")
    path: str = Field(default="", max_length=300, description="Only for a new visual state: its page path")
    steps: list[str] = Field(
        default_factory=list, max_length=10, description="Only for a new or changed person check: its steps"
    )
    remove: bool = Field(default=False, description="true to remove the item instead of rewording it")
    why: str = tools.bounded(500, "Why the approved wording is wrong and what the new one keeps", "Tabs are not names")


class CandidateResult(tools.Args):
    """``submit_result`` for the shaper's candidate: its items, or why it needs reshaping, and rejected findings."""

    items: list[CandidateItem] = Field(
        default_factory=list, max_length=10, description="The exact candidate; empty only with refuse"
    )
    refuse: str = Field(
        default="",
        max_length=1000,
        description="Only when the change needs the outcome or the non-goals: why; it is refused for reshaping",
    )
    rejected: list[tools.Rejection] = Field(
        default_factory=list,
        max_length=20,
        description="Only when your message lists findings: each one you judge wrong, with your reason",
    )


class Affected(tools.Args):
    """A visual state or person check the change affects beyond the changed items, with the reason."""

    item: str = tools.bounded(300, "screen:<state name> or check:<check id>", "screen:home")
    reason: str = tools.bounded(500, "Why its result no longer holds", "it shows the greeting AC-1 words")


class VerdictResult(tools.Args):
    """``submit_result`` for the amendment challenge: the verdict on the whole candidate and what it touches."""

    verdict: Literal["equivalent", "weaker", "unsure"] = Field(
        description="equivalent when nothing could pass that failed before; weaker when something could; unsure "
        "when only the owner can tell",
        examples=["equivalent"],
    )
    reasons: str = tools.bounded(2000, "Why, with evidence from the code, tests or brief", "AC-3 covers it")
    findings: list[tools.Finding] = Field(
        default_factory=list, max_length=20, description="Each problem of the wording that must be fixed"
    )
    rechecked: list[tools.Recheck] = Field(
        default_factory=list,
        max_length=20,
        description="Only when your message lists rejected findings to judge: your verdict on each one listed",
    )
    qualifies: bool = Field(
        default=False,
        description="true only when every item replaces a redundant or over-specific generated check and evidence "
        "independent of the proposer shows it",
    )
    build_only: bool = Field(default=False, description="true when the only motive is that the build fails against it")
    tightening: str = Field(
        default="", max_length=1000, description="For a tightening: its scope and cost; empty otherwise"
    )
    widens: bool = Field(default=False, description="true when it widens the Change's scope")
    affected: list[Affected] = Field(default_factory=list, max_length=20)
    beyond: str = Field(
        default="", max_length=1000, description="Only when your message gives the owner's answer: what it says more"
    )
    doubts: str = Field(
        default="", max_length=1000, description="A doubt only the owner can settle, which his answer left open"
    )


CANDIDATE = tools.Spec("submit_result", "Submit the exact candidate once.", CandidateResult, "result")
VERDICT = tools.Spec("submit_result", "Submit your verdict on the candidate once.", VerdictResult, "result")
