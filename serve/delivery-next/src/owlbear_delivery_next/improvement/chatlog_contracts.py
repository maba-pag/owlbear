"""The step configuration fields chatlog capture reads, independent of the runtime layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pathlib import Path


class StepKind(Protocol):
    """The step kind's serialized name."""

    @property
    def value(self) -> str:
        """The kind as the manifest stores it."""


class StepConfig(Protocol):
    """The configuration fields the capture uses to identify a step's owner."""

    @property
    def session_id(self) -> str:
        """The session that started the step."""

    @property
    def kind(self) -> StepKind:
        """The runtime's step kind."""

    @property
    def role(self) -> str:
        """The agent's role."""

    @property
    def job(self) -> str:
        """The step's job."""

    @property
    def worktree(self) -> Path:
        """The worktree the step runs in."""
