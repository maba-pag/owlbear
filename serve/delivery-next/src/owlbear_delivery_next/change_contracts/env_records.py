"""A person-only check's launched environment and the recipe it last started from; re-exported from ``models``."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Record(BaseModel):
    """A stored record: unknown fields are refused."""

    model_config = ConfigDict(extra="forbid")


class Environment(Record):
    """A person-only check's environment: the Builder's launch recipe and the PIDs the host started from it."""

    check: str
    command: str
    directory: str
    ready_url: str
    pids: dict[int, float | None] = Field(default_factory=dict)
    pgid: int | None = None
    launched_at: datetime | None = None  # set before spawning; without ``pgid`` the launch is uncertain
    ready_at: datetime | None = None


class Recipe(Record):
    """The launch recipe one check last started from; reused while its directory's own files are unchanged."""

    check: str
    command: str
    directory: str
    ready_url: str
    inputs: str | None = None  # digest of the directory's own files at launch; unknown is never reused
