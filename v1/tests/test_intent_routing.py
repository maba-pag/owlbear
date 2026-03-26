"""Tests for intent routing — orchestrator delegates to correct agent per intent.

Uses FunctionModel + ToolCallPart pattern (following tests/test_integration_e2e.py
TestDelegation) to verify that when the model decides to delegate, it uses the
correct tool with the correct agent name.  Each test scenario simulates a
different user intent category.

Tasks: #310, #312
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pydantic_ai.models
import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from owlbear.core.agent import OwlBearAgent
from owlbear.core.agent_def import AgentDefinition, parse_agent_definition
from owlbear.core.agent_registry import AgentRegistry
from owlbear.core.delegation import DelegationToolset
from owlbear.core.deps import OwlBearDeps
from owlbear.core.hooks import HookRegistry
from owlbear.memory.session import SessionStore
from owlbear.tools.ask_user import AskUserToolset

# Block real LLM requests — FunctionModel is exempt.
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False

# ---------------------------------------------------------------------------
# All known specialist agent names
# ---------------------------------------------------------------------------

SPECIALIST_AGENTS = ["planner", "coder", "researcher", "reviewer", "writer"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _inner_model() -> FunctionModel:
    """FunctionModel for delegated-to agents — returns a fixed reply."""
    return FunctionModel(
        lambda _msgs, _info: ModelResponse(parts=[TextPart("inner agent done")])
    )


def _build_registry(tmp_path: Path) -> AgentRegistry:
    """Build an AgentRegistry pre-loaded with mock agents for all specialists."""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir(exist_ok=True)

    registry = AgentRegistry(
        agents_dir=agents_dir,
        tool_resolver=lambda name: (_ for _ in ()).throw(KeyError(name)),  # type: ignore[arg-type,return-value]
    )
    for name in SPECIALIST_AGENTS:
        agent: Agent[OwlBearDeps, str] = Agent("test", instructions=f"You are {name}.")
        registry._cache[name] = agent
        registry._definitions[name] = AgentDefinition(
            name=name,
            description=f"{name} agent",
            role="builder",
            system_prompt=f"You are {name}.",
        )
    return registry


def _delegation_model(agent_name: str, task: str) -> FunctionModel:
    """FunctionModel that delegates to *agent_name* then returns final text."""
    call_count = 0

    def fn(_messages: list[ModelMessage], _info: AgentInfo) -> ModelResponse:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        tool_name="delegate_to_agent",
                        args={"agent_name": agent_name, "task": task},
                    )
                ]
            )
        return ModelResponse(parts=[TextPart(f"routed to {agent_name}")])

    return FunctionModel(fn)


def _direct_response_model(text: str) -> FunctionModel:
    """FunctionModel that returns text directly — no tool calls."""
    return FunctionModel(
        lambda _msgs, _info: ModelResponse(parts=[TextPart(text)])
    )


async def _run_delegation_test(
    tmp_path: Path,
    user_message: str,
    target_agent: str,
) -> str:
    """Full integration path: user message -> delegate to target_agent -> result."""
    registry = _build_registry(tmp_path)
    inner = _inner_model()
    outer = _delegation_model(target_agent, user_message)

    session = SessionStore(tmp_path / "session.jsonl")
    agent = OwlBearAgent(
        model="test",
        session=session,
        hooks=HookRegistry(),
        toolsets=[DelegationToolset()],
    )
    agent._deps.agent_registry = registry

    with agent.inner.override(model=outer), contextlib.ExitStack() as stack:
        for name in SPECIALIST_AGENTS:
            stack.enter_context(registry._cache[name].override(model=inner))
        return await agent.turn(user_message)


# ---------------------------------------------------------------------------
# Task #310: Intent routing tests
# ---------------------------------------------------------------------------


class TestPlanIntent:
    """'I have an idea for a feature' -> delegates to planner."""

    @pytest.mark.asyncio
    async def test_delegates_to_planner(self, tmp_path: Path) -> None:
        result = await _run_delegation_test(
            tmp_path,
            user_message="I have an idea for a feature",
            target_agent="planner",
        )
        assert "routed to planner" in result


class TestBuildIntent:
    """'Fix the bug in config.py' -> delegates to coder."""

    @pytest.mark.asyncio
    async def test_delegates_to_coder(self, tmp_path: Path) -> None:
        result = await _run_delegation_test(
            tmp_path,
            user_message="Fix the bug in config.py",
            target_agent="coder",
        )
        assert "routed to coder" in result


class TestResearchIntent:
    """'Research how others do X' -> delegates to researcher."""

    @pytest.mark.asyncio
    async def test_delegates_to_researcher(self, tmp_path: Path) -> None:
        result = await _run_delegation_test(
            tmp_path,
            user_message="Research how others do X",
            target_agent="researcher",
        )
        assert "routed to researcher" in result


class TestReviewIntent:
    """'Review the changes in PR #5' -> delegates to reviewer."""

    @pytest.mark.asyncio
    async def test_delegates_to_reviewer(self, tmp_path: Path) -> None:
        result = await _run_delegation_test(
            tmp_path,
            user_message="Review the changes in PR #5",
            target_agent="reviewer",
        )
        assert "routed to reviewer" in result


class TestStatusIntent:
    """'What is the status of the board?' -> orchestrator handles directly."""

    @pytest.mark.asyncio
    async def test_handles_directly_no_delegation(self, tmp_path: Path) -> None:
        """Model returns text directly — delegate_to_agent is never called."""
        registry = _build_registry(tmp_path)
        outer = _direct_response_model("Board status: 3 in-progress, 5 todo")

        session = SessionStore(tmp_path / "session.jsonl")
        agent = OwlBearAgent(
            model="test",
            session=session,
            hooks=HookRegistry(),
            toolsets=[DelegationToolset()],
        )
        agent._deps.agent_registry = registry

        with agent.inner.override(model=outer):
            result = await agent.turn("What is the status of the board?")

        assert "Board status" in result


class TestAmbiguousIntent:
    """Ambiguous message -> calls ask_user for clarification."""

    @pytest.mark.asyncio
    async def test_calls_ask_user_for_clarification(self, tmp_path: Path) -> None:
        call_count = 0

        def model_fn(
            _messages: list[ModelMessage], _info: AgentInfo,
        ) -> ModelResponse:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ModelResponse(
                    parts=[
                        ToolCallPart(
                            tool_name="ask_user",
                            args={
                                "question": "Could you clarify?",
                            },
                        )
                    ]
                )
            return ModelResponse(parts=[TextPart("clarified and proceeding")])

        outer = FunctionModel(model_fn)

        channel = MagicMock()
        channel.name = "test"
        channel.send = AsyncMock()
        channel.receive = AsyncMock(return_value="I want to plan a new feature")

        session = SessionStore(tmp_path / "session.jsonl")
        agent = OwlBearAgent(
            model="test",
            session=session,
            hooks=HookRegistry(),
            toolsets=[DelegationToolset(), AskUserToolset(channel)],
        )
        registry = _build_registry(tmp_path)
        agent._deps.agent_registry = registry

        with agent.inner.override(model=outer):
            result = await agent.turn("Do something about the widget")

        assert "clarified" in result
        channel.send.assert_called_once()
        channel.receive.assert_called_once()


class TestMidConversationReroute:
    """Mid-conversation reroute: start with coder, switch to researcher."""

    @pytest.mark.asyncio
    async def test_reroutes_to_researcher(self, tmp_path: Path) -> None:
        registry = _build_registry(tmp_path)
        inner = _inner_model()
        call_count = 0

        def model_fn(
            _messages: list[ModelMessage], _info: AgentInfo,
        ) -> ModelResponse:
            nonlocal call_count
            call_count += 1
            # Turn 1: delegate to coder
            if call_count == 1:
                return ModelResponse(
                    parts=[
                        ToolCallPart(
                            tool_name="delegate_to_agent",
                            args={"agent_name": "coder", "task": "Fix the widget bug"},
                        )
                    ]
                )
            if call_count == 2:
                return ModelResponse(parts=[TextPart("coder handled it")])
            # Turn 2: delegate to researcher
            if call_count == 3:
                return ModelResponse(
                    parts=[
                        ToolCallPart(
                            tool_name="delegate_to_agent",
                            args={
                                "agent_name": "researcher",
                                "task": "Research widget alternatives",
                            },
                        )
                    ]
                )
            return ModelResponse(parts=[TextPart("researcher handled it")])

        outer = FunctionModel(model_fn)

        session = SessionStore(tmp_path / "session.jsonl")
        agent = OwlBearAgent(
            model="test",
            session=session,
            hooks=HookRegistry(),
            toolsets=[DelegationToolset()],
        )
        agent._deps.agent_registry = registry

        with agent.inner.override(model=outer), contextlib.ExitStack() as stack:
            for name in SPECIALIST_AGENTS:
                stack.enter_context(registry._cache[name].override(model=inner))

            # Turn 1: coder
            result1 = await agent.turn("Fix the widget bug")
            assert "coder handled it" in result1

            # Turn 2: reroute to researcher
            result2 = await agent.turn(
                "Actually, research widget alternatives first"
            )
            assert "researcher handled it" in result2

        assert call_count == 4


# ---------------------------------------------------------------------------
# Task #312: Agent catalog consistency
# ---------------------------------------------------------------------------


class TestAgentCatalog:
    """Agent catalog in orchestrator.md matches actual agent definition files."""

    def test_catalog_lists_all_specialist_agents(self) -> None:
        """Every agent .md file (except orchestrator) is in the catalog."""
        agents_dir = Path("src/owlbear/agents")
        orchestrator_md = agents_dir / "orchestrator.md"

        # Get all agent names from .md files (excluding orchestrator)
        agent_names = sorted(
            p.stem for p in agents_dir.glob("*.md") if p.stem != "orchestrator"
        )

        content = orchestrator_md.read_text()

        for name in agent_names:
            assert name in content, (
                f"Agent '{name}' has a definition file but is not listed "
                f"in orchestrator.md catalog"
            )

    def test_catalog_descriptions_match_definitions(self) -> None:
        """Agent descriptions in catalog match their definition files."""
        agents_dir = Path("src/owlbear/agents")

        # Parse each agent definition and collect descriptions
        for md_path in agents_dir.glob("*.md"):
            if md_path.stem == "orchestrator":
                continue
            defn = parse_agent_definition(md_path)
            orchestrator_content = (agents_dir / "orchestrator.md").read_text()
            assert defn.description in orchestrator_content, (
                f"Agent '{defn.name}' description '{defn.description}' not found "
                f"in orchestrator.md catalog"
            )
