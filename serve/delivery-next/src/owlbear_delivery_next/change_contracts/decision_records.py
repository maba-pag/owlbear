"""A Change's decisions: those shaped into its brief, those Delivery recorded, and the baseline pinned at approval.

TD-419 slices 2 and 4 (decision-system-build §7).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    paths: list[str] = Field(default_factory=list)  # the UI paths a "Not a UI change" answer covers

    @model_validator(mode="before")
    @classmethod
    def _drop_words(cls, data: object) -> object:
        """A Change recorded before TD-449 held the owner's words: dropped, so they are never written back."""
        if isinstance(data, dict) and "words" in data:
            return {k: v for k, v in data.items() if k != "words"}
        return data


class PickedDecision(_Strict):
    """One decision the picker chose, as the list it read showed it."""

    id: str
    revision: str  # its rule revision
    title: str
    statement: str
    note: str = ""  # the picker's note on how it governs the work


class Pick(_Strict):
    """The picker's choice for one brief version (TD-459); approval pins it only while the list is as it read it."""

    version: int
    status: Literal["owed", "ok", "failed"] = "owed"  # owed: a request asked for it and the runner picks next
    reason: str = ""  # why it failed, or the ids it returned that the list did not hold
    commit: str = ""  # the data commit the list was read at
    listed: str = ""  # digest of the list it read: every id with its rule revision
    at: datetime | None = None
    decisions: list[PickedDecision] = Field(default_factory=list)
    dropped: list[str] = Field(default_factory=list)
    session: str = ""  # the picker's session, recorded before it starts: a killed runner's pick resumes it


class Published(_Strict):
    """A brief's project decision its approval published (TD-453), with that save's receipt."""

    id: str
    title: str
    state: str  # in force, or retired by a later approved version
    revision: str = ""  # the file's revision the save wrote
    saved: bool = False
    committed: bool = False
    published: bool = False  # the remote held it after the save; else the data repository's next save pushes it
    notice: str = ""
    at: datetime


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
