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
type Outcome = Literal["merge", "back", "ask", "model"]  # "model": a judge's model is unknown; the owner decides
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
    context: str = "default"  # the context tier the judge ran with
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


class DesignInput(_Strict):
    """One design judge session's inputs, kept so a calibration replay judges exactly the same (§3.5)."""

    message: str
    reveal: str
    images: list[str]  # the neutral image names, in attachment order


class OwnerDecision(_Strict):
    """The owner's answer on the decision page, bound to the capture and pack it was given for."""

    outcome: Literal["pass", "fail"]
    findings: list[str] = Field(default_factory=list)  # ticked finding ids
    comment: str = ""
    at: datetime


class VisualRound(_Strict):
    """One visual review: the capture it judged, both verdicts, the detector's evidence and how it ended.

    The capture, brief version, states, criteria, owner criteria, before capture, widths and pack are everything its
    verdicts depend on, so an owner's accept without the model check holds only while all of them stay (TD-94).
    """

    number: int
    head: str
    tree: str
    brief: int = 0  # the brief version the judges saw
    states: dict[str, int] = Field(default_factory=dict)
    criteria: dict[str, int] = Field(default_factory=dict)  # the brief's criterion versions the judges checked
    owner: list[str] = Field(default_factory=list)  # the owner criteria in force (TD-79)
    before: str = ""  # the before capture's identity the blind pairs came from
    widths: list[int] = Field(default_factory=list)
    pack: str = ""  # Impeccable's identity
    blind: dict[str, Literal["before", "after"]] = Field(default_factory=dict)  # the design judge's image names
    design_inputs: list[DesignInput] = Field(default_factory=list)  # each design session's message and images
    design_failures: DesignFailures = "ask"  # the setting in force when the round began
    verdicts: list[JudgeVerdict] = Field(default_factory=list)
    detector: list[DetectorScan] = Field(default_factory=list)
    decision: OwnerDecision | None = None
    outcome: Outcome | None = None
    waivable: Literal["merge", "back", "ask"] | None = None  # where the verdicts lead once the model check is waived
    model_waived: bool = False  # the owner accepted the round without the model check (TD-94)
    at: datetime

    @model_validator(mode="after")
    def _decided_on_two_verified_verdicts(self) -> Self:
        verified = sorted(
            v.lens for v in self.verdicts if v.verdict is not None and (v.usage_verified or self.model_waived)
        )
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


class PageError(_Strict):
    """One console error or uncaught page error a capture saw for one state version at one width (TD-49, TD-51)."""

    state: str
    version: int
    width: int
    kind: Literal["console", "page"]
    text: str
    location: str = ""  # where the browser says it came from; not part of its identity


class VisualResult(_Strict):
    """One judged capture of the brief's visual states at an exact head and tree."""

    head: str
    tree: str
    states: dict[str, int] = Field(default_factory=dict)  # state name -> version judged
    criteria: dict[str, int] = Field(default_factory=dict)  # criterion id -> version judged
    files: list[str] = Field(default_factory=list)  # screenshot names inside the Change's visual directory
    widths: list[int] = Field(default_factory=list)  # the desktop widths captured; a before's fix the after's
    errors: list[PageError] = Field(default_factory=list)  # every console and page error the capture saw
    design: list[DetectorScan] = Field(default_factory=list)  # the design detector's evidence (TD-77)
    doubts: list[str] = Field(default_factory=list)  # what the reviewer could not decide (N6)
    passed: bool = False
    findings: list[str] = Field(default_factory=list)
    at: datetime

    def identity(self) -> str:
        """This capture among others of the same head: a recapture is another one."""
        return f"{self.head}@{self.at.isoformat()}"
