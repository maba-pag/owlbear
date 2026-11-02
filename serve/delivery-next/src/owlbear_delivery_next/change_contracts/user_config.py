"""The owner's user-config switches as a step session carries them.

D-01M5YE4P5317N1HWD0QN6N05E0, D-01M69EBRBBW97001KZ43C0BJM1, D-01M6DX04FRP680Z4GGHK5B9VRC.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.permissions import Level


@dataclass(frozen=True)
class UserConfig:
    """Whether a step's session loads the owner's own instructions and skills (D-01M5YE4P5317N1HWD0QN6N05E0).

    ``memory`` is whether it runs with Copilot Memory (D-01M69EBRBBW97001KZ43C0BJM1); ``guard`` is the shell guard's
    level, fixed when the step's worker is built (D-01M6DX04FRP680Z4GGHK5B9VRC).
    """

    instructions: bool
    skills: bool
    memory: bool
    guard: Level = "strict"  # what decide() judges at by default


# A session no site switched on: never more than its own.
USER_OFF = UserConfig(instructions=False, skills=False, memory=False, guard="strict")
