"""Immutable attempt lifecycle event contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError as PydanticValidationError

from owlbear_kanban.change import Digest

if TYPE_CHECKING:
    from collections.abc import Mapping

AttemptEventKind = Literal["started", "released", "failed", "crashed", "succeeded"]


class AttemptEventDiagnosticCode(StrEnum):
    """Stable attempt event parser diagnostic codes."""

    UNKNOWN_FIELD = "ERR_ATTEMPT_EVENT_FIELD_UNKNOWN"
    IDENTITY_INVALID = "ERR_ATTEMPT_EVENT_IDENTITY_INVALID"
    REFERENCE_INVALID = "ERR_ATTEMPT_EVENT_REFERENCE_INVALID"
    SEQUENCE_INVALID = "ERR_ATTEMPT_EVENT_SEQUENCE_INVALID"
    KIND_INVALID = "ERR_ATTEMPT_EVENT_KIND_INVALID"
    REQUIRED_REFERENCE_MISSING = "ERR_ATTEMPT_EVENT_REFERENCE_MISSING"
    SCHEMA_INVALID = "ERR_ATTEMPT_EVENT_SCHEMA_INVALID"


class _AttemptEventModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class AttemptEvent(_AttemptEventModel):
    """One schema-version-one append-only attempt lifecycle event."""

    schema_version: Literal[1]
    attempt_id: str = Field(min_length=1)
    job_id: int = Field(gt=0)
    change_id: str = Field(min_length=1)
    delivery_digest: Digest
    target_node_id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    process_id: str = Field(min_length=1)
    sequence: int = Field(gt=0)
    timestamp: str = Field(min_length=1)
    kind: AttemptEventKind
    detail: str | None = None
    evidence_ids: tuple[str, ...] = ()


class AttemptEventDiagnostic(_AttemptEventModel):
    code: AttemptEventDiagnosticCode
    detail: str


class AttemptEventParseResult(_AttemptEventModel):
    event: AttemptEvent | None = None
    diagnostics: tuple[AttemptEventDiagnostic, ...] = ()

    def model_post_init(self, __context: object, /) -> None:
        if (self.event is None) == (not self.diagnostics):
            msg = "attempt event result must contain either one event or diagnostics"
            raise ValueError(msg)


def _diagnostic_from_validation(exc: PydanticValidationError) -> AttemptEventDiagnosticCode:
    message = str(exc)
    code = AttemptEventDiagnosticCode.SCHEMA_INVALID
    if "Extra inputs" in message:
        code = AttemptEventDiagnosticCode.UNKNOWN_FIELD
    elif "sequence" in message:
        code = AttemptEventDiagnosticCode.SEQUENCE_INVALID
    elif "kind" in message:
        code = AttemptEventDiagnosticCode.KIND_INVALID
    elif "Field required" in message and any(
        field in message for field in ("job_id", "change_id", "delivery_digest", "target_node_id", "evidence_ids")
    ):
        code = AttemptEventDiagnosticCode.REQUIRED_REFERENCE_MISSING
    elif any(
        field in message for field in ("job_id", "change_id", "delivery_digest", "target_node_id", "evidence_ids")
    ):
        code = AttemptEventDiagnosticCode.REFERENCE_INVALID
    elif any(field in message for field in ("attempt_id", "actor_id", "process_id")):
        code = AttemptEventDiagnosticCode.IDENTITY_INVALID
    return code


def parse_attempt_event_mapping(value: Mapping[str, object]) -> AttemptEventParseResult:
    """Parse a schema-version-one attempt event mapping with stable diagnostics."""
    normalized = dict(value)
    if isinstance(normalized.get("evidence_ids"), list):
        normalized["evidence_ids"] = tuple(normalized["evidence_ids"])
    try:
        event = AttemptEvent.model_validate(normalized)
    except PydanticValidationError as exc:
        return AttemptEventParseResult(
            diagnostics=(AttemptEventDiagnostic(code=_diagnostic_from_validation(exc), detail=str(exc)),)
        )
    return AttemptEventParseResult(event=event)


def serialize_attempt_event_mapping(event: AttemptEvent) -> dict[str, object]:
    """Serialize an attempt event as a schema-version-one JSON-compatible mapping."""
    return event.model_dump(mode="json")
