"""Brief amendments (TD-185): a proposed change to the approved brief, its exact candidate, its challenge and its end.

Kept apart from ``models`` so the Change record stays within its module limit; re-exported from there.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

type AmendField = Literal["criterion", "ui", "visual", "check", "scope", "decision"]
type Source = Literal["worker", "answer", "allow", "revert"]
type AmendState = Literal["recorded", "proposed", "applied", "declined", "refused", "moved"]
type Phase = Literal["prepare", "challenge", "recheck", "reconsider", "revise", "ask"]
type Level = Literal["", "autonomous", "approved", "decided"]
type Choice = Literal["yes", "within", "reshape", "stop"]
type Objection = Literal["revert", "keep", "reshape"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Action(_Strict):
    """One click or typing step before a visual state's screenshot, as ``models.VisualStep`` holds it."""

    do: Literal["click", "type"]
    target: str
    text: str = ""


class AmendedItem(_Strict):
    """One item's approved wording and its replacement: ``key`` names the item, empty to add one.

    Keys: a criterion's id, a visual state's name, a person check's id, a scope line as approved, a brief decision's
    id; ``ui`` has none. A visual state's ``path`` and a person check's ``steps`` and ``covers`` go with a new or
    changed one.
    """

    field: AmendField = "criterion"
    key: str = ""
    version: int = 0  # the item's version the candidate was made against
    old: str = ""
    new: str = ""
    remove: bool = False
    why: str = ""
    path: str = ""
    steps: list[str] = Field(default_factory=list)
    question: str = ""  # a new decision's
    covers: list[str] = Field(default_factory=list)  # a person check's criterion ids; empty keeps or gives all
    actions: list[Action] | None = None  # a visual state's steps before its screenshot; None keeps them
    visual: bool | None = None  # whether the person judges how a check's UI looks; None keeps it

    @model_validator(mode="before")
    @classmethod
    def _legacy(cls, data: object) -> object:
        """A TD-179 record named its generated criterion ``criterion``."""
        if isinstance(data, dict) and "criterion" in data:
            data = {k: v for k, v in data.items() if k != "criterion"} | {
                "field": "criterion",
                "key": data["criterion"],
            }
        return data


class Amendment(_Strict):
    """One proposed change, its exact candidate against a brief version, the challenger's verdict and how it ended.

    A record from before TD-185 is ``recorded``: judged at most, never applied.
    """

    id: str
    at: datetime
    step: str  # the step kind it stopped
    session: str = ""  # the proposing session, for a worker's
    source: Source = "worker"
    base: int  # the brief version the candidate was prepared against
    items: list[AmendedItem]
    evidence: list[str] = Field(default_factory=list)
    reason: str = ""  # the source's: a worker's premise, the owner's answer or the finding he allowed
    verdict: Literal["", "equivalent", "weaker", "unsure"] = ""
    judged: str = ""  # the challenger's reasons
    challenger: str = ""  # the last challenger session
    state: AmendState = "recorded"
    reference: int | None = None  # the reference version its weakening was judged from
    qualifies: bool = False  # every item replaces a redundant or over-specific generated check, shown independently
    build_only: bool = False  # motivated only by a failing build
    tightening: str = ""  # a tightening's scope and cost
    widens: bool = False  # it widens the scope: the governing decisions are reassessed
    affected: list[str] = Field(default_factory=list)  # "screen:<name>" or "check:<id>" the challenger named
    beyond: str = ""  # what it says beyond the owner's answer
    doubts: str = ""  # a doubt only the owner can settle
    unreviewed: bool = False  # its final wording is a revision no round judged
    level: Level = ""
    version: int | None = None  # the brief version it made
    choice: Choice | Literal[""] = ""  # the owner's answer
    declined: str = ""  # his reason for declining it
    refused: str = ""  # why the shaper refused it for reshaping
    reverts: str = ""  # the amendment a revert undoes
    question: str = ""  # the question whose answer started it
    moved_to: str = ""  # the new Change that holds it: this one merged before it ended
    done: list[str] = Field(default_factory=list)  # ``plan version:task id`` done when it applied: not built on it
    objected_at: datetime | None = None
    objection: Objection | Literal[""] = ""


class Amending(_Strict):
    """The amendment the Change runs before its stopped step (``Change.step``), and where its path is."""

    id: str
    phase: Phase = "prepare"
    revision: int = 0  # the shaper's revisions of its candidate: the loop's head is ``r<revision>``
