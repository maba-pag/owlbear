"""The confirmed project profile and the per-role model settings it carries (DR1, TD-27, TD-32)."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - pydantic resolves annotations at runtime
from typing import Literal

from pydantic import Field, model_validator

from owlbear_delivery_next.models import Effort, Record, Role

PROFILE_FORMAT = 1
type Runtime = Literal["managed", "vscode"]


class ProfileEntry(Record):
    """One detected project fact with its evidence (DR1); an HTTP 403 on rules is unknown."""

    state: Literal["known", "unknown", "unsupported"]
    value: str = ""
    evidence: str = ""


class RoleModel(Record):
    """The model and reasoning effort one session role runs with (TD-27)."""

    model: str
    effort: Effort

    @model_validator(mode="after")
    def _valid(self) -> RoleModel:
        """A named model, never ``auto`` (TD-32); luna and haiku always run at ``max`` (TD-27)."""
        if not self.model.strip():
            raise ValueError("model must not be empty")  # noqa: EM101, TRY003
        if self.model.strip().lower() == "auto":
            raise ValueError("model must be named; auto is never used (TD-32)")  # noqa: EM101, TRY003
        if (self.model == "gpt-6-luna" or self.model.startswith("claude-haiku-")) and self.effort != "max":
            raise ValueError(f"{self.model} always runs with effort max, got {self.effort}")  # noqa: EM102, TRY003
        return self


class Profile(Record):
    """The confirmed project profile; a new version is a premise change."""

    format: int = PROFILE_FORMAT
    version: int = 0
    confirmed_at: datetime | None = None
    entries: dict[str, ProfileEntry] = Field(default_factory=dict)
    roles: dict[Role, RoleModel] = Field(default_factory=dict)  # per-project overrides of the role defaults
    runtime: Runtime = "managed"  # TD-35: managed runs agent steps through the SDK; vscode runs them in VS Code
