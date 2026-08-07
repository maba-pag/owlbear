"""Behavioral tests for the session-review transcript extractor."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import types

_SCRIPT = Path(__file__).parents[1] / "scripts" / "extract_transcript.py"
_EXPECTED_TURNS = 2


def _load() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("extract_transcript", _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def extractor() -> types.ModuleType:
    """Load the direct-run extractor as a test module."""
    return _load()


@pytest.fixture
def transcript(tmp_path: Path) -> Path:
    """Create a representative transcript fixture."""
    path = tmp_path / "session.jsonl"
    events = (
        {
            "type": "session.start",
            "id": "event-1",
            "timestamp": "2026-08-05T10:00:00Z",
            "parentId": None,
            "data": {"sessionId": "11111111-1111-4111-8111-111111111111", "producer": "copilot"},
        },
        {
            "type": "user.message",
            "id": "event-2",
            "timestamp": "2026-08-05T10:01:00Z",
            "parentId": "event-1",
            "data": {"content": "first request token=visible-secret", "attachments": []},
        },
        {
            "type": "assistant.message",
            "id": "event-3",
            "timestamp": "2026-08-05T10:01:01Z",
            "parentId": "event-2",
            "data": {
                "content": "checking the workspace",
                "reasoningText": "private chain of thought",
                "toolRequests": [
                    {
                        "toolCallId": "call-1",
                        "name": "read_file",
                        "arguments": {"filePath": "README.md", "api_key": "visible-secret"},
                        "type": "function",
                    }
                ],
            },
        },
        {
            "type": "tool.execution_start",
            "id": "event-4",
            "timestamp": "2026-08-05T10:01:02Z",
            "parentId": "event-3",
            "data": {
                "toolCallId": "call-1",
                "toolName": "read_file",
                "arguments": {"filePath": "README.md", "api_key": "visible-secret"},
            },
        },
        {
            "type": "tool.execution_complete",
            "id": "event-5",
            "timestamp": "2026-08-05T10:01:03Z",
            "parentId": "event-4",
            "data": {"toolCallId": "call-1", "success": True},
        },
        {
            "type": "user.message",
            "id": "event-6",
            "timestamp": "2026-08-05T10:02:00Z",
            "parentId": "event-5",
            "data": {"content": "second request with marker lifecycle-proof", "attachments": []},
        },
        {
            "type": "assistant.message",
            "id": "event-7",
            "timestamp": "2026-08-05T10:02:01Z",
            "parentId": "event-6",
            "data": {"content": "a long response", "reasoningText": "do not emit", "toolRequests": []},
        },
    )
    path.write_text("".join(f"{json.dumps(event)}\n" for event in events), encoding="utf-8")
    return path


@pytest.fixture
def nested_transcript(tmp_path: Path) -> Path:
    """Create a transcript with one parent turn and one nested agent invocation."""
    path = tmp_path / "nested-session.jsonl"
    events = (
        {
            "type": "session.start",
            "id": "event-1",
            "timestamp": "2026-08-05T10:00:00Z",
            "parentId": None,
            "data": {"sessionId": "22222222-2222-4222-8222-222222222222", "producer": "copilot"},
        },
        {
            "type": "assistant.message",
            "id": "event-2",
            "timestamp": "2026-08-05T10:00:01Z",
            "parentId": "event-1",
            "data": {
                "content": "parent preamble",
                "toolRequests": [
                    {
                        "toolCallId": "call-agent",
                        "name": "runSubagent",
                        "arguments": {"agentName": "builder", "prompt": "nested prompt"},
                    }
                ],
            },
        },
        {
            "type": "tool.execution_start",
            "id": "event-3",
            "timestamp": "2026-08-05T10:00:02Z",
            "parentId": "event-2",
            "data": {
                "toolCallId": "call-agent",
                "toolName": "runSubagent",
                "arguments": {"agentName": "builder", "prompt": "nested prompt"},
            },
        },
        {
            "type": "user.message",
            "id": "event-4",
            "timestamp": "2026-08-05T10:00:03Z",
            "parentId": "event-3",
            "data": {"content": "nested prompt", "attachments": []},
        },
        {
            "type": "assistant.message",
            "id": "event-5",
            "timestamp": "2026-08-05T10:00:04Z",
            "parentId": "event-4",
            "data": {
                "content": "nested response",
                "toolRequests": [
                    {
                        "toolCallId": "call-read",
                        "name": "read_file",
                        "arguments": {"filePath": "README.md"},
                    }
                ],
            },
        },
        {
            "type": "tool.execution_start",
            "id": "event-6",
            "timestamp": "2026-08-05T10:00:05Z",
            "parentId": "event-5",
            "data": {
                "toolCallId": "call-read",
                "toolName": "read_file",
                "arguments": {"filePath": "README.md"},
            },
        },
        {
            "type": "tool.execution_complete",
            "id": "event-7",
            "timestamp": "2026-08-05T10:00:06Z",
            "parentId": "event-6",
            "data": {"toolCallId": "call-read", "success": True},
        },
        {
            "type": "tool.execution_complete",
            "id": "event-8",
            "timestamp": "2026-08-05T10:00:07Z",
            "parentId": "event-7",
            "data": {"toolCallId": "call-agent", "success": True},
        },
        {
            "type": "assistant.message",
            "id": "event-9",
            "timestamp": "2026-08-05T10:00:08Z",
            "parentId": "event-8",
            "data": {
                "content": "parent resumes",
                "toolRequests": [
                    {
                        "toolCallId": "call-integrate",
                        "name": "integrate_ready_change",
                        "arguments": {"change_id": "example"},
                    }
                ],
            },
        },
        {
            "type": "assistant.turn_start",
            "id": "event-10",
            "timestamp": "2026-08-05T10:00:09Z",
            "parentId": "event-9",
            "data": {"turnId": "9"},
        },
    )
    path.write_text("".join(f"{json.dumps(event)}\n" for event in events), encoding="utf-8")
    return path


def test_extracts_turns_tools_and_redacts_sensitive_values(
    extractor: types.ModuleType,
    transcript: Path,
) -> None:
    """Extract messages and tool evidence without leaking private fields."""
    config = extractor.ExtractConfig(max_content_chars=100, include_tools=True, include_tool_arguments=True)

    metadata, turns = extractor.extract_turns(transcript, config)

    assert metadata["turn_count"] == _EXPECTED_TURNS
    assert turns[0].user == "first request token=<redacted>"
    assert turns[0].assistant == ["checking the workspace"]
    assert len(turns[0].tools) == 1
    assert turns[0].tools[0].name == "read_file"
    assert turns[0].tools[0].success is True
    assert turns[0].tools[0].arguments == {"filePath": "README.md", "api_key": "<redacted>"}
    rendered = extractor.render_json(metadata, turns)
    assert "private chain of thought" not in rendered
    assert "visible-secret" not in rendered


def test_selects_matching_turn_with_context(extractor: types.ModuleType, transcript: Path) -> None:
    """Include a matching turn and the requested neighboring context."""
    config = extractor.ExtractConfig(max_content_chars=100, include_tools=False, include_tool_arguments=False)
    _, turns = extractor.extract_turns(transcript, config)

    selected = extractor.select_turns(
        turns,
        extractor.TurnSelection(
            from_turn=None,
            to_turn=None,
            last_turns=None,
            around="LIFECYCLE-PROOF",
            context_turns=1,
        ),
    )

    assert [turn.index for turn in selected] == [1, 2]


def test_bounds_content_and_omits_tools_by_default(extractor: types.ModuleType, transcript: Path) -> None:
    """Bound message content and keep tool evidence opt-in."""
    config = extractor.ExtractConfig(max_content_chars=8, include_tools=False, include_tool_arguments=False)

    _, turns = extractor.extract_turns(transcript, config)

    assert turns[0].user.startswith("first re")
    assert "chars omitted" in turns[0].user
    assert turns[0].tools == []


def test_retains_only_bounded_tail_while_preserving_total_count(
    extractor: types.ModuleType,
    transcript: Path,
) -> None:
    """Retain a bounded tail without losing the total turn count."""
    config = extractor.ExtractConfig(max_content_chars=100, include_tools=False, include_tool_arguments=False)

    metadata, turns = extractor.extract_turns(transcript, config, retain_last=1)

    assert metadata["turn_count"] == _EXPECTED_TURNS
    assert [turn.index for turn in turns] == [2]


def test_preserves_parent_turn_across_nested_agent_invocation(
    extractor: types.ModuleType,
    nested_transcript: Path,
) -> None:
    """Keep nested prompts and events inside their owning top-level turn."""
    config = extractor.ExtractConfig(max_content_chars=100, include_tools=True, include_tool_arguments=False)

    metadata, turns = extractor.extract_turns(nested_transcript, config)

    assert metadata["turn_count"] == 1
    assert metadata["synthetic_turn_count"] == 1
    assert len(turns) == 1
    assert turns[0].user == "<session input unavailable in raw transcript>"
    assert turns[0].nested_users == ["nested prompt"]
    assert turns[0].assistant == ["parent preamble", "nested response", "parent resumes"]
    assert [(tool.name, tool.started, tool.success) for tool in turns[0].tools] == [
        ("runSubagent", True, True),
        ("read_file", True, True),
        ("integrate_ready_change", False, None),
    ]


def test_reports_unresolved_tool_request_at_raw_transcript_tail(
    extractor: types.ModuleType,
    nested_transcript: Path,
) -> None:
    """Expose raw-tail loss instead of implying that requested tools completed."""
    config = extractor.ExtractConfig(max_content_chars=100, include_tools=True, include_tool_arguments=False)

    metadata, turns = extractor.extract_turns(nested_transcript, config)

    assert metadata["last_event_type"] == "assistant.turn_start"
    assert metadata["last_event_timestamp"] == "2026-08-05T10:00:09Z"
    assert metadata["incomplete_tool_calls"] == [
        {
            "name": "integrate_ready_change",
            "tool_call_id": "call-integrate",
            "state": "requested",
        }
    ]
    rendered = extractor.render_markdown(metadata, turns)
    assert "1 tool call lacks a completion record" in rendered


def test_bounds_tool_arguments_after_redaction(extractor: types.ModuleType, transcript: Path) -> None:
    """Redact and cap tool arguments before rendering them."""
    config = extractor.ExtractConfig(max_content_chars=20, include_tools=True, include_tool_arguments=True)

    _, turns = extractor.extract_turns(transcript, config)

    arguments = turns[0].tools[0].arguments
    assert isinstance(arguments, str)
    assert "chars omitted" in arguments
    assert "visible-secret" not in arguments


def test_locates_exact_session_without_recursive_scan(extractor: types.ModuleType, tmp_path: Path) -> None:
    """Locate a transcript through the stable workspace-storage shape."""
    session_id = "11111111-1111-4111-8111-111111111111"
    transcript = tmp_path / "workspace" / "GitHub.copilot-chat" / "transcripts" / f"{session_id}.jsonl"
    transcript.parent.mkdir(parents=True)
    transcript.write_text("", encoding="utf-8")

    assert extractor.locate_transcript(session_id, (tmp_path,)) == transcript


def test_rejects_malformed_json(extractor: types.ModuleType, tmp_path: Path) -> None:
    """Fail with bounded location evidence for malformed records."""
    transcript = tmp_path / "broken.jsonl"
    transcript.write_text('{"type": "user.message"}\nnot-json\n', encoding="utf-8")
    config = extractor.ExtractConfig(max_content_chars=100, include_tools=False, include_tool_arguments=False)

    with pytest.raises(ValueError, match="invalid JSON"):
        extractor.extract_turns(transcript, config)
