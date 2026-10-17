"""Challenge rounds (TD-208, TD-209): a loop's findings with stable IDs, its rounds and the policy it pinned."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from collections.abc import Sequence

type FindingState = Literal[
    "open", "fixed", "rejected", "standing", "escalated", "owner-fix", "owner-drop", "withdrawn"
]
type Ended = Literal["", "clean", "count", "max", "accepted", "retried", "restarted", "replanned"]
MAX_FINDINGS = 20  # a review result's own cap
FINAL = "final"  # the final review's subject
RECHECK = "rejections"  # a review step that judges only an early last round's rejections (TD-218)
KEYED = re.compile(r"- (F\d+): (.*)")


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RoundPolicy(_Record):
    """The four values a loop runs with (TD-209), pinned when it starts."""

    max_rounds: int = Field(default=3, ge=1)
    max_findings: int = Field(default=10, ge=1, le=MAX_FINDINGS)
    last_round_at: int = Field(default=4, ge=0)
    ask_owner_at: int = Field(default=7, ge=1)

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if not self.last_round_at < self.ask_owner_at <= self.max_findings:
            msg = (
                f"last round at ({self.last_round_at}) must be below ask owner at ({self.ask_owner_at}), "
                f"which must not exceed max findings ({self.max_findings})"
            )
            raise ValueError(msg)
        return self


class RoundFinding(_Record):
    """One finding of a loop, known by the same ID in every round."""

    id: str  # F<n> in order of first raise
    text: str  # "place: problem - fix: fix"
    raised: int  # the round that raised it
    tasks: list[str] = Field(default_factory=list)  # the plan tasks a final-review finding names (TD-216)
    state: FindingState = "open"
    reason: str = ""  # the worker's rejection reason
    judgement: str = ""  # the challenger's judgement of that rejection
    note: str = ""  # the owner's note
    repair: str = ""  # the repair task that reported it fixed

    @property
    def line(self) -> str:
        """The finding as one line of a repair task, carrying its ID."""
        return f"- {self.id}: {self.text}"


class Completion(_Record):
    """The engine's record that the final loop ended without a pass (TD-208): it stands for this content only."""

    head: str  # the commit the last, unreviewed repair left
    criteria: dict[str, int] = Field(default_factory=dict)  # the brief's criterion versions then


class RoundLoop(_Record):
    """One subject's challenge loop: a root plan task, the final review, a plan, a pack update or a brief."""

    subject: str
    attempt: int = 1
    since: int = 0  # the plan's task count when the attempt began: later tasks were made during it
    round: int = 0  # completed verdicts
    found: int = 0  # the latest verdict's new findings
    extra: int = 0  # rounds the owner granted beyond max rounds
    policy: RoundPolicy
    findings: list[RoundFinding] = Field(default_factory=list)
    last: bool = False  # the latest verdict made its round the last
    ended: Ended = ""
    unreviewed: list[str] = Field(default_factory=list)  # repair tasks no round reviewed
    reviewed: list[str] = Field(default_factory=list)  # repairs a full round reviewed after they reported their fixes
    batch: list[str] = Field(default_factory=list)  # the final loop's built repair, whose rejections it judges next
    head: str = ""  # the commit the latest verdict reviewed
    reentry: bool = False  # new work after the loop ended: this round focuses on it (TD-215)
    completion: Completion | None = None  # set when the final loop's last repair is built
    rebuild: list[str] = Field(default_factory=list)  # the plan tasks the owner ticked, until their undo is done
    undo: str = ""  # the head an undo of this loop's work started from, recorded before anything is promoted
    history: list[RoundLoop] = Field(default_factory=list)  # the attempts a retry or restart replaced

    def raise_findings(self, texts: Sequence[str], tasks: Sequence[Sequence[str]] = ()) -> list[RoundFinding]:
        """Record new findings of the current round under the next free IDs, in order."""
        start = len(self.findings) + 1
        new = [
            RoundFinding(
                id=f"F{start + i}", text=text, raised=self.round, tasks=list(tasks[i]) if i < len(tasks) else []
            )
            for i, text in enumerate(texts)
        ]
        self.findings += new
        return new


def parse(text: str) -> tuple[str, str] | None:
    """A repair line's ID and finding, or None for a line without an ID."""
    found = KEYED.fullmatch(text)
    return (found[1], found[2]) if found else None
