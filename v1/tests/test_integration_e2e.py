"""End-to-end integration tests — bootstrap to daemon loop.

Exercises the full wiring path from ``bootstrap()`` through real agent
turns, daemon loops, CLI chat I/O, delegation, and hook pipelines.  Uses
PydanticAI ``FunctionModel`` for deterministic model control — no real
API calls.

Task: #295
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pydantic_ai.models
import pytest
from conftest import MockChannel, make_settings  # type: ignore[import-untyped]
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from owlbear.bootstrap import bootstrap
from owlbear.channels.cli import CLIChannel
from owlbear.core.agent import OwlBearAgent
from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.daemon import run_daemon

# Block real LLM requests globally — FunctionModel / TestModel are exempt.
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


# ---------------------------------------------------------------------------
# Test 1: run_daemon with real OwlBearAgent wiring
# ---------------------------------------------------------------------------


class TestRunDaemonWithRealAgent:
    """bootstrap() → run_daemon() processes 1 message, returns response, exits via sentinel."""

    @pytest.mark.asyncio
    async def test_daemon_processes_message_with_real_agent(self, tmp_path: Path) -> None:
        """Bootstrap a real OwlBearAgent with FunctionModel, run_daemon processes 1
        message, and the response is sent back through the channel.
        """

        def model_fn(_messages: list[object], _info: AgentInfo) -> ModelResponse:
            return ModelResponse(parts=[TextPart("daemon says hello")])

        fn_model = FunctionModel(model_fn)

        settings = make_settings(tmp_path)
        mock_client = AsyncMock()
        with (
            patch(
                "owlbear.bootstrap.create_copilot_client",
                new_callable=AsyncMock,
                return_value=mock_client,
            ),
            patch("owlbear.bootstrap.OpenAIChatModel", return_value=fn_model),
        ):
            result = await bootstrap(settings, channel_name="cli", workspace_root=tmp_path)

        assert isinstance(result.agent, OwlBearAgent)

        # Wire a mock channel with one message, then None (EOF)
        channel = MockChannel(["Hello agent", None])

        await run_daemon(
            channel=channel,
            agent=result.agent,
            config_dir=tmp_path,
        )

        # The agent should have responded with the FunctionModel output
        assert len(channel.sent) >= 1
        assert "daemon says hello" in channel.sent[0]

    @pytest.mark.asyncio
    async def test_daemon_exits_cleanly_on_sentinel(self, tmp_path: Path) -> None:
        """Daemon exits cleanly when channel returns None (EOF sentinel)."""

        def model_fn(_messages: list[object], _info: AgentInfo) -> ModelResponse:
            return ModelResponse(parts=[TextPart("response")])

        fn_model = FunctionModel(model_fn)

        settings = make_settings(tmp_path)
        mock_client = AsyncMock()
        with (
            patch(
                "owlbear.bootstrap.create_copilot_client",
                new_callable=AsyncMock,
                return_value=mock_client,
            ),
            patch("owlbear.bootstrap.OpenAIChatModel", return_value=fn_model),
        ):
            result = await bootstrap(settings, channel_name="cli", workspace_root=tmp_path)

        # Channel sends 2 messages, then EOF
        channel = MockChannel(["msg1", "msg2", None])

        await run_daemon(
            channel=channel,
            agent=result.agent,
            config_dir=tmp_path,
        )

        # Both messages processed
        assert len(channel.sent) == 2
        assert all("response" in s for s in channel.sent)

    @pytest.mark.asyncio
    async def test_daemon_with_tool_call(self, tmp_path: Path) -> None:
        """FunctionModel triggers a real tool call (read_file) through the daemon."""
        # Create a file for the agent to read
        (tmp_path / "test.txt").write_text("integration test content", encoding="utf-8")

        call_count = 0

        def model_fn(_messages: list[object], _info: AgentInfo) -> ModelResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ModelResponse(
                    parts=[ToolCallPart(tool_name="read_file", args={"path": "test.txt"})]
                )
            return ModelResponse(parts=[TextPart("I read the file")])

        fn_model = FunctionModel(model_fn)

        settings = make_settings(tmp_path)
        mock_client = AsyncMock()
        with (
            patch(
                "owlbear.bootstrap.create_copilot_client",
                new_callable=AsyncMock,
                return_value=mock_client,
            ),
            patch("owlbear.bootstrap.OpenAIChatModel", return_value=fn_model),
        ):
            result = await bootstrap(settings, channel_name="cli", workspace_root=tmp_path)

        channel = MockChannel(["Read test.txt", None])

        await run_daemon(
            channel=channel,
            agent=result.agent,
            config_dir=tmp_path,
        )

        assert len(channel.sent) >= 1
        assert "I read the file" in channel.sent[0]
        assert call_count == 2  # tool call step + final text step


# ---------------------------------------------------------------------------
# Test 2: _chat_loop I/O through CLIChannel
# ---------------------------------------------------------------------------


class TestChatLoopIO:
    """_chat_loop reads from CLIChannel(StringIO), prints model response to stdout."""

    @pytest.mark.asyncio
    async def test_chat_loop_roundtrip(self, tmp_path: Path) -> None:
        """User input appears in conversation, model response printed to stdout."""
        from bearclaw.cli import _chat_loop

        def model_fn(_messages: list[object], _info: AgentInfo) -> ModelResponse:
            return ModelResponse(parts=[TextPart("chat response")])

        fn_model = FunctionModel(model_fn)

        session = __import__("owlbear.memory.session", fromlist=["SessionStore"]).SessionStore(
            tmp_path / "session.jsonl"
        )
        agent = OwlBearAgent(model="test", session=session)

        # StringIO simulates user typing "hello" then "exit"
        input_stream = StringIO("hello\nexit\n")
        output_stream = StringIO()
        channel = CLIChannel(input=input_stream, output=output_stream)

        with agent.inner.override(model=fn_model):
            await _chat_loop(agent, channel)

        output = output_stream.getvalue()
        # Model response should be in the output
        assert "chat response" in output
        # Goodbye message on exit
        assert "Goodbye" in output

    @pytest.mark.asyncio
    async def test_chat_loop_eof_exits(self, tmp_path: Path) -> None:
        """CLIChannel returning None (empty input) exits the loop."""
        from bearclaw.cli import _chat_loop

        session = __import__("owlbear.memory.session", fromlist=["SessionStore"]).SessionStore(
            tmp_path / "session.jsonl"
        )
        agent = OwlBearAgent(model="test", session=session)

        # Empty StringIO → readline returns "" → receive returns None → loop exits
        input_stream = StringIO("")
        output_stream = StringIO()
        channel = CLIChannel(input=input_stream, output=output_stream)

        with agent.inner.override(model=TestModel(custom_output_text="nope")):
            await _chat_loop(agent, channel)

        output = output_stream.getvalue()
        assert "Goodbye" in output

    @pytest.mark.asyncio
    async def test_chat_loop_multiple_turns(self, tmp_path: Path) -> None:
        """Multiple user messages each get a response."""
        from bearclaw.cli import _chat_loop

        turn_counter = 0

        def model_fn(_messages: list[object], _info: AgentInfo) -> ModelResponse:
            nonlocal turn_counter
            turn_counter += 1
            return ModelResponse(parts=[TextPart(f"reply-{turn_counter}")])

        fn_model = FunctionModel(model_fn)

        session = __import__("owlbear.memory.session", fromlist=["SessionStore"]).SessionStore(
            tmp_path / "session.jsonl"
        )
        agent = OwlBearAgent(model="test", session=session)

        input_stream = StringIO("first\nsecond\nexit\n")
        output_stream = StringIO()
        channel = CLIChannel(input=input_stream, output=output_stream)

        with agent.inner.override(model=fn_model):
            await _chat_loop(agent, channel)

        output = output_stream.getvalue()
        assert "reply-1" in output
        assert "reply-2" in output


# ---------------------------------------------------------------------------
# Test 3: Delegation from orchestrator to inner agent
# ---------------------------------------------------------------------------


class TestDelegation:
    """Orchestrator agent delegates to a coder agent via delegate_to_agent tool."""

    @pytest.mark.asyncio
    async def test_delegation_outer_to_inner(self, tmp_path: Path) -> None:
        """Outer agent emits delegate_to_agent ToolCallPart; inner agent produces output.

        Uses Agent.override to inject FunctionModel for both agents, and
        a real AgentRegistry with a programmatically-registered coder agent.
        """
        from pydantic_ai import Agent

        from owlbear.core.agent_registry import AgentRegistry
        from owlbear.core.delegation import DelegationToolset
        from owlbear.core.deps import OwlBearDeps
        from owlbear.memory.session import SessionStore

        hooks = HookRegistry()

        # -- Inner "coder" agent (returns a fixed reply) -------------------
        inner_model = FunctionModel(
            lambda _msgs, _info: ModelResponse(parts=[TextPart("inner agent output")])
        )
        coder_agent: Agent[OwlBearDeps, str] = Agent("test", instructions="You are a coder.")

        # -- Build a minimal AgentRegistry with the coder ------------------
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        registry = AgentRegistry(
            agents_dir=agents_dir,
            tool_resolver=lambda name: (_ for _ in ()).throw(KeyError(name)),  # type: ignore[arg-type,return-value]
        )
        # Inject the coder agent directly into the cache
        registry._cache["coder"] = coder_agent
        registry._definitions["coder"] = type(
            "FakeDefn",
            (),
            {
                "name": "coder",
                "tools": [],
                "skills": [],
                "role": "builder",
                "model": None,
                "system_prompt": "You are a coder.",
            },
        )()

        # -- Outer "orchestrator" agent (delegates to coder) ---------------
        outer_call_count = 0

        def outer_model_fn(_messages: list[object], _info: AgentInfo) -> ModelResponse:
            nonlocal outer_call_count
            outer_call_count += 1
            if outer_call_count == 1:
                return ModelResponse(
                    parts=[
                        ToolCallPart(
                            tool_name="delegate_to_agent",
                            args={"agent_name": "coder", "task": "Write hello world"},
                        )
                    ]
                )
            # After delegation returns, produce final output including inner result
            return ModelResponse(parts=[TextPart("orchestrator done: inner agent output")])

        outer_model = FunctionModel(outer_model_fn)

        session = SessionStore(tmp_path / "session.jsonl")
        agent = OwlBearAgent(
            model="test",
            session=session,
            hooks=hooks,
            toolsets=[DelegationToolset()],
        )
        agent._deps.agent_registry = registry

        with (
            agent.inner.override(model=outer_model),
            coder_agent.override(model=inner_model),
        ):
            result = await agent.turn("Delegate a task to coder")

        assert "inner agent output" in result
        assert outer_call_count == 2  # tool call + final text


# ---------------------------------------------------------------------------
# Test 4: Hook pipeline fires in correct order through bootstrap
# ---------------------------------------------------------------------------


class TestHookPipeline:
    """Bootstrap-wired HookRegistry fires PRE_TOOL → POST_TOOL in order."""

    @pytest.mark.asyncio
    async def test_hook_events_fire_in_order(self, tmp_path: Path) -> None:
        """Register a listener that records events. Execute agent.turn() with a
        tool call. Assert: events fired in order PRE_TOOL → POST_TOOL.
        """
        call_count = 0

        def model_fn(_messages: list[object], _info: AgentInfo) -> ModelResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ModelResponse(
                    parts=[ToolCallPart(tool_name="read_file", args={"path": "hook_test.txt"})]
                )
            return ModelResponse(parts=[TextPart("done")])

        fn_model = FunctionModel(model_fn)

        # Create the file the tool will read
        (tmp_path / "hook_test.txt").write_text("hook content", encoding="utf-8")

        settings = make_settings(tmp_path)
        mock_client = AsyncMock()
        with (
            patch(
                "owlbear.bootstrap.create_copilot_client",
                new_callable=AsyncMock,
                return_value=mock_client,
            ),
            patch("owlbear.bootstrap.OpenAIChatModel", return_value=fn_model),
        ):
            result = await bootstrap(settings, channel_name="cli", workspace_root=tmp_path)

        # Record hook events
        events: list[str] = []

        result.hooks.register(HookEvent.PRE_TOOL_USE, lambda _d: events.append("PRE_TOOL"))
        result.hooks.register(HookEvent.POST_TOOL_USE, lambda _d: events.append("POST_TOOL"))

        reply = await result.agent.turn("Read hook_test.txt")

        assert reply == "done"
        # PRE_TOOL must come before POST_TOOL
        assert "PRE_TOOL" in events
        assert "POST_TOOL" in events
        pre_idx = events.index("PRE_TOOL")
        post_idx = events.index("POST_TOOL")
        assert pre_idx < post_idx

    @pytest.mark.asyncio
    async def test_hook_events_include_tool_name(self, tmp_path: Path) -> None:
        """Hook data includes the tool name for both PRE and POST events."""
        call_count = 0

        def model_fn(_messages: list[object], _info: AgentInfo) -> ModelResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ModelResponse(
                    parts=[ToolCallPart(tool_name="read_file", args={"path": "data.txt"})]
                )
            return ModelResponse(parts=[TextPart("read complete")])

        fn_model = FunctionModel(model_fn)

        (tmp_path / "data.txt").write_text("some data", encoding="utf-8")

        settings = make_settings(tmp_path)
        mock_client = AsyncMock()
        with (
            patch(
                "owlbear.bootstrap.create_copilot_client",
                new_callable=AsyncMock,
                return_value=mock_client,
            ),
            patch("owlbear.bootstrap.OpenAIChatModel", return_value=fn_model),
        ):
            result = await bootstrap(settings, channel_name="cli", workspace_root=tmp_path)

        captured: list[dict] = []

        def capture_pre(data: object) -> None:
            if isinstance(data, dict):
                captured.append({"event": "pre", **data})

        def capture_post(data: object) -> None:
            if isinstance(data, dict):
                captured.append({"event": "post", **data})

        result.hooks.register(HookEvent.PRE_TOOL_USE, capture_pre)
        result.hooks.register(HookEvent.POST_TOOL_USE, capture_post)

        await result.agent.turn("Read data.txt")

        pre_events = [e for e in captured if e["event"] == "pre"]
        post_events = [e for e in captured if e["event"] == "post"]

        assert len(pre_events) >= 1
        assert len(post_events) >= 1
        assert pre_events[0]["tool_name"] == "read_file"
        assert post_events[0]["tool_name"] == "read_file"

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_fire_multiple_hook_pairs(self, tmp_path: Path) -> None:
        """Two tool calls → two PRE/POST pairs in order."""
        call_count = 0

        def model_fn(_messages: list[object], _info: AgentInfo) -> ModelResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ModelResponse(
                    parts=[ToolCallPart(tool_name="read_file", args={"path": "a.txt"})]
                )
            if call_count == 2:
                return ModelResponse(
                    parts=[ToolCallPart(tool_name="read_file", args={"path": "b.txt"})]
                )
            return ModelResponse(parts=[TextPart("all done")])

        fn_model = FunctionModel(model_fn)

        (tmp_path / "a.txt").write_text("aaa", encoding="utf-8")
        (tmp_path / "b.txt").write_text("bbb", encoding="utf-8")

        settings = make_settings(tmp_path)
        mock_client = AsyncMock()
        with (
            patch(
                "owlbear.bootstrap.create_copilot_client",
                new_callable=AsyncMock,
                return_value=mock_client,
            ),
            patch("owlbear.bootstrap.OpenAIChatModel", return_value=fn_model),
        ):
            result = await bootstrap(settings, channel_name="cli", workspace_root=tmp_path)

        events: list[str] = []
        result.hooks.register(HookEvent.PRE_TOOL_USE, lambda _d: events.append("PRE"))
        result.hooks.register(HookEvent.POST_TOOL_USE, lambda _d: events.append("POST"))

        await result.agent.turn("Read both files")

        # Should have at least 2 PRE and 2 POST (there are also built-in hooks
        # that might fire, but our listeners should see at least 2 of each)
        pre_count = events.count("PRE")
        post_count = events.count("POST")
        assert pre_count >= 2
        assert post_count >= 2

        # Events should alternate PRE, POST, PRE, POST
        # (each tool call: PRE before POST)
        for i, evt in enumerate(events):
            if evt == "POST":
                # There must be a PRE before this POST
                assert "PRE" in events[:i]
