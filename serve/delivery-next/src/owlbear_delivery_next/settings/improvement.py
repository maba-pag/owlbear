"""Improvement's layered settings (design §4, the owner's choices of 2026-10-25 and 2026-10-26): the Spotter's.

Global, this machine or a project sets each field; none is built in. ``switch``, the four categories' actions,
``steer_share``, ``intervention_cap``, ``verbose``, ``looks`` and ``look_credit_limit`` must be set, and ``sample_rate``
when ``sample`` is a look; ``verbose_until`` is optional. Each unset one is listed whatever the switch, so the Settings
page shows it; a step is refused only for what it reads (``workflow_steps.watched.needed``): off reads the switch alone.

The switch turns W1a's feed and the Spotter's looks on or off (D-01M5WB09Z3ZKJVN02WGWVHGWBH). The Spotter files each
finding under one of four categories, each set to one action its category allows (D-01M5WP8Z4ADZ5FN7RJDR17RQQ5); a
look records the action its category is given, and nothing acts yet: steering, refusing and stopping come with live
delivery, with the steer share, the cap and the steered-versus-silent test.

Each look, live or replayed, stops at its own credit limit (D-01M5XCD49YHHR1NQKKY8TQD0C3); there is no daily budget.
The limit is a credit amount, a finite number above zero, written into Global once (``settings.carried``).
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Annotated, Any, Literal, get_args

from pydantic import ConfigDict, Field, field_validator

from owlbear_delivery_next.change_contracts.models import Record

if TYPE_CHECKING:
    from collections.abc import Callable

type Switch = Literal["off", "on"]
type Verbose = Literal["off", "on"]
type Look = Literal["hand-off", "plan", "state-change", "sample"]
type FindingCategory = Literal[
    "hand-off-fitness", "course-and-constraints", "outside-state-changes", "irreversible-harm"
]
type HandOffAction = Literal["record", "show-owner", "steer", "refuse-hand-off"]
type CourseAction = Literal["record", "show-owner", "steer", "stop-and-resume", "stop-and-ask"]
type StateAction = Literal["record", "show-owner", "stop-and-resume", "stop-and-ask"]  # outside state and harm
type Credits = Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)]  # a credit limit: finite, above 0
LOOKS: tuple[str, ...] = get_args(Look.__value__)
CATEGORIES: dict[str, str] = {c: c.replace("-", "_") for c in get_args(FindingCategory.__value__)}  # -> its field
REQUIRED: tuple[str, ...] = (
    "switch", *CATEGORIES.values(), "steer_share", "intervention_cap", "verbose", "looks", "look_credit_limit"
)  # fmt: skip


class Spotter(Record):
    """The Spotter's settings in one layer, or resolved; ``None`` inherits, or is unset once resolved."""

    model_config = ConfigDict(extra="forbid", strict=True)

    switch: Switch | None = None  # the Spotter's looks and W1a's feed
    hand_off_fitness: HandOffAction | None = None  # the result should not be accepted as it stands
    course_and_constraints: CourseAction | None = None  # recoverable work heading materially wrong
    outside_state_changes: StateAction | None = None  # a consequential change beyond the task's files, undoable
    irreversible_harm: StateAction | None = None  # takes precedence; what counts is the Spotter's own judgement
    steer_share: int | None = Field(default=None, ge=0, le=100)  # percent of whole Changes and chats steered when live
    intervention_cap: int | None = Field(default=None, ge=0, le=20)  # steering notes per step or chat turn
    verbose: Verbose | None = None  # a bounded rationale with its evidence per look
    verbose_until: str | None = None  # an ISO date; after it, verbose counts as off
    looks: list[Look] | None = None
    sample_rate: int | None = Field(default=None, ge=0, le=100)  # percent of completed actions, when sample is a look
    look_credit_limit: Credits | None = None  # credits one look, live or replayed, may spend before it is stopped

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

    def actions(self) -> dict[str, str]:
        """Each category's action, for those set."""
        return {c: a for c, f in CATEGORIES.items() if (a := getattr(self, f)) is not None}

    def verbose_on(self, today: date) -> bool:
        """Whether looks explain themselves today: verbose on and not past its date."""
        return self.verbose == "on" and (self.verbose_until is None or today <= date.fromisoformat(self.verbose_until))


def _allowed(field: str) -> tuple[str, ...]:
    return get_args(next(a for a in get_args(Spotter.model_fields[field].annotation) if a is not type(None)).__value__)


ALLOWED: dict[str, tuple[str, ...]] = {c: _allowed(f) for c, f in CATEGORIES.items()}  # each category's actions


def resolve(pick: Callable[..., Any], layers: list[tuple[str, Any]]) -> tuple[Spotter, list[str]]:
    """Each field from the first layer that sets it (*pick* records its source); and the required keys left unset.

    Every required key is listed whatever the switch, so the page shows it; ``watched.needed`` decides what blocks.
    """
    values = {
        name: pick(f"spotter.{name}", *((s, getattr(layer.spotter or Spotter(), name)) for s, layer in layers))
        for name in Spotter.model_fields
    }
    spotter = Spotter.model_validate(values)
    needed = [*REQUIRED, *(("sample_rate",) if spotter.looks and "sample" in spotter.looks else ())]
    return spotter, [f"spotter.{n}" for n in needed if values[n] is None]
