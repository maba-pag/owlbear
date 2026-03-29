"""NDJSON protocol models for voice addon communication."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

# ---------------------------------------------------------------------------
# VoiceState type alias
# ---------------------------------------------------------------------------

VoiceState = Literal["ready", "listening", "speaking", "idle", "shutdown"]

# ---------------------------------------------------------------------------
# VoiceOutMessage models (addon -> orchestrator)
# ---------------------------------------------------------------------------


class TranscriptMsg(BaseModel):
    """Final or interim transcript from the voice addon."""

    model_config = ConfigDict(frozen=True)

    type: Literal["transcript"] = "transcript"
    text: str
    line_idx: int
    final: bool


class PartialMsg(BaseModel):
    """Partial (in-progress) transcript token from the voice addon."""

    model_config = ConfigDict(frozen=True)

    type: Literal["partial"] = "partial"
    text: str
    line_idx: int


class StatusMsg(BaseModel):
    """Voice addon state change notification."""

    model_config = ConfigDict(frozen=True)

    type: Literal["status"] = "status"
    state: VoiceState


class ErrorMsg(BaseModel):
    """Error report from the voice addon."""

    model_config = ConfigDict(frozen=True)

    type: Literal["error"] = "error"
    code: str
    message: str


# ---------------------------------------------------------------------------
# VoiceInMessage models (orchestrator -> addon)
# ---------------------------------------------------------------------------


class SpeakMsg(BaseModel):
    """Instruct the voice addon to speak text."""

    model_config = ConfigDict(frozen=True)

    type: Literal["speak"] = "speak"
    text: str
    interrupt: bool


class ConfigMsg(BaseModel):
    """Send configuration settings to the voice addon."""

    model_config = ConfigDict(frozen=True)

    type: Literal["config"] = "config"
    settings: dict[str, Any]


class ShutdownMsg(BaseModel):
    """Instruct the voice addon to shut down."""

    model_config = ConfigDict(frozen=True)

    type: Literal["shutdown"] = "shutdown"


# ---------------------------------------------------------------------------
# Discriminated union type aliases
# ---------------------------------------------------------------------------

VoiceOutMessage = Annotated[
    TranscriptMsg | PartialMsg | StatusMsg | ErrorMsg,
    Field(discriminator="type"),
]

VoiceInMessage = Annotated[
    SpeakMsg | ConfigMsg | ShutdownMsg,
    Field(discriminator="type"),
]

# ---------------------------------------------------------------------------
# Module-level TypeAdapter instances (public API)
# ---------------------------------------------------------------------------

out_adapter: TypeAdapter[VoiceOutMessage] = TypeAdapter(VoiceOutMessage)
in_adapter: TypeAdapter[VoiceInMessage] = TypeAdapter(VoiceInMessage)
