"""The visual review's records (TD-74, TD-78, TD-79).

One round per capture: two judges' verdicts, the detector's evidence, the owner's decision; and the owner's
criteria that later rounds check.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

type Lens = Literal["correctness", "design"]
type Verdict = Literal["pass", "fail", "unsure"]
type Outcome = Literal["merge", "back", "ask"]
type DesignFailures = Literal["back", "ask"]
type Freshness = Literal["new", "existing", "unknown"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class JudgeFinding(_Strict):
    """One finding of a judge, with the rule it cites, so the owner can tick it and a fix task can carry it."""

    id: str  # unique within its round, such as ``design-3``
    state: str
    width: int | None = None
    image: str = ""  # the image the judge saw it in; the round's ``blind`` names its side
    text: str
    rule: str = ""  # a section of the design skill or a detector rule id
    severity: Literal["P0", "P1", "P2", "P3"] | None = None
    introduced: bool | None = None  # by this Change; None when the judge could not tell


class JudgeVerdict(_Strict):
    """One judge's verdict in one round; ``verdict`` is None until a verified result exists."""

    lens: Lens
    verdict: Verdict | None = None
    findings: list[JudgeFinding] = Field(default_factory=list)
    reason: str = ""  # why unsure, or why no verified result
    model: str = ""
    effort: str = ""
    usage_verified: bool = False
    unanchored: Verdict | None = None  # the design judge's verdict before it saw the detector (phase 1)
    false_positives: list[str] = Field(default_factory=list)  # detector findings the judge set aside, by rule
    agreed: list[str] = Field(default_factory=list)  # detector rules the judge's findings share
    preferences: dict[str, Literal["before", "after", "equal"]] = Field(default_factory=dict)  # per state-width
    at: datetime | None = None


class DetectorFinding(_Strict):
    """One detector finding as evidence, marked new, existing or unknown against "before"."""

    rule: str
    category: str
    advisory: bool
    where: str
    detail: str = ""
    freshness: Freshness = "unknown"


class DetectorScan(_Strict):
    """One scan of one state at one width, or of the changed sources; never a fail on its own (TD-77)."""

    state: str  # a state name, or ``sources``
    width: int | None = None
    kind: Literal["page", "url", "source"]
    scanned: bool
    reason: str = ""  # why it was not scanned
    covered: list[str] = Field(default_factory=list)  # a source scan's paths, whether or not the tree had them
    findings: list[DetectorFinding] = Field(default_factory=list)


class OwnerDecision(_Strict):
    """The owner's answer on the decision page, bound to the capture and pack it was given for."""

    outcome: Literal["pass", "fail"]
    findings: list[str] = Field(default_factory=list)  # ticked finding ids
    comment: str = ""
    at: datetime


class VisualRound(_Strict):
    """One visual review: the capture it judged, both verdicts, the detector's evidence and how it ended."""

    number: int
    head: str
    tree: str
    states: dict[str, int] = Field(default_factory=dict)
    widths: list[int] = Field(default_factory=list)
    pack: str = ""  # the design pack's identity
    blind: dict[str, Literal["before", "after"]] = Field(default_factory=dict)  # the design judge's image names
    design_failures: DesignFailures = "ask"  # the setting in force when the round began
    verdicts: list[JudgeVerdict] = Field(default_factory=list)
    detector: list[DetectorScan] = Field(default_factory=list)
    decision: OwnerDecision | None = None
    outcome: Outcome | None = None
    at: datetime

    @model_validator(mode="after")
    def _decided_on_two_verified_verdicts(self) -> Self:
        verified = sorted(v.lens for v in self.verdicts if v.verdict is not None and v.usage_verified)
        one_each = verified == ["correctness", "design"] and len(self.verdicts) == len(verified)
        if self.decision is not None and not one_each:
            msg = "a round is decided only on one verified verdict from each judge"
            raise ValueError(msg)
        return self


class OwnerCriterion(_Strict):
    """A Fail comment of the owner, which every later visual review checks until he withdraws it (TD-79)."""

    id: str
    text: str
    round: int
    brief_version: int
    at: datetime
    withdrawn_at: datetime | None = None
