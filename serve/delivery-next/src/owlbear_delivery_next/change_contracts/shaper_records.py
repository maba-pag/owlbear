"""The saved shaping chat and its one owner-directed hand-off."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class SavingChat(BaseModel):
    """A runtime-observed save caller, or why that caller could not be established."""

    model_config = ConfigDict(extra="forbid")

    session: str = ""
    call: str = ""
    owner: str = ""
    chat: str = ""
    reason: str = ""


class ShaperNotice(BaseModel):
    """One ready answer's fixed posting attempt; attempted without a receipt is never resent."""

    model_config = ConfigDict(extra="forbid")

    question: str
    version: int
    attempt: int
    message: str
    at: datetime
    state: Literal["pending", "attempted", "posted", "failed"] = "pending"
    detail: str = ""
