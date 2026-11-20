"""Merge-side records of a Change: check and lag episodes, the pull-back and Delivery's merge-queue claim."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

QUEUE_UNSEEN = "gate:merge:queue-unseen"  # the owner's question about an enqueue GitHub shows no trace of


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Pullback(_Record):
    """The last attempt to bring the local target branch up to the merged remote one."""

    state: Literal["updated", "behind", "skipped"]
    reason: str = ""
    worktree: str = ""
    at: datetime


class ReleaseLook(_Record):
    """A proven delivery whose owner-approved look waits for its installed release."""

    version: int = Field(ge=1)
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    done_at: datetime | None = None


class QueueClaim(_Record):
    """Delivery's own enqueue attempt at one head, never GitHub's queue state (DR5, TD-226).

    Unsettled while the send's answer is unknown; ``quiet`` counts passes that showed no evidence of it.
    """

    head: str
    at: datetime
    queued_at: datetime | None = None  # GitHub's enqueuedAt of this attempt's entry; its added event has this time
    settled: bool = False
    adopted: bool = False  # a person enqueued it and Delivery followed
    quiet: int = 0


class Episode(_Record):
    """When expected checks were first observed missing at one head (P10), or a PR first lagged a pushed head."""

    head: str
    since: datetime
    pr: int | None = None
