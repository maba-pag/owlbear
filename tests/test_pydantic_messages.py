"""Validation tests — PydanticAI message types meet OwlBear's needs.

These tests prove that PydanticAI's message system serializes correctly to JSONL
(the persistence format chosen in #41) and covers the message types OwlBear will
actually use.
"""

from __future__ import annotations

import json

from pydantic import TypeAdapter
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

_msg_ta: TypeAdapter[ModelMessage] = TypeAdapter(ModelMessage)


# ---------------------------------------------------------------------------
# Round-trip serialization for each message type OwlBear needs
# ---------------------------------------------------------------------------


class TestMessageRoundTrip:
    """Every OwlBear-relevant message type survives JSON round-trip."""

    def test_user_prompt_round_trip(self) -> None:
        msg = ModelRequest(parts=[UserPromptPart(content="Hello")])
        raw = _msg_ta.dump_json(msg)
        loaded = _msg_ta.validate_json(raw)
        assert isinstance(loaded, ModelRequest)
        assert loaded.parts[0].content == "Hello"

    def test_text_response_round_trip(self) -> None:
        msg = ModelResponse(parts=[TextPart(content="Hi!")])
        raw = _msg_ta.dump_json(msg)
        loaded = _msg_ta.validate_json(raw)
        assert isinstance(loaded, ModelResponse)
        assert loaded.parts[0].content == "Hi!"

    def test_system_prompt_round_trip(self) -> None:
        msg = ModelRequest(parts=[SystemPromptPart(content="You are OwlBear.")])
        raw = _msg_ta.dump_json(msg)
        loaded = _msg_ta.validate_json(raw)
        assert loaded.parts[0].content == "You are OwlBear."

    def test_tool_call_round_trip(self) -> None:
        msg = ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="read_file",
                    args={"path": "src/main.py"},
                    tool_call_id="tc-1",
                )
            ]
        )
        raw = _msg_ta.dump_json(msg)
        loaded = _msg_ta.validate_json(raw)
        assert isinstance(loaded, ModelResponse)
        part = loaded.parts[0]
        assert isinstance(part, ToolCallPart)
        assert part.tool_name == "read_file"
        assert part.args == {"path": "src/main.py"}

    def test_tool_return_round_trip(self) -> None:
        msg = ModelRequest(
            parts=[
                ToolReturnPart(
                    tool_name="read_file",
                    content="file contents here",
                    tool_call_id="tc-1",
                )
            ]
        )
        raw = _msg_ta.dump_json(msg)
        loaded = _msg_ta.validate_json(raw)
        part = loaded.parts[0]
        assert isinstance(part, ToolReturnPart)
        assert part.content == "file contents here"

    def test_retry_prompt_round_trip(self) -> None:
        msg = ModelRequest(
            parts=[
                RetryPromptPart(
                    content="Try again with valid JSON.",
                    tool_name="parse_json",
                    tool_call_id="tc-2",
                )
            ]
        )
        raw = _msg_ta.dump_json(msg)
        loaded = _msg_ta.validate_json(raw)
        part = loaded.parts[0]
        assert isinstance(part, RetryPromptPart)
        assert part.content == "Try again with valid JSON."


# ---------------------------------------------------------------------------
# Multi-message conversation round-trip
# ---------------------------------------------------------------------------


class TestConversationRoundTrip:
    """A full multi-turn conversation survives JSONL persistence."""

    def test_multi_turn_jsonl(self) -> None:
        conversation: list[ModelMessage] = [
            ModelRequest(
                parts=[
                    SystemPromptPart(content="You are OwlBear."),
                    UserPromptPart(content="Read file x.py"),
                ]
            ),
            ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="read_file",
                        args={"path": "x.py"},
                        tool_call_id="tc-1",
                    )
                ]
            ),
            ModelRequest(
                parts=[
                    ToolReturnPart(
                        tool_name="read_file",
                        content="print('hello')",
                        tool_call_id="tc-1",
                    )
                ]
            ),
            ModelResponse(parts=[TextPart(content="The file prints hello.")]),
        ]

        # Serialize each message as one JSON line (JSONL format)
        lines = [_msg_ta.dump_json(m).decode("utf-8") for m in conversation]
        jsonl = "\n".join(lines) + "\n"

        # Verify each line is valid JSON
        for line in jsonl.strip().splitlines():
            json.loads(line)

        # Deserialize and verify types
        loaded = [_msg_ta.validate_json(line) for line in jsonl.strip().splitlines()]
        assert len(loaded) == 4
        assert isinstance(loaded[0], ModelRequest)
        assert isinstance(loaded[1], ModelResponse)
        assert isinstance(loaded[2], ModelRequest)
        assert isinstance(loaded[3], ModelResponse)


# ---------------------------------------------------------------------------
# Discriminator field verification
# ---------------------------------------------------------------------------


class TestMessageDiscriminators:
    """PydanticAI uses 'kind' and 'part_kind' for polymorphic deserialization."""

    def test_request_has_kind_request(self) -> None:
        msg = ModelRequest(parts=[])
        data = json.loads(_msg_ta.dump_json(msg))
        assert data["kind"] == "request"

    def test_response_has_kind_response(self) -> None:
        msg = ModelResponse(parts=[])
        data = json.loads(_msg_ta.dump_json(msg))
        assert data["kind"] == "response"

    def test_user_prompt_part_kind(self) -> None:
        part = UserPromptPart(content="hi")
        data = json.loads(_msg_ta.dump_json(ModelRequest(parts=[part])))
        assert data["parts"][0]["part_kind"] == "user-prompt"

    def test_text_part_kind(self) -> None:
        part = TextPart(content="hi")
        data = json.loads(_msg_ta.dump_json(ModelResponse(parts=[part])))
        assert data["parts"][0]["part_kind"] == "text"

    def test_tool_call_part_kind(self) -> None:
        part = ToolCallPart(tool_name="x", args={}, tool_call_id="t")
        data = json.loads(_msg_ta.dump_json(ModelResponse(parts=[part])))
        assert data["parts"][0]["part_kind"] == "tool-call"
