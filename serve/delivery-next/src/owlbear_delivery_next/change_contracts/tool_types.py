"""Shared argument and result-tool contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo


class Args(BaseModel):
    """Strict tool arguments: unknown fields are an error the agent sees."""

    model_config = ConfigDict(extra="forbid")


def bounded(limit: int, description: str, example: object, least: int = 1) -> FieldInfo:
    """A bounded field with its description and one example (T5)."""
    return Field(min_length=least, max_length=limit, description=description, examples=[example])


class Unpicked(Args):
    """One decision missing from the picked set, for the picker to judge rather than the worker to fix."""

    id: str = bounded(40, "The decision's id as the complete list shows it", "D-01JC0000000000000000000000")
    note: str = bounded(300, "How it governs this work, not a finding", "The new page must have no build step.")


@dataclass(frozen=True)
class Spec:
    """One tool's name, description, argument model and the step ending an accepted call causes."""

    name: str
    description: str
    model: type[Args]
    ending: Literal["result", "ask", "premise", "missing-tool"]
