"""Target-bound verification profile authority."""

from __future__ import annotations

import hashlib
import subprocess
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from owlbear_delivery.git_executable import resolve_git_executable

INTEGRATION_VERIFICATION_PROFILE_PATH = ".owlbear/delivery/verification.json"
_COMMIT_LENGTH = 40


class _VerificationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class IntegrationVerificationStep(_VerificationModel):
    """One ordered argv verification step."""

    step_id: str = Field(max_length=128, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    argv: tuple[Annotated[str, Field(min_length=1, max_length=1_024)], ...] = Field(min_length=1)
    cwd: str = Field(default=".", min_length=1, max_length=512)
    timeout_seconds: int = Field(gt=0, le=3_600)

    @model_validator(mode="after")
    def _validate_cwd(self) -> IntegrationVerificationStep:
        path = PurePosixPath(self.cwd)
        if path.is_absolute() or ".." in path.parts:
            message = "verification cwd must stay within the candidate checkout"
            raise ValueError(message)
        return self


class IntegrationVerificationProfile(_VerificationModel):
    """Tracked project policy governing every Integration candidate."""

    schema_version: Literal[1]
    pass_environment: tuple[str, ...] = Field(max_length=32)
    steps: tuple[IntegrationVerificationStep, ...] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def _validate_unique_values(self) -> IntegrationVerificationProfile:
        step_ids = tuple(step.step_id for step in self.steps)
        if len(step_ids) != len(set(step_ids)):
            message = "verification step IDs must be unique"
            raise ValueError(message)
        if len(self.pass_environment) != len(set(self.pass_environment)):
            message = "verification environment names must be unique"
            raise ValueError(message)
        for name in self.pass_environment:
            if not name or not name.replace("_", "A").isalnum() or not name[0].isalpha():
                message = "verification environment names must be portable identifiers"
                raise ValueError(message)
        return self


class IntegrationVerificationProfileState(StrEnum):
    """Authority state observed while binding a verification request."""

    CONFIGURED = "configured"
    UNCONFIGURED = "unconfigured"
    INVALID = "invalid"
    CHANGED = "changed"


class TargetVerificationProfile(_VerificationModel):
    """Validated verification authority read only from one exact target commit."""

    target_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    profile_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    profile: IntegrationVerificationProfile


def read_target_verification_profile(repository: Path, target_commit: str) -> TargetVerificationProfile:
    """Read and validate verification authority from the engine-selected target commit."""
    if len(target_commit) != _COMMIT_LENGTH or any(character not in "0123456789abcdef" for character in target_commit):
        message = "target verification profile requires one exact commit"
        raise ValueError(message)
    result = subprocess.run(  # noqa: S603 - fixed executable and argument vector.
        (
            resolve_git_executable(),
            "-C",
            str(repository.resolve()),
            "show",
            f"{target_commit}:{INTEGRATION_VERIFICATION_PROFILE_PATH}",
        ),
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        message = "target verification profile is missing"
        raise ValueError(message)
    try:
        profile = IntegrationVerificationProfile.model_validate_json(result.stdout)
    except ValidationError as exc:
        message = "target verification profile is invalid"
        raise ValueError(message) from exc
    return TargetVerificationProfile(
        target_commit=target_commit,
        profile_digest=hashlib.sha256(result.stdout).hexdigest(),
        profile=profile,
    )


__all__ = [
    "INTEGRATION_VERIFICATION_PROFILE_PATH",
    "IntegrationVerificationProfile",
    "IntegrationVerificationProfileState",
    "IntegrationVerificationStep",
    "TargetVerificationProfile",
    "read_target_verification_profile",
]
