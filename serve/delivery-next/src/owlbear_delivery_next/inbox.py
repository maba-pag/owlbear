"""Inbox items: the owner's and Delivery's inputs to one Change, one discriminated union."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - pydantic resolves annotations at runtime
from typing import Annotated, Literal

from pydantic import Field

from owlbear_delivery_next.models import Channel, Inputs, Record


class _Item(Record):
    at: datetime
    channel: Channel = "status-view"


class BriefApproval(_Item):
    """Approve one brief version."""

    kind: Literal["brief-approval"] = "brief-approval"
    version: int


class AnswerItem(_Item):
    """Answer one open question."""

    kind: Literal["answer"] = "answer"
    question: str
    option: str | None = None
    text: str = ""


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


type InboxItem = Annotated[
    BriefApproval | AnswerItem | CheckResult | Recovery | ConsentItem | IntentItem | PullItem,
    Field(discriminator="kind"),
]
