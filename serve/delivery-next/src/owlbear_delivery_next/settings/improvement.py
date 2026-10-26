"""Improvement's layered settings (design §4, the owner's choices of 2026-10-25): the Spotter's.

Global, this machine or a project sets each field; none is built in. ``mode``, ``steer_share``, ``intervention_cap``,
``verbose`` and ``looks`` must be set, and ``sample_rate`` when ``sample`` is a look; ``verbose_until`` is optional.
Nothing reads them yet beyond the mode, which switches W1a's feed: the looks, live delivery and the test come later.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any, Literal, get_args

from pydantic import ConfigDict, Field, field_validator

from owlbear_delivery_next.change_contracts.models import Record

if TYPE_CHECKING:
    from collections.abc import Callable

type Mode = Literal["off", "learning", "live"]  # off; record what it would do; act
type Verbose = Literal["off", "on"]
type Look = Literal["hand-off", "plan", "state-change", "sample"]
LOOKS: tuple[str, ...] = get_args(Look.__value__)
REQUIRED: tuple[str, ...] = ("mode", "steer_share", "intervention_cap", "verbose", "looks")


class Spotter(Record):
    """The Spotter's settings in one layer, or resolved; ``None`` inherits, or is unset once resolved."""

    model_config = ConfigDict(extra="forbid", strict=True)

    mode: Mode | None = None
    steer_share: int | None = Field(default=None, ge=0, le=100)  # percent of whole Changes and chats steered when live
    intervention_cap: int | None = Field(default=None, ge=0, le=20)  # steering notes per step or chat turn
    verbose: Verbose | None = None  # a bounded rationale with its evidence per look
    verbose_until: str | None = None  # an ISO date; after it, verbose counts as off
    looks: list[Look] | None = None
    sample_rate: int | None = Field(default=None, ge=0, le=100)  # percent of completed actions, when sample is a look

    @field_validator("looks")
    @classmethod
    def _looks(cls, v: list[str] | None) -> list[str] | None:
        if v is not None and (not v or len(set(v)) < len(v)):
            raise ValueError("looks must be a non-empty list without repeats")  # noqa: EM101, TRY003
        return v

    @field_validator("verbose_until")
    @classmethod
    def _until(cls, v: str | None) -> str | None:
        if v is not None:
            date.fromisoformat(v)
        return v

    def verbose_on(self, today: date) -> bool:
        """Whether looks explain themselves today: verbose on and not past its date."""
        return self.verbose == "on" and (self.verbose_until is None or today <= date.fromisoformat(self.verbose_until))


def resolve(pick: Callable[..., Any], layers: list[tuple[str, Any]]) -> tuple[Spotter, list[str]]:
    """Each field from the first layer that sets it (*pick* records its source); and the required keys left unset."""
    values = {
        name: pick(f"spotter.{name}", *((s, getattr(layer.spotter or Spotter(), name)) for s, layer in layers))
        for name in Spotter.model_fields
    }
    spotter = Spotter.model_validate(values)
    needed = [*REQUIRED, *(("sample_rate",) if spotter.looks and "sample" in spotter.looks else ())]
    return spotter, [f"spotter.{n}" for n in needed if values[n] is None]
