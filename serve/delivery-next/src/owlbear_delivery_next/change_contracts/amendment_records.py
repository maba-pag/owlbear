"""A worker's proposed change to approved brief wording (TD-179 rules 3-6), its exact candidate and its challenge.

Kept apart from ``models`` so the Change record stays within its module limit; re-exported from there.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AmendedCriterion(_Strict):
    """One generated criterion's approved wording and the proposed replacement."""

    criterion: str
    version: int  # the criterion version the proposal was made against
    old: str
    new: str
    why: str


class Amendment(_Strict):
    """One batch a worker proposed, prepared exactly against a brief version, and the challenger's verdict.

    Nothing is applied: the owner adopts a candidate by revising the brief, which he approves as usual.
    """

    id: str
    at: datetime
    step: str  # the step kind that proposed it
    session: str  # the proposing session
    base: int  # the brief version the candidate was prepared against
    items: list[AmendedCriterion]
    evidence: list[str] = Field(default_factory=list)
    reason: str = ""  # the worker's premise
    verdict: Literal["", "equivalent", "weaker", "unsure"] = ""  # "" until the challenge returns
    judged: str = ""  # the challenger's reason: what could now pass that failed before, or its doubt
    challenger: str = ""  # the challenger session
