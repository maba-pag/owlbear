"""The settings and folders used by the machine's update jobs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.local_system.data_repo import DataRepo
    from owlbear_delivery_next.settings.config import Settings


class UpdateSource(Protocol):
    """The update state folder, settings and shared project data, without a Change store."""

    root: Path
    name: str

    @property
    def shared(self) -> DataRepo | None:
        """The shared data repository, if configured."""
        ...

    def settings(self) -> Settings:
        """Resolve the settings that apply to the job."""
        ...
