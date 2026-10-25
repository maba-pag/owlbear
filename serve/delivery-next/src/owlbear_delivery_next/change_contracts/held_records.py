"""The durable record of a held agent result (RUN-04): the Change keeps it when the held file cannot be written."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class HeldRun(BaseModel):
    """The parts of a session's run its processing reads, with the accounting its gate would have counted (RUN-04)."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    ending: str
    detail: str = ""
    head: str | None = None
    changed: list[str] = []  # the paths the commits change at head, as Delivery read them; empty in older holds
    payload: dict[str, Any] | None = None  # {"model": a result model's name, "args": its fields}
    denials: list[str] = []
    denied: dict[str, str] = {}
    runtime: str = "sdk"
    quota: bool = False
    quota_reset: datetime | None = None
    usage: dict[str, Any] = {}
    usage_unread: str = ""
    model_check: Literal["verified", "mismatch", "unknown"] = "unknown"
    subagents: list[dict[str, Any]] = []
    tool_calls: dict[str, dict[str, int]] = {}
    counted: bool = False  # the usage and tool calls above were kept with the hold; an older build kept none


class PendingChild(BaseModel):
    """A paid child session of a durable parent step, until its verdict, spend and receipt commit together (RUN-04).

    Its usage is the child's own, never the owner-hold marker: the pending child settles once with its Change.
    """

    model_config = ConfigDict(extra="forbid")

    label: str  # the session's step label: plan-challenge or amendment-challenge
    parent: str  # what the child judges: the plan version, or the candidate amendment's id
    route: dict[str, Any] | None = None  # the proposing step's own result, which stands unless the challenger stops
    step: tuple[str, str | None, str | None] | None = None  # the proposing step's kind, task and mode
    run: HeldRun | None = None  # the child's validated run, kept as soon as it returns


class HeldRecord(BaseModel):
    """What the held result depends on, the gate question that offers it, and the result itself.

    The held file holds this record with its Change; when that file cannot be written, the Change keeps it instead.
    """

    model_config = ConfigDict(extra="forbid")

    question: str
    kind: str
    task: str | None
    mode: str | None
    brief: int
    head: str
    at: datetime
    run: HeldRun
    label: dict[str, Any] = {}  # whose session it was when not the step's own (TD-376)
