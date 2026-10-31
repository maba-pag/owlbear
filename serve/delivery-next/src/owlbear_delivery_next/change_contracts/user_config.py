"""The owner's user-config switches as a step session carries them.

D-01M5YE4P5317N1HWD0QN6N05E0, D-01M69EBRBBW97001KZ43C0BJM1.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserConfig:
    """Whether a step's session loads the owner's own instructions and skills (D-01M5YE4P5317N1HWD0QN6N05E0).

    ``memory`` is whether it runs with Copilot Memory (D-01M69EBRBBW97001KZ43C0BJM1).
    """

    instructions: bool
    skills: bool
    memory: bool


# A session no site switched on: never more than its own.
USER_OFF = UserConfig(instructions=False, skills=False, memory=False)
