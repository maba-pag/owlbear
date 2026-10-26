"""Inbox items: the owner's and Delivery's inputs to one Change, one discriminated union."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - pydantic resolves annotations at runtime
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, ValidationError

from owlbear_delivery_next.change_contracts.decision_records import (  # noqa: TC001 - pydantic
    DecisionBaseline,
    Pick,
    Published,
)
from owlbear_delivery_next.change_contracts.models import AnswerKind, Channel, Inputs, Record


class _Item(Record):
    at: datetime
    channel: Channel = "status-view"


class BriefApproval(_Item):
    """Approve one brief version."""

    kind: Literal["brief-approval"] = "brief-approval"
    version: int
    baseline: DecisionBaseline | None = None  # None: no data repository, or *unpinned*
    unpinned: bool = False  # the decisions could not be read when the owner approved; the runner asks to pin them
    picked: Pick | None = None  # the pick the approval validated, pinned with the approved version (TD-459)
    published: list[Published] = Field(default_factory=list)  # its project decisions, saved before it was queued


class AnswerItem(_Item):
    """Answer one open question."""

    kind: Literal["answer"] = "answer"
    question: str
    option: str | None = None
    text: str = ""
    round: int | None = None  # the visual round a decision is about (TD-79)
    findings: list[str] = Field(default_factory=list)  # the findings the owner ticked in it
    tasks: list[str] = Field(default_factory=list)  # the plan tasks a final retry rebuilds (TD-217)
    attempt: int | None = None  # with the head, the final loop the owner's task list was shown for
    head: str = ""
    classed: AnswerKind | None = None  # how its relayer classed a worker question's answer (TD-461)
    statement: str = ""  # a clarification's intent as the owner confirmed it when read back


class WithdrawItem(_Item):
    """Withdraw one of the owner's visual criteria; later reviews no longer check it (TD-79)."""

    kind: Literal["withdraw"] = "withdraw"
    criterion: str


class CheckResult(_Item):
    """Pass or fail of one person-only check, with the inputs shown to the user."""

    kind: Literal["check-result"] = "check-result"
    check: str
    passed: bool
    note: str = ""
    inputs: Inputs


class Recovery(_Item):
    """The user performed the current stop's action."""

    kind: Literal["recovery"] = "recovery"
    action: str


class ConsentItem(_Item):
    """Consent to merge one exact head."""

    kind: Literal["merge-consent"] = "merge-consent"
    head: str
    delta: str = ""


class IntentItem(_Item):
    """Pause, resume, abandon, or change the intent."""

    kind: Literal["intent"] = "intent"
    intent: Literal["pause", "resume", "abandon", "change"]
    text: str = ""


class PullItem(_Item):
    """Pull the merged target into the local target branch again."""

    kind: Literal["pull"] = "pull"


class RestartItem(_Item):
    """Restart the final review loop from round 0 (TD-215)."""

    kind: Literal["restart-review"] = "restart-review"


type InboxItem = Annotated[
    BriefApproval
    | AnswerItem
    | CheckResult
    | Recovery
    | ConsentItem
    | IntentItem
    | PullItem
    | RestartItem
    | WithdrawItem,
    Field(discriminator="kind"),
]
_ITEM: TypeAdapter[InboxItem] = TypeAdapter(InboxItem)


def parse_rows(rows: list[tuple[int, str]]) -> tuple[list[InboxItem], list[str]]:
    """The queued items that validate, and the raw text of those that do not (the activity keeps them)."""
    items: list[InboxItem] = []
    rejected: list[str] = []
    for _, text in rows:
        try:
            items.append(_ITEM.validate_json(text))
        except ValidationError:
            rejected.append(text)
    return items, rejected
