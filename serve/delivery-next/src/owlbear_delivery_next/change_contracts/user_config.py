"""The owner's user-config switches as a step session carries them (D-01M5YE4P5317N1HWD0QN6N05E0)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserConfig:
    """Whether a step's session loads the owner's own instructions and skills (D-01M5YE4P5317N1HWD0QN6N05E0)."""

    instructions: bool
    skills: bool


USER_OFF = UserConfig(instructions=False, skills=False)  # a session no site switched on: never more than its own
