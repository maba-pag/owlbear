"""A Change's decisions: those shaped into its brief, those Delivery recorded, and the baseline pinned at approval.

TD-419 slices 2 and 4 (decision-system-build §7).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

type Origin = Literal["decided", "approved", "autonomous"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BriefDecision(_Strict):
    """One choice made while shaping a brief version, with who made it."""

    id: str = ""  # owlbear_decisions.new_id(), kept across brief versions; empty in Changes older than TD-419
    question: str
    answer: str
    origin: Origin
    scope: Literal["change", "project"] = "change"  # project: a lasting rule for later Changes (TD-426)
    replaces: str = ""  # the approved decision this one changes: an approved answer is never edited (TD-430)


class Decision(_Strict):
    """One recorded decision with its provenance."""

    id: str = ""  # owlbear_decisions.new_id() at creation; empty in Changes older than TD-419
    text: str
    origin: Origin
    at: datetime
    words: str = ""  # the owner's own answer behind a decided one; empty in Changes older than TD-419
    paths: list[str] = Field(default_factory=list)  # the UI paths a "Not a UI change" answer covers


class Said(BaseModel):
    """What a pinned decision said, kept for those that applied, so a later difference can show the old wording."""

    model_config = ConfigDict(extra="forbid")

    title: str
    statement: str


class DecisionBaseline(BaseModel):
    """Every decision in force in the project's view at a data commit, by id and revision."""

    model_config = ConfigDict(extra="forbid")

    commit: str
    at: datetime
    revisions: dict[str, str] = Field(default_factory=dict)
    said: dict[str, Said] = Field(default_factory=dict)  # the ones that applied to the Change
