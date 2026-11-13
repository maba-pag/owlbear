"""A stuck step's repair as the Change keeps it (#1066, D-01M6RT5QHXFM58C9BPQXEK3QFB)."""

import shlex
from datetime import datetime
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_delivery_next.change_contracts.preparation import Preparation

type Phase = Literal["running", "asked", "approved", "applied", "unchanged", "stopped"]
type Fix = Literal["none", "patch", "profile-check", "retry", "preparation"]
KEPT = "refs/owlbear/repair/"  # + the Change's slug: a fix waiting for the owner's yes stays reachable


class PreparationProposal(BaseModel):
    """One synthetic setup, its data source and consequences, and a command checking the seeded state."""

    model_config = ConfigDict(extra="forbid")

    option: Preparation
    description: str = Field(min_length=1, max_length=3000)
    verify: str = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def _synthetic(self) -> PreparationProposal:
        option = self.option
        if option.kind != "data-only" or option.data_classes or option.live:
            msg = "option: propose synthetic data-only setup, without copying live data or changing permissions"
            raise ValueError(msg)
        home = PurePosixPath(option.isolation.get("HOME", ""))
        if not option.isolation.get("HOME", "").strip() or home.is_absolute() or ".." in home.parts or str(home) == ".":
            msg = "option.isolation.HOME: name a directory inside the execution worktree, relative to its root"
            raise ValueError(msg)
        if not self.description.strip() or not shlex.split(self.verify):
            msg = "description and verify: describe source, seeded data, cleanup and isolation; verify the seeded state"
            raise ValueError(msg)
        return self


class Tried(BaseModel):
    """One fix the repairer tried, and what happened when it ran the checks."""

    model_config = ConfigDict(extra="forbid")

    fix: str
    outcome: str


class Witness(BaseModel):
    """Delivery's own run of the step's checks in the copy, with the fix: only exit 0 is proof."""

    model_config = ConfigDict(extra="forbid")

    commands: list[str]
    exit: int | None  # None: it did not finish within the repairer's time limit, or did not start
    seconds: float
    output: str  # whole


class Repair(BaseModel):
    """One repair of one cause on one step."""

    model_config = ConfigDict(extra="forbid")

    cause: str
    evidence: str  # what the step reported, whole
    step: str
    task: str | None = None
    mode: str | None = None
    phase: Phase = "running"
    at: datetime
    session: str = ""
    rerun: bool = False  # its one rerun after a wrong model is spent (D-01M5DW3X003TZZRSDCY027SP3C)
    found: str = ""  # the repairer's cause, with its evidence
    tried: list[Tried] = Field(default_factory=list)
    fix: Fix = "none"
    package: str = ""  # a profile check's package and command
    command: str = ""
    paths: list[str] = Field(default_factory=list)  # what the fix changes
    base: str = ""  # the copy's baseline: the step worktree's whole state when the repair began
    target: str = ""  # the actual configured target commit this diagnosis must compare with
    commit: str = ""  # the fix, committed by Delivery on that baseline; kept under ``KEPT`` until it ends
    applied: str = ""  # its commit on the Change's branch
    witness: Witness | None = None
    held: list[str] = Field(default_factory=list)  # why the owner is asked before it is applied
    diff: str = ""  # what he is shown
    question: str = ""  # his yes/no question's id
    defect: str = ""  # the issue filed for a defect in OwlBear's code, the text held for him, or why it failed
    credits: float | None = None  # the repair session's spend; None when it could not be read
    stopped: str = ""  # why it stopped
    root: str = ""  # the owner-question cause it repairs, so its own question counts with them (#1064)
    preparation: PreparationProposal | None = None
    preparations_before: list[Preparation] | None = None


class Repairs(BaseModel):
    """The repair under way, if any, and those before it."""

    model_config = ConfigDict(extra="forbid")

    current: Repair | None = None
    done: list[Repair] = Field(default_factory=list)
