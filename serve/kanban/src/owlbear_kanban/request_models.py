"""Pydantic models for structured decision/action requests.

These models validate request frontmatter content used by decision request files.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, ClassVar, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

UUID4_VERSION = 4
ERR_UUID4 = "request_id must be a valid UUID4 string"
ERR_CREATED_AT = "created_at must be an ISO 8601 datetime string"
ERR_CREATED_AT_TZ = "created_at must include timezone information"
ERR_ONE_RECOMMENDED = "at most one option can have recommended=true"


class RequestOption(BaseModel):
    """One candidate option in a decision request."""

    model_config = ConfigDict(extra="forbid")

    option_id: str = Field(
        min_length=2,
        max_length=63,
        pattern=r"^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$",
    )
    label: str = Field(max_length=120)
    confidence: float = Field(ge=0.0, le=1.0)
    recommended: bool
    rationale: str = Field(max_length=500)


class Resolution(BaseModel):
    """Resolution payload for either decision or action requests."""

    model_config = ConfigDict(extra="forbid")

    selected_option_id: str | None = None
    free_text: str | None = None
    resolved_at: str | None = None


class _RequestBase(BaseModel):
    """Shared fields and validation for request models."""

    model_config = ConfigDict(extra="forbid")

    task_id: int
    request_id: str
    title: str = Field(max_length=120)
    summary: str
    agent: str
    created_at: str
    resolution: Resolution = Field(default_factory=Resolution)

    @field_validator("request_id")
    @classmethod
    def _validate_request_id(cls, value: str) -> str:
        try:
            parsed = UUID(value)
        except ValueError as exc:
            msg = ERR_UUID4
            raise ValueError(msg) from exc
        if parsed.version != UUID4_VERSION:
            msg = ERR_UUID4
            raise ValueError(msg)
        return value

    @field_validator("created_at")
    @classmethod
    def _validate_created_at(cls, value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            msg = ERR_CREATED_AT
            raise ValueError(msg) from exc
        if parsed.tzinfo is None:
            msg = ERR_CREATED_AT_TZ
            raise ValueError(msg)
        return value


class DecisionRequest(_RequestBase):
    """Structured decision request."""

    kind: Literal["decision"]
    options: list[RequestOption] = Field(min_length=2, max_length=10)

    @model_validator(mode="after")
    def _validate_recommended_count(self) -> DecisionRequest:
        if sum(1 for option in self.options if option.recommended) > 1:
            msg = ERR_ONE_RECOMMENDED
            raise ValueError(msg)
        return self


class ActionRequest(_RequestBase):
    """Structured action request."""

    kind: Literal["action"]
    options: list[RequestOption] = Field(default_factory=list, max_length=0)


RequestType = Annotated[DecisionRequest | ActionRequest, Field(discriminator="kind")]


class Request:
    """Convenience validator for discriminated request payloads."""

    _adapter: ClassVar[TypeAdapter[RequestType]] = TypeAdapter(RequestType)

    @classmethod
    def model_validate(cls, data: object) -> DecisionRequest | ActionRequest:
        """Validate and dispatch a payload to the matching request model."""
        return cls._adapter.validate_python(data)
