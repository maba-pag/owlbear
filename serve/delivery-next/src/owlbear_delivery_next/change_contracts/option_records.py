"""Executable worker options and their engine-owned preflight evidence."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery_next.change_contracts.held_records import HeldRun

type OptionAction = Literal["continue", "retry", "pause", "abandon"]


class Record(BaseModel):
    """Strict durable records with runtime-evaluated model fields."""

    model_config = ConfigDict(extra="forbid")


class Inputs(Record):
    """What a review or person-only check depended on; valid while unchanged (P5)."""

    criteria: dict[str, int] = Field(default_factory=dict)
    paths: dict[str, str] = Field(default_factory=dict)
    procedure: int = 0
    environment: list[str] = Field(default_factory=list)


class OptionProof(Record):
    """What Delivery checked before offering an option, never a worker's claimed result."""

    admission: str = ""
    command: str = ""
    head: str = ""
    elapsed_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    exit_code: int | None = None
    output: str = ""
    inputs: str = ""


class PendingQuestion(Record):
    """A submitted ask kept privately while its sequential preflight runs."""

    run: HeldRun
    checks: list[str]
    head: str
    step: tuple[str, str | None, str | None]
    brief: int
    proof: OptionProof | None = None
    answer: str = ""
    inputs: str = ""
