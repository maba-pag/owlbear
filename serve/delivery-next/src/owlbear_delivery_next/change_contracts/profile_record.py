"""The confirmed project profile and the per-role model settings it carries (DR1, TD-27, TD-32)."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - pydantic resolves annotations at runtime
from typing import Literal

from pydantic import Field, model_validator

from owlbear_delivery_next.change_contracts.models import Context, Effort, Record

PROFILE_FORMAT = 5  # 2: role overrides moved to config.json; 3: preference import; 4: its basis; 5: no runtime switch


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
    """A detected fact or confirmed intent; ``observed`` binds the latter to the complete raw observation.

    The owner's replacement value is not the observation. An HTTP 403 on rules remains unknown.
    """

    state: Literal["known", "unknown", "unsupported"]
    value: str = ""
    evidence: str = ""
    observed: str = Field(default="", pattern=r"^(?:[0-9a-f]{64})?$", exclude_if=lambda value: not value)


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
    prefs_import: Literal["", "pending", "done"] = ""  # R15: the one-time legacy import; "done" is permanent
    prefs_basis: str = ""  # R15: while pending, the project config's digest at the claim ("absent" if none); else ""
    prefs_claim: str | None = None  # R15: the nonce of the claim attempt that wrote "pending"; None on older profiles
