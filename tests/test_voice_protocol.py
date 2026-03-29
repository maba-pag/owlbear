"""Failing tests for voice protocol Pydantic models (task #112).

Covers: round-trip serialization (7), discriminator field presence (7),
union type selection via isinstance (7), unknown type rejection (2),
and missing required field rejection (2).

All tests fail on current HEAD because
``packages/orchestrator/src/owlbear/voice/protocol.py``
does not yet exist.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from owlbear.voice.protocol import (
    ConfigMsg,
    ErrorMsg,
    PartialMsg,
    ShutdownMsg,
    SpeakMsg,
    StatusMsg,
    TranscriptMsg,
    in_adapter,
    out_adapter,
)


# ---------------------------------------------------------------------------
# Round-trip tests (7): model_dump_json() → adapter.validate_json() preserves fields
# ---------------------------------------------------------------------------


class TestFromAC_RoundTrip:  # noqa: N801
    """model_dump_json() then adapter.validate_json() preserves all fields per model."""

    def test_transcript_msg_round_trip(self) -> None:
        msg = TranscriptMsg(text="hello world", line_idx=3, final=True)
        restored = out_adapter.validate_json(msg.model_dump_json())
        assert restored.text == "hello world"
        assert restored.line_idx == 3
        assert restored.final is True

    def test_partial_msg_round_trip(self) -> None:
        msg = PartialMsg(text="hel", line_idx=2)
        restored = out_adapter.validate_json(msg.model_dump_json())
        assert restored.text == "hel"
        assert restored.line_idx == 2

    def test_status_msg_round_trip(self) -> None:
        msg = StatusMsg(state="listening")
        restored = out_adapter.validate_json(msg.model_dump_json())
        assert restored.state == "listening"

    def test_error_msg_round_trip(self) -> None:
        msg = ErrorMsg(code="ERR_TIMEOUT", message="connection timed out")
        restored = out_adapter.validate_json(msg.model_dump_json())
        assert restored.code == "ERR_TIMEOUT"
        assert restored.message == "connection timed out"

    def test_speak_msg_round_trip(self) -> None:
        msg = SpeakMsg(text="say this aloud", interrupt=False)
        restored = in_adapter.validate_json(msg.model_dump_json())
        assert restored.text == "say this aloud"
        assert restored.interrupt is False

    def test_config_msg_round_trip(self) -> None:
        msg = ConfigMsg(settings={"volume": 0.8, "language": "en"})
        restored = in_adapter.validate_json(msg.model_dump_json())
        assert restored.settings == {"volume": 0.8, "language": "en"}

    def test_shutdown_msg_round_trip(self) -> None:
        msg = ShutdownMsg()
        restored = in_adapter.validate_json(msg.model_dump_json())
        assert isinstance(restored, ShutdownMsg)


# ---------------------------------------------------------------------------
# Discriminator tests (7): serialized JSON contains correct "type" value
# ---------------------------------------------------------------------------


class TestFromAC_DiscriminatorField:  # noqa: N801
    """Serialized JSON contains the correct ``type`` discriminator value per model."""

    def test_transcript_msg_type_value(self) -> None:
        data = json.loads(TranscriptMsg(text="x", line_idx=0, final=False).model_dump_json())
        assert data["type"] == "transcript"

    def test_partial_msg_type_value(self) -> None:
        data = json.loads(PartialMsg(text="x", line_idx=1).model_dump_json())
        assert data["type"] == "partial"

    def test_status_msg_type_value(self) -> None:
        data = json.loads(StatusMsg(state="ready").model_dump_json())
        assert data["type"] == "status"

    def test_error_msg_type_value(self) -> None:
        data = json.loads(ErrorMsg(code="e", message="m").model_dump_json())
        assert data["type"] == "error"

    def test_speak_msg_type_value(self) -> None:
        data = json.loads(SpeakMsg(text="x", interrupt=True).model_dump_json())
        assert data["type"] == "speak"

    def test_config_msg_type_value(self) -> None:
        data = json.loads(ConfigMsg(settings={}).model_dump_json())
        assert data["type"] == "config"

    def test_shutdown_msg_type_value(self) -> None:
        data = json.loads(ShutdownMsg().model_dump_json())
        assert data["type"] == "shutdown"


# ---------------------------------------------------------------------------
# Type-select tests (7): validate_json() returns correct concrete type
# ---------------------------------------------------------------------------


class TestFromAC_TypeSelect:  # noqa: N801
    """validate_json() returns the correct concrete model type via isinstance()."""

    def test_out_adapter_selects_transcript_msg(self) -> None:
        raw = '{"type":"transcript","text":"hi","line_idx":0,"final":true}'
        result = out_adapter.validate_json(raw)
        assert isinstance(result, TranscriptMsg)

    def test_out_adapter_selects_partial_msg(self) -> None:
        raw = '{"type":"partial","text":"hi","line_idx":1}'
        result = out_adapter.validate_json(raw)
        assert isinstance(result, PartialMsg)

    def test_out_adapter_selects_status_msg(self) -> None:
        raw = '{"type":"status","state":"idle"}'
        result = out_adapter.validate_json(raw)
        assert isinstance(result, StatusMsg)

    def test_out_adapter_selects_error_msg(self) -> None:
        raw = '{"type":"error","code":"ERR","message":"fail"}'
        result = out_adapter.validate_json(raw)
        assert isinstance(result, ErrorMsg)

    def test_in_adapter_selects_speak_msg(self) -> None:
        raw = '{"type":"speak","text":"hello","interrupt":false}'
        result = in_adapter.validate_json(raw)
        assert isinstance(result, SpeakMsg)

    def test_in_adapter_selects_config_msg(self) -> None:
        raw = '{"type":"config","settings":{"rate":1.0}}'
        result = in_adapter.validate_json(raw)
        assert isinstance(result, ConfigMsg)

    def test_in_adapter_selects_shutdown_msg(self) -> None:
        raw = '{"type":"shutdown"}'
        result = in_adapter.validate_json(raw)
        assert isinstance(result, ShutdownMsg)


# ---------------------------------------------------------------------------
# Unknown-type rejection tests (2): ValidationError for both unions
# ---------------------------------------------------------------------------


class TestFromAC_UnknownTypeRejection:  # noqa: N801
    """``{"type":"unknown"}`` raises ValidationError for both adapter unions."""

    def test_out_adapter_rejects_unknown_type(self) -> None:
        with pytest.raises(ValidationError):
            out_adapter.validate_json('{"type":"unknown"}')

    def test_in_adapter_rejects_unknown_type(self) -> None:
        with pytest.raises(ValidationError):
            in_adapter.validate_json('{"type":"unknown"}')


# ---------------------------------------------------------------------------
# Missing required field tests (2): ValidationError when required field absent
# ---------------------------------------------------------------------------


class TestFromAC_MissingRequiredField:  # noqa: N801
    """Omitting a required field raises ValidationError."""

    def test_out_adapter_raises_on_missing_text(self) -> None:
        # TranscriptMsg requires text — omit it
        with pytest.raises(ValidationError):
            out_adapter.validate_json('{"type":"transcript","line_idx":0,"final":true}')

    def test_in_adapter_raises_on_missing_interrupt(self) -> None:
        # SpeakMsg requires interrupt — omit it
        with pytest.raises(ValidationError):
            in_adapter.validate_json('{"type":"speak","text":"hello"}')


# ---------------------------------------------------------------------------
# Frozen immutability tests (7): AC requires frozen=True on all models
# ---------------------------------------------------------------------------


class TestFromAC_FrozenImmutability:  # noqa: N801
    """All 7 models use frozen=True — mutation of any field raises ValidationError."""

    def test_transcript_msg_is_frozen(self) -> None:
        msg = TranscriptMsg(text="hello", line_idx=0, final=False)
        with pytest.raises(ValidationError):
            msg.text = "mutated"  # type: ignore[misc]

    def test_partial_msg_is_frozen(self) -> None:
        msg = PartialMsg(text="hel", line_idx=1)
        with pytest.raises(ValidationError):
            msg.line_idx = 99  # type: ignore[misc]

    def test_status_msg_is_frozen(self) -> None:
        msg = StatusMsg(state="ready")
        with pytest.raises(ValidationError):
            msg.state = "idle"  # type: ignore[misc]

    def test_error_msg_is_frozen(self) -> None:
        msg = ErrorMsg(code="ERR", message="fail")
        with pytest.raises(ValidationError):
            msg.code = "OTHER"  # type: ignore[misc]

    def test_speak_msg_is_frozen(self) -> None:
        msg = SpeakMsg(text="say this", interrupt=True)
        with pytest.raises(ValidationError):
            msg.interrupt = False  # type: ignore[misc]

    def test_config_msg_is_frozen(self) -> None:
        msg = ConfigMsg(settings={"vol": 1.0})
        with pytest.raises(ValidationError):
            msg.settings = {}  # type: ignore[misc]

    def test_shutdown_msg_is_frozen(self) -> None:
        msg = ShutdownMsg()
        with pytest.raises(ValidationError):
            msg.type = "other"  # type: ignore[misc]
