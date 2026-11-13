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


@pytest.fixture
def extractor() -> types.ModuleType:
    """Load the direct-run extractor."""
    spec = importlib.util.spec_from_file_location("extract_transcript", _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _transcript(tmp_path: Path, name: str, events: list[tuple[str, dict[str, object]]]) -> Path:
    path = tmp_path / name
    records = [
        {
            "type": kind,
            "id": f"event-{index + 1}",
            "timestamp": f"2026-08-05T10:00:{index:02}Z",
            "parentId": f"event-{index}" if index else None,
            "data": data,
        }
        for index, (kind, data) in enumerate(events)
    ]
    path.write_text("".join(f"{json.dumps(event)}\n" for event in records), encoding="utf-8")
    return path


@pytest.fixture
def transcript(tmp_path: Path) -> Path:
    """Two top-level turns with sensitive content and tool arguments."""
    request = {
        "toolCallId": "call-1",
        "name": "read_file",
        "arguments": {"filePath": "README.md", "api_key": "visible-secret"},
        "type": "function",
    }
    return _transcript(
        tmp_path,
        "session.jsonl",
        [
            ("session.start", {"sessionId": "11111111-1111-4111-8111-111111111111", "producer": "copilot"}),
            ("user.message", {"content": "first request token=visible-secret", "attachments": []}),
            (
                "assistant.message",
                {
                    "content": "checking the workspace",
                    "reasoningText": "private chain of thought",
                    "toolRequests": [request],
                },
            ),
            (
                "tool.execution_start",
                {
                    "toolCallId": "call-1",
                    "toolName": "read_file",
                    "arguments": request["arguments"],
                },
            ),
            ("tool.execution_complete", {"toolCallId": "call-1", "success": True}),
            ("user.message", {"content": "second request with marker lifecycle-proof", "attachments": []}),
            ("assistant.message", {"content": "a long response", "reasoningText": "do not emit", "toolRequests": []}),
        ],
    )


@pytest.fixture
def nested_transcript(tmp_path: Path) -> Path:
    """A synthetic parent turn containing a nested agent and an incomplete tail."""
    return _transcript(
        tmp_path,
        "nested-session.jsonl",
        [
            ("session.start", {"sessionId": "22222222-2222-4222-8222-222222222222", "producer": "copilot"}),
            (
                "assistant.message",
                {
                    "content": "parent preamble",
                    "toolRequests": [
                        {
                            "toolCallId": "call-agent",
                            "name": "runSubagent",
                            "arguments": {"agentName": "builder", "prompt": "nested prompt"},
                        }
                    ],
                },
            ),
            (
                "tool.execution_start",
                {
                    "toolCallId": "call-agent",
                    "toolName": "runSubagent",
                    "arguments": {"agentName": "builder", "prompt": "nested prompt"},
                },
            ),
            ("user.message", {"content": "nested prompt", "attachments": []}),
            (
                "assistant.message",
                {
                    "content": "nested response",
                    "toolRequests": [
                        {"toolCallId": "call-read", "name": "read_file", "arguments": {"filePath": "README.md"}}
                    ],
                },
            ),
            (
                "tool.execution_start",
                {
                    "toolCallId": "call-read",
                    "toolName": "read_file",
                    "arguments": {"filePath": "README.md"},
                },
            ),
            ("tool.execution_complete", {"toolCallId": "call-read", "success": True}),
            ("tool.execution_complete", {"toolCallId": "call-agent", "success": True}),
            (
                "assistant.message",
                {
                    "content": "parent resumes",
                    "toolRequests": [
                        {
                            "toolCallId": "call-integrate",
                            "name": "integrate_ready_change",
                            "arguments": {"change_id": "example"},
                        }
                    ],
                },
            ),
            ("assistant.turn_start", {"turnId": "9"}),
        ],
    )


def test_extracts_turns_tools_and_redacts_sensitive_values(extractor: types.ModuleType, transcript: Path) -> None:
    """Extract evidence without leaking private fields."""
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
    """Retain the matching turn and its requested neighbor."""
    config = extractor.ExtractConfig(max_content_chars=100, include_tools=False, include_tool_arguments=False)
    _, turns = extractor.extract_turns(transcript, config)

    selected = extractor.select_turns(
        turns,
        extractor.TurnSelection(
            from_turn=None, to_turn=None, last_turns=None, around="LIFECYCLE-PROOF", context_turns=1
        ),
    )

    assert [turn.index for turn in selected] == [1, 2]


def test_selects_matching_events_inside_one_nested_turn(extractor: types.ModuleType, nested_transcript: Path) -> None:
    """Narrow nested evidence without unrelated messages or tools."""
    config = extractor.ExtractConfig(max_content_chars=100, include_tools=True, include_tool_arguments=True)
    _, turns = extractor.extract_turns(nested_transcript, config)

    selected = extractor.select_events(turns, "README.md")

    assert len(selected) == 1
    assert selected[0].user == "<not selected by --around-event>"
    assert selected[0].nested_users == []
    assert selected[0].assistant == []
    assert [(tool.name, tool.arguments) for tool in selected[0].tools] == [("read_file", {"filePath": "README.md"})]


def test_cli_narrows_events_inside_one_turn(
    extractor: types.ModuleType,
    nested_transcript: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Expose event selection through the bundled command."""
    exit_code = extractor.main(
        (
            "--transcript",
            str(nested_transcript),
            "--around-event",
            "nested response",
            "--include-tools",
            "--format",
            "json",
        )
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert len(payload["turns"]) == 1
    assert payload["turns"][0]["assistant"] == ["nested response"]
    assert payload["turns"][0]["tools"] == []


def test_bounds_content_and_omits_tools_by_default(extractor: types.ModuleType, transcript: Path) -> None:
    """Bound messages while keeping tool evidence opt-in."""
    config = extractor.ExtractConfig(max_content_chars=8, include_tools=False, include_tool_arguments=False)

    _, turns = extractor.extract_turns(transcript, config)

    assert turns[0].user.startswith("first re")
    assert "chars omitted" in turns[0].user
    assert turns[0].tools == []


def test_retains_only_bounded_tail_while_preserving_total_count(extractor: types.ModuleType, transcript: Path) -> None:
    """Retain a bounded tail without losing the total."""
    config = extractor.ExtractConfig(max_content_chars=100, include_tools=False, include_tool_arguments=False)

    metadata, turns = extractor.extract_turns(transcript, config, retain_last=1)

    assert metadata["turn_count"] == _EXPECTED_TURNS
    assert [turn.index for turn in turns] == [2]


def test_preserves_parent_turn_across_nested_agent_invocation(
    extractor: types.ModuleType,
    nested_transcript: Path,
) -> None:
    """Keep nested evidence with its parent and report unresolved raw-tail tools."""
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
    assert metadata["last_event_type"] == "assistant.turn_start"
    assert metadata["last_event_timestamp"] == "2026-08-05T10:00:09Z"
    assert metadata["incomplete_tool_calls"] == [
        {"name": "integrate_ready_change", "tool_call_id": "call-integrate", "state": "requested"},
    ]
    rendered = extractor.render_markdown(metadata, turns)
    assert "not result bodies or command/domain success" in rendered
    assert "1 tool call lacks a completion record" in rendered


def test_bounds_tool_arguments_after_redaction(extractor: types.ModuleType, transcript: Path) -> None:
    """Redact tool arguments before bounding their rendered size."""
    config = extractor.ExtractConfig(max_content_chars=20, include_tools=True, include_tool_arguments=True)

    _, turns = extractor.extract_turns(transcript, config)

    arguments = turns[0].tools[0].arguments
    assert isinstance(arguments, str)
    assert "chars omitted" in arguments
    assert "visible-secret" not in arguments


def test_locates_exact_session_without_recursive_scan(extractor: types.ModuleType, tmp_path: Path) -> None:
    """Resolve the stable workspace-storage path directly."""
    session_id = "11111111-1111-4111-8111-111111111111"
    transcript = tmp_path / "workspace" / "GitHub.copilot-chat" / "transcripts" / f"{session_id}.jsonl"
    transcript.parent.mkdir(parents=True)
    transcript.write_text("", encoding="utf-8")

    assert extractor.locate_transcript(session_id, (tmp_path,)) == transcript


def test_rejects_malformed_json(extractor: types.ModuleType, tmp_path: Path) -> None:
    """Refuse malformed event records."""
    transcript = tmp_path / "broken.jsonl"
    transcript.write_text('{"type": "user.message"}\nnot-json\n', encoding="utf-8")
    config = extractor.ExtractConfig(max_content_chars=100, include_tools=False, include_tool_arguments=False)

    with pytest.raises(ValueError, match="invalid JSON"):
        extractor.extract_turns(transcript, config)
