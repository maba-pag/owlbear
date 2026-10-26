"""What an owner-confirmed profile replacement was confirmed against, and why a write refused it (R15)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class SourceChangedError(RuntimeError):
    """The clone's old profile changed after the owner confirmed its replacement; nothing was written."""


class TargetChangedError(SourceChangedError):
    """The shared profile changed after the owner confirmed its replacement; nothing was written."""


@dataclass(frozen=True)
class Basis:
    """What the owner confirmed a replacement against: the old profile's digest, the shared profile's digest."""

    source: str = ""
    target: str = ""
    rebind: Callable[[str], None] | None = None  # records the shared digest that now holds, once the write is attempted
