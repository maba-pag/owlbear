"""The confirmed project profile and the per-role model settings it carries (DR1, TD-27, TD-32)."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - pydantic resolves annotations at runtime
from typing import Literal

from pydantic import Field, model_validator

from owlbear_delivery_next.change_contracts.models import Context, Effort, Record

PROFILE_FORMAT = 2  # format 2 moved the role overrides into the project settings (config.json)
type Runtime = Literal["managed", "vscode"]


def named(model: str) -> str:
    """A named model, never empty and never ``auto`` (TD-32).

    Raises:
        ValueError: The model is empty or ``auto``.
    """
    if not model.strip():
        raise ValueError("model must not be empty")  # noqa: EM101, TRY003
    if model.strip().lower() == "auto":
        raise ValueError("model must be named; auto is never used (TD-32)")  # noqa: EM101, TRY003
    return model


class ProfileEntry(Record):
    """One detected project fact with its evidence (DR1); an HTTP 403 on rules is unknown."""

    state: Literal["known", "unknown", "unsupported"]
    value: str = ""
    evidence: str = ""


class RoleModel(Record):
    """The model, reasoning effort and context tier one session role runs with (TD-27)."""

    model: str
    effort: Effort
    context: Context = "default"

    @model_validator(mode="after")
    def _valid(self) -> RoleModel:
        """A named model, never ``auto`` (TD-32)."""
        named(self.model)
        return self


class Profile(Record):
    """The confirmed project profile; a new version is a premise change."""

    format: int = PROFILE_FORMAT
    version: int = 0
    confirmed_at: datetime | None = None
    entries: dict[str, ProfileEntry] = Field(default_factory=dict)
    runtime: Runtime = "managed"  # TD-35: managed runs agent steps through the SDK; vscode runs them in VS Code


WINDOW_PAUSED = True  # TD-137: until the window probes pass, every agent step runs through the SDK
PAUSED_NOTE = "window steps are paused until the window probes pass (TD-137); agent steps run through the SDK"


def in_window(profile: Profile | None) -> bool:
    """Whether agent steps run in a VS Code window: the profile says so and window steps are not paused."""
    return not WINDOW_PAUSED and (profile or Profile()).runtime == "vscode"
