"""E2E integration tests for OwlBearAgent chat lifecycle.

Tests exercise the full turn() stack — hooks, session persistence, and real
tool execution — using PydanticAI's ``FunctionModel`` to control model
responses without making real LLM calls.

Pattern: FunctionModel with step-based dispatch + ``Agent.override`` on
``agent.inner``.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pydantic_ai.models
from pydantic_ai.messages import (
    ModelResponse,
    TextPart,
    ToolCallPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from owlbear.core.agent import OwlBearAgent
from owlbear.memory.session import SessionStore
from owlbear.tools.filesystem import FileToolset
from owlbear.tools.terminal import TerminalToolset

# Global guard — blocks any real LLM requests (FunctionModel is exempt).
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

type _Messages = list[object]
"""Shorthand for the messages list passed to FunctionModel callbacks."""


# ---------------------------------------------------------------------------
# Test: text response
# ---------------------------------------------------------------------------


class TestTextResponse:
    """FunctionModel returns TextPart, OwlBearAgent.turn() returns the string."""

    def test_turn_returns_text_response(self, tmp_path: Path) -> None:
        """Agent turn with a simple text response — no tool calls."""

        def model_fn(_messages: _Messages, _info: AgentInfo) -> ModelResponse:
            return ModelResponse(parts=[TextPart("Hello from OwlBear!")])

        session = SessionStore(tmp_path / "session.jsonl")
        agent = OwlBearAgent(model="test", session=session)

        import asyncio

        with agent.inner.override(model=FunctionModel(model_fn)):
            result = asyncio.run(agent.turn("hi"))

        assert result == "Hello from OwlBear!"


# ---------------------------------------------------------------------------
# Test: read_file tool
# ---------------------------------------------------------------------------


class TestReadFileTool:
    """FunctionModel emits ToolCallPart for read_file, real FileToolset reads a tmp_path file."""

    def test_read_file_tool_executes(self, tmp_path: Path) -> None:
        """Agent calls read_file tool, FileToolset reads real file, model summarises."""
        # Arrange: create a real file in the workspace
        (tmp_path / "test.txt").write_text("hello world", encoding="utf-8")

        call_count = 0

        def model_fn(_messages: _Messages, _info: AgentInfo) -> ModelResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Step 1: ask the agent to call read_file
                return ModelResponse(
                    parts=[ToolCallPart(tool_name="read_file", args={"path": "test.txt"})]
                )
            # Step 2: the tool result is in messages; return a summary
            return ModelResponse(parts=[TextPart("File contains: hello world")])

        session = SessionStore(tmp_path / "session.jsonl")
        agent = OwlBearAgent(
            model="test",
            session=session,
            toolsets=[FileToolset(tmp_path)],
        )

        with agent.inner.override(model=FunctionModel(model_fn)):
            result = asyncio.run(agent.turn("Read test.txt"))

        assert result == "File contains: hello world"
        assert call_count == 2  # model called twice (tool call + final text)


# ---------------------------------------------------------------------------
# Test: run_command tool
# ---------------------------------------------------------------------------


class TestRunCommandTool:
    """FunctionModel emits ToolCallPart for run_command; real subprocess."""

    def test_run_command_tool_executes(self, tmp_path: Path) -> None:
        """Agent calls run_command, TerminalToolset runs real 'echo hello', model returns result."""

        call_count = 0

        def model_fn(_messages: _Messages, _info: AgentInfo) -> ModelResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Step 1: ask the agent to run a command
                return ModelResponse(
                    parts=[
                        ToolCallPart(
                            tool_name="run_command",
                            args={"command": "echo hello"},
                        )
                    ]
                )
            # Step 2: the command output is in messages; return summary
            return ModelResponse(parts=[TextPart("Command returned: hello")])

        session = SessionStore(tmp_path / "session.jsonl")
        agent = OwlBearAgent(
            model="test",
            session=session,
            toolsets=[TerminalToolset(workspace_root=tmp_path)],
        )

        with agent.inner.override(model=FunctionModel(model_fn)):
            result = asyncio.run(agent.turn("Run echo hello"))

        assert result == "Command returned: hello"
        assert call_count == 2


# ---------------------------------------------------------------------------
# Test: session persistence
# ---------------------------------------------------------------------------


class TestSessionPersistence:
    """After agent.turn(), SessionStore JSONL file exists with serialised messages."""

    def test_session_file_created_after_turn(self, tmp_path: Path) -> None:
        """The session JSONL file is created and contains messages after a turn."""
        session_path = tmp_path / "session.jsonl"

        def model_fn(_messages: _Messages, _info: AgentInfo) -> ModelResponse:
            return ModelResponse(parts=[TextPart("persisted reply")])

        session = SessionStore(session_path)
        agent = OwlBearAgent(model="test", session=session)

        with agent.inner.override(model=FunctionModel(model_fn)):
            asyncio.run(agent.turn("save this"))

        # Session file must exist
        assert session_path.exists()

        # Must contain serialised messages (at least user prompt + model response)
        loaded = session.load()
        assert len(loaded) >= 2


# ---------------------------------------------------------------------------
# Test: session continuity
# ---------------------------------------------------------------------------


class TestSessionContinuity:
    """Agent B picks up Agent A's history and can continue the conversation."""

    def test_second_agent_loads_first_agents_history(self, tmp_path: Path) -> None:
        """Create agent A, run turn, create agent B with same session — B has A's history."""
        session_path = tmp_path / "session.jsonl"

        # --- Agent A ---
        def model_fn_a(_messages: _Messages, _info: AgentInfo) -> ModelResponse:
            return ModelResponse(parts=[TextPart("reply from A")])

        session_a = SessionStore(session_path)
        agent_a = OwlBearAgent(model="test", session=session_a)

        with agent_a.inner.override(model=FunctionModel(model_fn_a)):
            asyncio.run(agent_a.turn("message to A"))

        first_messages = session_a.load()
        assert len(first_messages) >= 2

        # --- Agent B (new instance, same session path) ---
        call_count = 0

        def model_fn_b(_messages: _Messages, _info: AgentInfo) -> ModelResponse:
            nonlocal call_count
            call_count += 1
            # messages should contain Agent A's history + the new user prompt
            return ModelResponse(parts=[TextPart("reply from B")])

        session_b = SessionStore(session_path)
        agent_b = OwlBearAgent(model="test", session=session_b)

        with agent_b.inner.override(model=FunctionModel(model_fn_b)):
            result = asyncio.run(agent_b.turn("message to B"))

        assert result == "reply from B"

        # Session should now contain messages from both turns
        all_messages = session_b.load()
        assert len(all_messages) > len(first_messages)
